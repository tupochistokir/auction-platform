from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.database import SessionLocal
from app.db.models import Auction, Bid
from app.pricing.decision import seller_decision
from app.pricing.forecast import calculate_expected_final_price
from fastapi import UploadFile, File
import shutil
import uuid

router = APIRouter(prefix="/auctions", tags=["Аукционы"])


class BidCreate(BaseModel):
    user: str
    amount: float


@router.get("/")
def get_auctions():
    db = SessionLocal()

    auctions = db.query(Auction).all()
    result = []

    for a in auctions:
        bids = db.query(Bid).filter(Bid.auction_id == a.id).all()

        result.append({
            "id": a.id,
            "title": a.title,
            "brand": a.brand,
            "current_price": a.current_price,
            "recommended_bid_step": a.recommended_bid_step,
            "status": a.status,
            "image_url": a.image_url,
            "image_urls": a.image_urls or [],
            "bids": [{"user": b.user, "amount": b.amount} for b in bids]
        })

    db.close()
    return {"auctions": result}


@router.get("/{auction_id}")
def get_auction(auction_id: int):
    db = SessionLocal()

    auction = db.query(Auction).filter(Auction.id == auction_id).first()

    if not auction:
        db.close()
        raise HTTPException(status_code=404, detail="Аукцион не найден")

    bids = db.query(Bid).filter(Bid.auction_id == auction_id).all()

    result = {
        "id": auction.id,
        "title": auction.title,
        "brand": auction.brand,
        "current_price": auction.current_price,
        "recommended_bid_step": auction.recommended_bid_step,
        "status": auction.status,
        "image_url": auction.image_url,
        "image_urls": auction.image_urls or [],
        "bids": [{"user": b.user, "amount": b.amount} for b in bids]
    }

    db.close()
    return result


@router.post("/{auction_id}/bid")
def place_bid(auction_id: int, bid: BidCreate):
    try:
        db = SessionLocal()

        auction = db.query(Auction).filter(Auction.id == auction_id).first()

        if not auction:
            db.close()
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        if auction.status != "active":
            db.close()
            raise HTTPException(status_code=400, detail="Аукцион завершён")

        min_bid = auction.current_price + auction.recommended_bid_step

        if bid.amount < min_bid:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Минимальная ставка должна быть не меньше {round(min_bid, 2)} ₽"
            )

        new_bid = Bid(
            auction_id=auction_id,
            user=bid.user,
            amount=float(bid.amount)
        )

        auction.current_price = float(bid.amount)

        db.add(new_bid)
        db.commit()

        bids = db.query(Bid).filter(Bid.auction_id == auction_id).all()

        db.close()

        return {
            "message": "Ставка принята",
            "auction": {
                "id": auction.id,
                "title": auction.title,
                "brand": auction.brand,
                "current_price": auction.current_price,
                "recommended_bid_step": auction.recommended_bid_step,
                "status": auction.status,
                "bids": [{"user": b.user, "amount": b.amount} for b in bids]
            }
        }

    except Exception as e:
        return {"error": str(e)}

from app.schemas.lot import LotCreate


@router.post("/")
def create_auction(lot: LotCreate):
    db = SessionLocal()

    new_auction = Auction(
        image_url=lot.image_url,
        image_urls=lot.image_urls,
        title=lot.title,
        brand=lot.questionnaire.brand,
        current_price=lot.start_price,
        start_price=lot.start_price,
        description=lot.description,
        status="active",
        recommended_bid_step=100,
        questionnaire=lot.questionnaire.dict(),
        analysis={}
    )

    db.add(new_auction)
    db.commit()
    db.refresh(new_auction)

    db.close()

    return {
        "message": "Аукцион создан",
        "auction": {
            "id": new_auction.id,
            "title": new_auction.title,
            "current_price": new_auction.current_price
        }
    }

class OfferCreate(BaseModel):
    user: str
    amount: float


@router.post("/{auction_id}/offer")
def make_offer(auction_id: int, offer: OfferCreate):
    db = SessionLocal()

    auction = db.query(Auction).filter(Auction.id == auction_id).first()

    if not auction:
        db.close()
        raise HTTPException(status_code=404, detail="Аукцион не найден")

    # прогноз финальной цены
    expected_price = calculate_expected_final_price(
        base_price=auction.start_price,
        attractiveness=0.7,
        value_score=0.7
    )

    decision = seller_decision(offer.amount, expected_price)

    new_offer = Offer(
        auction_id=auction_id,
        user=offer.user,
        amount=offer.amount,
        status=decision
    )

    db.add(new_offer)
    db.commit()

    db.close()

    return {
        "offer": offer.amount,
        "expected_price": round(expected_price, 2),
        "decision": decision
    }

@router.post("/upload-image")
def upload_image(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}.jpg"
    file_path = f"uploads/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"image_url": f"http://127.0.0.1:8000/uploads/{filename}"}
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.db.models import Auction, Bid, Offer
from app.pricing.math_core import calculate_full_pricing, calculate_recommended_bid
from app.schemas.lot import LotCreate

router = APIRouter(prefix="/auctions", tags=["Аукционы"])


class BidCreate(BaseModel):
    user: str
    amount: float


class OfferCreate(BaseModel):
    user: str
    amount: float


class BidRecommendationRequest(BaseModel):
    user_value: float


class OfferDecisionRequest(BaseModel):
    action: str
    counter_amount: Optional[float] = None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _bid_to_dict(bid: Bid) -> Dict[str, Any]:
    return {
        "id": bid.id,
        "auction_id": bid.auction_id,
        "user": bid.user,
        "amount": bid.amount,
        "created_at": _iso(getattr(bid, "created_at", None)),
    }


def _offer_to_dict(offer: Offer) -> Dict[str, Any]:
    return {
        "id": offer.id,
        "auction_id": offer.auction_id,
        "user": offer.user,
        "amount": offer.amount,
        "status": offer.status,
        "recommendation": getattr(offer, "recommendation", None),
        "seller_wait_utility": getattr(offer, "seller_wait_utility", None),
        "risk_discount": getattr(offer, "risk_discount", None),
        "counter_amount": getattr(offer, "counter_amount", None),
        "created_at": _iso(getattr(offer, "created_at", None)),
        "decided_at": _iso(getattr(offer, "decided_at", None)),
    }


def _seller_name(auction: Auction) -> str:
    return getattr(auction, "seller_name", None) or "Кирилл"


def _sync_auction_status(auction: Auction) -> None:
    end_time = getattr(auction, "end_time", None)
    if auction.status == "active" and end_time and end_time <= datetime.utcnow():
        auction.status = "finished"


def _serialize_auction(
    db,
    auction: Auction,
    include_offers: bool = False,
) -> Dict[str, Any]:
    _sync_auction_status(auction)

    bids = (
        db.query(Bid)
        .filter(Bid.auction_id == auction.id)
        .order_by(Bid.created_at.asc(), Bid.id.asc())
        .all()
    )
    analysis = auction.analysis or {}

    result = {
        "id": auction.id,
        "title": auction.title,
        "brand": auction.brand,
        "seller_name": _seller_name(auction),
        "description": auction.description,
        "current_price": auction.current_price,
        "start_price": auction.start_price,
        "recommended_bid_step": auction.recommended_bid_step,
        "expected_final_price": analysis.get("expected_final_price"),
        "auction_attractiveness": analysis.get("auction_attractiveness"),
        "confirmed_value_score": analysis.get("confirmed_value_score"),
        "status": auction.status,
        "image_url": auction.image_url,
        "image_urls": auction.image_urls or [],
        "questionnaire": auction.questionnaire or {},
        "analysis": analysis,
        "created_at": _iso(getattr(auction, "created_at", None)),
        "end_time": _iso(getattr(auction, "end_time", None)),
        "bids": [_bid_to_dict(bid) for bid in bids],
    }

    if include_offers:
        offers = (
            db.query(Offer)
            .filter(Offer.auction_id == auction.id)
            .order_by(Offer.created_at.asc(), Offer.id.asc())
            .all()
        )
        result["offers"] = [_offer_to_dict(offer) for offer in offers]

    return result


@router.get("/")
def get_auctions():
    db = SessionLocal()
    try:
        auctions = db.query(Auction).order_by(Auction.id.desc()).all()
        result = [_serialize_auction(db, auction) for auction in auctions]
        db.commit()
        return {"auctions": result}
    finally:
        db.close()


@router.get("/profile/{user_name}")
def get_profile(user_name: str):
    db = SessionLocal()
    try:
        normalized_user = user_name.strip().lower()
        auctions = db.query(Auction).order_by(Auction.id.desc()).all()
        bids = db.query(Bid).order_by(Bid.id.desc()).all()
        offers = db.query(Offer).order_by(Offer.id.desc()).all()

        auction_by_id = {auction.id: auction for auction in auctions}
        seller_auctions = [
            auction
            for auction in auctions
            if _seller_name(auction).strip().lower() == normalized_user
        ]
        seller_auction_ids = {auction.id for auction in seller_auctions}

        user_bids = [
            bid for bid in bids if (bid.user or "").strip().lower() == normalized_user
        ]
        latest_bid_by_auction: Dict[int, Bid] = {}
        for bid in user_bids:
            if bid.auction_id not in latest_bid_by_auction:
                latest_bid_by_auction[bid.auction_id] = bid

        buyer_lots = []
        for auction_id, bid in latest_bid_by_auction.items():
            auction = auction_by_id.get(auction_id)
            if not auction:
                continue
            _sync_auction_status(auction)
            buyer_lots.append({
                "auction": _serialize_auction(db, auction, include_offers=False),
                "my_last_bid": _bid_to_dict(bid),
                "is_leading": float(auction.current_price or 0) == float(bid.amount or 0),
            })

        sent_offers = [
            {
                "offer": _offer_to_dict(offer),
                "auction": _serialize_auction(db, auction_by_id[offer.auction_id], include_offers=False),
            }
            for offer in offers
            if (offer.user or "").strip().lower() == normalized_user
            and offer.auction_id in auction_by_id
        ]

        incoming_offers = [
            {
                "offer": _offer_to_dict(offer),
                "auction": _serialize_auction(db, auction_by_id[offer.auction_id], include_offers=False),
            }
            for offer in offers
            if offer.auction_id in seller_auction_ids and offer.auction_id in auction_by_id
        ]

        active_seller_auctions = [
            auction for auction in seller_auctions if auction.status == "active"
        ]
        finished_seller_auctions = [
            auction for auction in seller_auctions if auction.status == "finished"
        ]
        pending_incoming = [
            item for item in incoming_offers if item["offer"]["status"] == "pending"
        ]

        return {
            "user": {
                "name": user_name,
                "roles": ["buyer", "seller"],
                "rating": 4.9,
                "verification": "demo_verified",
            },
            "buyer": {
                "stats": {
                    "active_bids": len(buyer_lots),
                    "leading_bids": sum(1 for item in buyer_lots if item["is_leading"]),
                    "sent_offers": len(sent_offers),
                    "pending_offers": sum(
                        1 for item in sent_offers if item["offer"]["status"] == "pending"
                    ),
                },
                "bids": buyer_lots,
                "offers": sent_offers,
            },
            "seller": {
                "stats": {
                    "listings": len(seller_auctions),
                    "active_listings": len(active_seller_auctions),
                    "finished_listings": len(finished_seller_auctions),
                    "pending_offers": len(pending_incoming),
                    "expected_revenue": round(
                        sum(float(auction.current_price or 0) for auction in seller_auctions),
                        2,
                    ),
                },
                "listings": [
                    _serialize_auction(db, auction, include_offers=True)
                    for auction in seller_auctions
                ],
                "incoming_offers": incoming_offers,
            },
        }
    finally:
        db.commit()
        db.close()


@router.get("/{auction_id}")
def get_auction(auction_id: int):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        result = _serialize_auction(db, auction, include_offers=True)
        db.commit()
        return result
    finally:
        db.close()


@router.post("/")
def create_auction(lot: LotCreate):
    db = None
    try:
        questionnaire_dict = lot.questionnaire.dict()
        pricing_result = calculate_full_pricing(questionnaire_dict)
        final_start_price = (
            float(lot.start_price)
            if lot.start_price and lot.start_price > 0
            else pricing_result["recommended_start_price"]
        )
        final_bid_step = (
            float(lot.bid_step_override)
            if lot.bid_step_override and lot.bid_step_override > 0
            else pricing_result["recommended_bid_step"]
        )
        pricing_result["seller_final_start_price"] = round(final_start_price, 2)
        pricing_result["seller_final_bid_step"] = round(final_bid_step, 2)
        now = datetime.utcnow()

        db = SessionLocal()
        new_auction = Auction(
            image_url=lot.image_url,
            image_urls=lot.image_urls,
            title=lot.title,
            brand=lot.questionnaire.brand or "unknown",
            seller_name=lot.seller_name or "Кирилл",
            current_price=round(final_start_price, 2),
            start_price=round(final_start_price, 2),
            description=lot.description,
            status="active",
            recommended_bid_step=round(final_bid_step, 2),
            questionnaire=questionnaire_dict,
            analysis=pricing_result,
            created_at=now,
            end_time=now + timedelta(days=7),
        )

        db.add(new_auction)
        db.commit()
        db.refresh(new_auction)

        return {
            "message": "Аукцион создан на основе математической модели ценообразования",
            "auction": _serialize_auction(db, new_auction, include_offers=True),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании аукциона: {exc}",
        )
    finally:
        if db:
            db.close()


@router.post("/{auction_id}/bid")
def place_bid(auction_id: int, bid: BidCreate):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        _sync_auction_status(auction)
        if auction.status != "active":
            db.commit()
            raise HTTPException(status_code=400, detail="Аукцион завершен")

        current_price = float(auction.current_price or 0)
        bid_step = float(auction.recommended_bid_step or 100)
        min_allowed_bid = round(current_price + bid_step, 2)

        if bid.amount < min_allowed_bid:
            raise HTTPException(
                status_code=400,
                detail=f"Ставка слишком мала. Минимальная допустимая ставка: {min_allowed_bid}",
            )

        new_bid = Bid(
            auction_id=auction_id,
            user=bid.user,
            amount=float(bid.amount),
            created_at=datetime.utcnow(),
        )
        auction.current_price = float(bid.amount)

        db.add(new_bid)
        db.commit()
        db.refresh(auction)

        return {
            "message": "Ставка успешно принята",
            "auction_id": auction.id,
            "previous_price": current_price,
            "new_price": auction.current_price,
            "bid_step": bid_step,
            "min_allowed_bid": min_allowed_bid,
            "auction": _serialize_auction(db, auction, include_offers=True),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при размещении ставки: {exc}",
        )
    finally:
        db.close()


@router.get("/{auction_id}/bids")
def get_auction_bids(auction_id: int):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        bids = (
            db.query(Bid)
            .filter(Bid.auction_id == auction_id)
            .order_by(Bid.created_at.asc(), Bid.id.asc())
            .all()
        )
        return [_bid_to_dict(bid) for bid in bids]
    finally:
        db.close()


@router.post("/{auction_id}/recommend-bid")
def recommend_bid(auction_id: int, request: BidRecommendationRequest):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        _sync_auction_status(auction)
        if auction.status != "active":
            db.commit()
            raise HTTPException(status_code=400, detail="Аукцион завершен")

        current_price = float(auction.current_price or 0)
        bid_step = float(auction.recommended_bid_step or 100)
        min_allowed_bid = round(current_price + bid_step, 2)

        recommendation = calculate_recommended_bid(
            current_price=current_price,
            user_value=float(request.user_value),
            bid_step=bid_step,
        )

        analysis = auction.analysis or calculate_full_pricing(auction.questionnaire or {})

        return {
            "message": "Рекомендация ставки рассчитана по функции полезности",
            "auction_id": auction.id,
            "current_price": current_price,
            "bid_step": bid_step,
            "min_allowed_bid": min_allowed_bid,
            "user_value": float(request.user_value),
            "recommended_bid": recommendation,
            "expected_final_price": analysis.get("expected_final_price"),
            "auction_attractiveness": analysis.get("auction_attractiveness"),
            "formula": "s* = argmax U(s), U(s) = P_win(s) * (V_user - s)",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при расчете рекомендованной ставки: {exc}",
        )
    finally:
        db.close()


@router.post("/{auction_id}/bid-recommendation")
def recommend_bid_alias(auction_id: int, request: BidRecommendationRequest):
    return recommend_bid(auction_id, request)


@router.post("/{auction_id}/offer")
def make_offer(auction_id: int, offer: OfferCreate):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        _sync_auction_status(auction)
        if auction.status != "active":
            db.commit()
            raise HTTPException(status_code=400, detail="Аукцион завершен")

        current_price = float(auction.current_price or 0)
        if offer.amount <= current_price:
            raise HTTPException(
                status_code=400,
                detail=f"Оффер должен быть выше текущей цены: {current_price}",
            )

        analysis = auction.analysis or calculate_full_pricing(auction.questionnaire or {})
        expected_price = float(analysis["expected_final_price"])
        attractiveness = float(analysis.get("auction_attractiveness", 0.5))
        risk_discount = 0.12 + 0.18 * (1 - attractiveness)
        seller_wait_utility = round(expected_price * (1 - risk_discount), 2)

        bid_step = float(auction.recommended_bid_step or 100)
        if offer.amount >= seller_wait_utility:
            recommendation = "accept"
            counter_amount = None
        elif offer.amount >= current_price + bid_step:
            recommendation = "counteroffer"
            counter_amount = seller_wait_utility
        else:
            recommendation = "reject"
            counter_amount = round(current_price + bid_step, 2)

        new_offer = Offer(
            auction_id=auction_id,
            user=offer.user,
            amount=float(offer.amount),
            status="pending",
            recommendation=recommendation,
            seller_wait_utility=seller_wait_utility,
            risk_discount=round(risk_discount, 4),
            counter_amount=counter_amount,
            created_at=datetime.utcnow(),
        )

        db.add(new_offer)
        db.commit()
        db.refresh(new_offer)
        db.refresh(auction)

        return {
            "message": "Оффер отправлен продавцу. Модель рассчитала рекомендацию, но решение принимает продавец.",
            "offer": _offer_to_dict(new_offer),
            "expected_final_price": expected_price,
            "seller_wait_utility": seller_wait_utility,
            "risk_discount": round(risk_discount, 4),
            "recommendation": recommendation,
            "decision": "pending",
            "explanation": {
                "seller_wait_utility": "Порог, при котором продавцу рационально принять оффер вместо ожидания финала торгов.",
                "recommendation": "accept/counteroffer/reject — это рекомендация модели, а не автоматическое действие.",
            },
            "auction": _serialize_auction(db, auction, include_offers=True),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке оффера: {exc}",
        )
    finally:
        db.close()


@router.post("/{auction_id}/offers/{offer_id}/decision")
def decide_offer(auction_id: int, offer_id: int, decision: OfferDecisionRequest):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        offer = (
            db.query(Offer)
            .filter(Offer.id == offer_id, Offer.auction_id == auction_id)
            .first()
        )
        if not offer:
            raise HTTPException(status_code=404, detail="Оффер не найден")

        action = decision.action.lower().strip()
        if action not in {"accept", "reject", "counteroffer"}:
            raise HTTPException(
                status_code=400,
                detail="Действие должно быть accept, reject или counteroffer",
            )

        if action == "accept":
            offer.status = "accepted"
            auction.status = "finished"
            auction.current_price = float(offer.amount)
        elif action == "reject":
            offer.status = "rejected"
        else:
            offer.status = "counteroffer"
            offer.counter_amount = (
                float(decision.counter_amount)
                if decision.counter_amount and decision.counter_amount > 0
                else offer.counter_amount
            )

        offer.decided_at = datetime.utcnow()
        db.commit()
        db.refresh(offer)
        db.refresh(auction)

        return {
            "message": "Решение продавца по офферу сохранено",
            "offer": _offer_to_dict(offer),
            "auction": _serialize_auction(db, auction, include_offers=True),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке решения по офферу: {exc}",
        )
    finally:
        db.close()


@router.get("/{auction_id}/offers")
def get_auction_offers(auction_id: int):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        offers = (
            db.query(Offer)
            .filter(Offer.auction_id == auction_id)
            .order_by(Offer.created_at.asc(), Offer.id.asc())
            .all()
        )
        return [_offer_to_dict(offer) for offer in offers]
    finally:
        db.close()


@router.post("/upload-image")
def upload_image(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join("uploads", filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"image_url": f"http://127.0.0.1:8000/uploads/{filename}"}

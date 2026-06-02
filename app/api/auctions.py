import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from statistics import pstdev
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.db.models import Auction, AuctionInteraction, Bid, Offer, User
from app.api.auth import _get_current_user
from app.config import get_public_base_url
from app.pricing.math_core import calculate_full_pricing, calculate_recommended_bid
from app.pricing.recommendation_engine import (
    generate_user_advice,
)
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


class AuctionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    start_price: Optional[float] = None
    recommended_bid_step: Optional[float] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _to_utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _bid_to_dict(bid: Bid) -> Dict[str, Any]:
    return {
        "id": bid.id,
        "auction_id": bid.auction_id,
        "user_id": getattr(bid, "user_id", None),
        "user": bid.user,
        "amount": bid.amount,
        "created_at": _iso(getattr(bid, "created_at", None)),
    }


def _offer_to_dict(offer: Offer) -> Dict[str, Any]:
    return {
        "id": offer.id,
        "auction_id": offer.auction_id,
        "user_id": getattr(offer, "user_id", None),
        "user": offer.user,
        "amount": offer.amount,
        "status": offer.status,
        "recommendation": getattr(offer, "recommendation", None),
        "seller_wait_utility": getattr(offer, "seller_wait_utility", None),
        "risk_discount": getattr(offer, "risk_discount", None),
        "counter_amount": getattr(offer, "counter_amount", None),
        "created_at": _iso(getattr(offer, "created_at", None)),
        "decided_at": _iso(getattr(offer, "decided_at", None)),
        "flow": _offer_flow(offer.status),
    }


def _offer_to_public_dict(offer: Offer) -> Dict[str, Any]:
    result = {
        "id": offer.id,
        "auction_id": offer.auction_id,
        "user_id": getattr(offer, "user_id", None),
        "user": offer.user,
        "amount": offer.amount,
        "status": offer.status,
        "created_at": _iso(getattr(offer, "created_at", None)),
        "decided_at": _iso(getattr(offer, "decided_at", None)),
    }
    if offer.status == "counteroffer" and getattr(offer, "counter_amount", None):
        result["counter_amount"] = offer.counter_amount
    result["flow"] = _offer_flow(offer.status)
    return result


def _offer_flow(status: str) -> Dict[str, Any]:
    """Describe the real buyer-seller route for an offer lifecycle."""
    base = {
        "offer": "Оффер создаёт покупатель и отправляет продавцу как досрочное предложение цены.",
        "counteroffer": "Контроффер создаёт только продавец: это встречная цена вместо суммы покупателя.",
        "seller_inbox": "Продавец видит новые офферы во входящих офферах личного кабинета.",
        "buyer_inbox": "Покупатель видит свои офферы и ответы продавца в разделе «Мои офферы».",
    }
    states = {
        "pending": {
            "stage": "waiting_for_seller",
            "next_actor": "seller",
            "visible_to": ["buyer_my_offers", "seller_incoming_offers"],
            "meaning": "Оффер отправлен покупателем и ждёт решения продавца.",
        },
        "counteroffer": {
            "stage": "waiting_for_buyer",
            "next_actor": "buyer",
            "visible_to": ["buyer_my_offers", "seller_offer_history"],
            "meaning": "Продавец отправил встречную цену; покупатель должен принять или отклонить её.",
        },
        "accepted": {
            "stage": "finished",
            "next_actor": None,
            "visible_to": ["buyer_my_offers", "seller_offer_history"],
            "meaning": "Оффер принят, аукцион завершён по согласованной цене.",
        },
        "rejected": {
            "stage": "closed",
            "next_actor": None,
            "visible_to": ["buyer_my_offers", "seller_offer_history"],
            "meaning": "Оффер отклонён, торги продолжаются, если аукцион активен.",
        },
    }
    return {**base, **states.get(status, states["pending"])}


def _seller_name(auction: Auction) -> str:
    return getattr(auction, "seller_name", None) or "Кирилл"


def _seller_public_profile(db, auction: Auction, include_private: bool = False) -> Dict[str, Any]:
    seller = None
    seller_id = getattr(auction, "seller_id", None)
    if seller_id is not None:
        seller = db.query(User).filter(User.id == seller_id).first()

    display_name = (
        getattr(seller, "display_name", None)
        or getattr(seller, "username", None)
        or _seller_name(auction)
    )
    is_incognito = bool(getattr(seller, "is_incognito", False))
    is_finished = getattr(auction, "status", None) == "finished"

    return {
        "display_name": display_name if include_private or (is_finished and not is_incognito) else None,
        "is_incognito": is_incognito,
        "revealed": bool(include_private or (is_finished and not is_incognito)),
    }


def _is_auction_seller(user: Any, auction: Auction) -> bool:
    if not user:
        return False

    seller_id = getattr(auction, "seller_id", None)
    if seller_id is None:
        return False

    try:
        return int(seller_id) == int(user.id)
    except (TypeError, ValueError):
        return False


def _is_legacy_seller_name_match(user: Any, auction: Auction) -> bool:
    if not user:
        return False

    allowed_names = {
        (user.username or "").strip().lower(),
        (user.email or "").strip().lower(),
        (user.display_name or user.username or "").strip().lower(),
    }
    return _seller_name(auction).strip().lower() in allowed_names


def _require_seller_access(db, auction: Auction, authorization: Optional[str]):
    user = _get_current_user(db, authorization)
    if _is_auction_seller(user, auction):
        return user

    if getattr(auction, "seller_id", None) is None and _is_legacy_seller_name_match(user, auction):
        auction.seller_id = user.id
        db.flush()
        return user

    raise HTTPException(
        status_code=403,
        detail="Этим лотом может управлять только его продавец",
    )


def _get_optional_current_user(db, authorization: Optional[str]):
    if not authorization:
        return None
    try:
        return _get_current_user(db, authorization)
    except HTTPException:
        return None


def _get_interaction(db, auction_id: int, user_id: int) -> AuctionInteraction:
    interaction = (
        db.query(AuctionInteraction)
        .filter(
            AuctionInteraction.auction_id == auction_id,
            AuctionInteraction.user_id == user_id,
        )
        .first()
    )
    if interaction:
        return interaction

    interaction = AuctionInteraction(
        auction_id=auction_id,
        user_id=user_id,
        viewed=False,
        liked=False,
        favorited=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(interaction)
    db.flush()
    return interaction


def _sync_interaction_counts(db, auction: Auction) -> None:
    auction.views_count = (
        db.query(AuctionInteraction)
        .filter(
            AuctionInteraction.auction_id == auction.id,
            AuctionInteraction.viewed.is_(True),
        )
        .count()
    )
    auction.likes_count = (
        db.query(AuctionInteraction)
        .filter(
            AuctionInteraction.auction_id == auction.id,
            AuctionInteraction.liked.is_(True),
        )
        .count()
    )
    auction.favorites_count = (
        db.query(AuctionInteraction)
        .filter(
            AuctionInteraction.auction_id == auction.id,
            AuctionInteraction.favorited.is_(True),
        )
        .count()
    )


def _viewer_signals(db, auction_id: int, user_id: Optional[int]) -> Dict[str, bool]:
    if not user_id:
        return {"viewed": False, "liked": False, "favorited": False}

    interaction = (
        db.query(AuctionInteraction)
        .filter(
            AuctionInteraction.auction_id == auction_id,
            AuctionInteraction.user_id == user_id,
        )
        .first()
    )
    return {
        "viewed": bool(getattr(interaction, "viewed", False)) if interaction else False,
        "liked": bool(getattr(interaction, "liked", False)) if interaction else False,
        "favorited": bool(getattr(interaction, "favorited", False)) if interaction else False,
    }


def _sync_auction_status(auction: Auction) -> None:
    end_time = getattr(auction, "end_time", None)
    if auction.status == "active" and end_time and end_time <= datetime.utcnow():
        auction.status = "finished"
    if auction.status == "finished" and getattr(auction, "final_price", None) is None:
        auction.final_price = float(auction.current_price or 0)


def _safe_int(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _public_questionnaire(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    public_fields = {
        "brand",
        "category",
        "subcategory",
        "size",
        "color",
        "colors",
        "material",
        "style",
        "condition",
        "has_tag",
        "estimated_age",
        "defects",
        "seller_comment",
    }
    return {
        key: value
        for key, value in (questionnaire or {}).items()
        if key in public_fields
    }


def _auction_rule_explanations() -> Dict[str, str]:
    return {
        "minimum_bid": "Минимальная ставка равна текущей цене плюс установленный шаг ставки.",
        "anti_sniping": "Если ставка сделана меньше чем за 2 минуты до конца торгов, end_time продлевается на 2 минуты. Это защищает аукцион от последней мгновенной ставки.",
        "expired_auction": "После end_time новые ставки не принимаются: лот переводится в статус finished и фиксируется финальная цена.",
        "offer": "Оффер — предложение покупателя купить лот досрочно по своей цене. Он отображается у продавца во входящих офферах и у покупателя в разделе моих офферов.",
        "counteroffer": "Встречная цена продавца — ответ продавца на оффер покупателя. Покупатель видит её в своих офферах и может принять или отклонить.",
        "seller_decision": "Продавец может принять оффер, отклонить его, предложить встречную цену или принять любую ставку из истории ставок.",
    }


def _price_std_for_market(
    auction: Auction,
    bids: list[Bid],
    offers: list[Offer],
) -> float:
    prices = [
        _safe_float(getattr(auction, "start_price", 0)),
        _safe_float(getattr(auction, "current_price", 0)),
    ]
    prices.extend(_safe_float(bid.amount) for bid in bids)
    for offer in offers:
        prices.append(_safe_float(offer.amount))
        if getattr(offer, "counter_amount", None):
            prices.append(_safe_float(offer.counter_amount))

    clean_prices = [price for price in prices if price > 0]
    if len(clean_prices) < 2:
        return 0.0
    return round(float(pstdev(clean_prices)), 2)


def _refresh_live_analysis(
    auction: Auction,
    bids: list[Bid],
    offers: list[Offer],
    increment_view: bool = False,
) -> Dict[str, Any]:
    if increment_view:
        auction.views_count = _safe_int(getattr(auction, "views_count", 0)) + 1

    _sync_auction_status(auction)

    auction.total_bids = len(bids)
    likes_count = _safe_int(getattr(auction, "likes_count", 0))
    favorites_count = _safe_int(getattr(auction, "favorites_count", 0))
    views_count = _safe_int(getattr(auction, "views_count", 0))
    offers_count = len(offers)
    price_std = _price_std_for_market(auction, bids, offers)
    bidder_keys = {
        str(getattr(bid, "user_id", "") or getattr(bid, "user", "") or "").strip().lower()
        for bid in bids
        if str(getattr(bid, "user_id", "") or getattr(bid, "user", "") or "").strip()
    }
    bidders_count = len(bidder_keys)
    created_at = getattr(auction, "created_at", None)
    end_time = getattr(auction, "end_time", None)
    elapsed_hours = 0.0
    if created_at:
        elapsed_hours = max(1 / 60, (datetime.utcnow() - created_at).total_seconds() / 3600)
    bid_velocity = round(len(bids) / elapsed_hours, 4) if elapsed_hours > 0 else 0.0
    bid_time_fractions = []
    if created_at and end_time and end_time > created_at:
        duration_seconds = max(1.0, (end_time - created_at).total_seconds())
        for bid in bids:
            bid_created_at = getattr(bid, "created_at", None)
            if bid_created_at:
                bid_time_fractions.append(
                    max(
                        0.0,
                        min(1.0, (bid_created_at - created_at).total_seconds() / duration_seconds),
                    )
                )
    late_bid_share = (
        round(
            len([fraction for fraction in bid_time_fractions if fraction >= 0.8])
            / len(bid_time_fractions),
            4,
        )
        if bid_time_fractions
        else 0.0
    )
    last_bid_time_fraction = (
        round(max(bid_time_fractions), 4)
        if bid_time_fractions
        else 0.0
    )

    questionnaire = dict(auction.questionnaire or {})
    questionnaire.update(
        {
            "views_count": views_count,
            "likes_count": likes_count,
            "favorites_count": favorites_count,
            "bids_count": len(bids),
            "bidders_count": bidders_count,
            "offers_count": offers_count,
            "bid_velocity": bid_velocity,
            "price_std": price_std,
            "late_bid_share": late_bid_share,
            "last_bid_time_fraction": last_bid_time_fraction,
            "current_price": _safe_float(getattr(auction, "current_price", 0)),
            "start_price": _safe_float(getattr(auction, "start_price", 0)),
            "final_price": _safe_float(getattr(auction, "final_price", 0)),
            "status": getattr(auction, "status", "active"),
            "title": getattr(auction, "title", ""),
            "description": getattr(auction, "description", ""),
        }
    )

    previous_analysis = auction.analysis or {}
    analysis = calculate_full_pricing(questionnaire)
    initial_expected = previous_analysis.get("initial_expected_final_price")
    if initial_expected is None:
        initial_expected = previous_analysis.get("expected_final_price")
    if initial_expected is not None:
        analysis["initial_expected_final_price"] = round(_safe_float(initial_expected), 2)
    analysis["seller_final_start_price"] = previous_analysis.get(
        "seller_final_start_price",
        _safe_float(getattr(auction, "start_price", 0)),
    )
    current_bid_step = _safe_float(getattr(auction, "recommended_bid_step", 0))
    analysis["seller_final_bid_step"] = previous_analysis.get(
        "seller_final_bid_step",
        current_bid_step,
    )
    if current_bid_step > 0:
        analysis["recommended_bid_step"] = current_bid_step
    analysis["live_market_state"] = {
        "views_count": views_count,
        "likes_count": likes_count,
        "favorites_count": favorites_count,
        "bids_count": len(bids),
        "bidders_count": bidders_count,
        "offers_count": offers_count,
        "bid_velocity": bid_velocity,
        "price_std": price_std,
        "late_bid_share": late_bid_share,
        "last_bid_time_fraction": last_bid_time_fraction,
        "current_price": _safe_float(getattr(auction, "current_price", 0)),
        "final_price": _safe_float(getattr(auction, "final_price", 0)),
        "updated_at": datetime.utcnow().isoformat(),
    }

    auction.questionnaire = questionnaire
    auction.analysis = analysis
    if current_bid_step <= 0:
        auction.recommended_bid_step = float(
            analysis.get("recommended_bid_step") or auction.recommended_bid_step or 100
        )
    return analysis


def _serialize_auction(
    db,
    auction: Auction,
    include_offers: bool = False,
    include_private: bool = False,
    viewer_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    _sync_auction_status(auction)
    _sync_interaction_counts(db, auction)

    bids = (
        db.query(Bid)
        .filter(Bid.auction_id == auction.id)
        .order_by(Bid.created_at.asc(), Bid.id.asc())
        .all()
    )
    offers = (
        db.query(Offer)
        .filter(Offer.auction_id == auction.id)
        .order_by(Offer.created_at.asc(), Offer.id.asc())
        .all()
    )

    analysis = _refresh_live_analysis(
        auction=auction,
        bids=bids,
        offers=offers,
        increment_view=False,
    )
    db.flush()

    result = {
        "id": auction.id,
        "title": auction.title,
        "brand": auction.brand,
        "seller_name": _seller_name(auction),
        "seller_public_profile": _seller_public_profile(db, auction, include_private),
        "is_owner": bool(include_private),
        "description": auction.description,
        "current_price": auction.current_price,
        "start_price": auction.start_price,
        "final_price": getattr(auction, "final_price", None),
        "recommended_bid_step": auction.recommended_bid_step,
        "status": auction.status,
        "image_url": auction.image_url,
        "image_urls": auction.image_urls or [],
        "questionnaire": (
            auction.questionnaire or {}
        ) if include_private else _public_questionnaire(auction.questionnaire or {}),
        "views_count": _safe_int(getattr(auction, "views_count", 0)),
        "likes_count": _safe_int(getattr(auction, "likes_count", 0)),
        "favorites_count": _safe_int(getattr(auction, "favorites_count", 0)),
        "total_bids": _safe_int(getattr(auction, "total_bids", 0)),
        "created_at": _iso(getattr(auction, "created_at", None)),
        "end_time": _iso(getattr(auction, "end_time", None)),
        "bids": [_bid_to_dict(bid) for bid in bids],
        "viewer_signals": _viewer_signals(db, auction.id, viewer_user_id),
        "auction_rules": _auction_rule_explanations(),
    }

    if include_private:
        result["analysis"] = analysis
        result["conservative_final_price"] = analysis.get("conservative_final_price")
        result["expected_final_price"] = analysis.get("expected_final_price")
        result["optimistic_final_price"] = analysis.get("optimistic_final_price")
        result["initial_expected_final_price"] = analysis.get("initial_expected_final_price")
        result["auction_attractiveness"] = analysis.get("auction_attractiveness")
        result["auction_potential_pre"] = analysis.get("auction_potential_pre")
        result["auction_activity_live"] = analysis.get("auction_activity_live")
        result["confirmed_value_score"] = analysis.get("confirmed_value_score")
        result["auction_behavior_source"] = analysis.get("auction_behavior_source")
        result["bids_bucket"] = analysis.get("bids_bucket")
        result["auction_uplift"] = analysis.get("auction_uplift")
        result["pricing_confidence"] = analysis.get("pricing_confidence")

    if auction.status == "finished":
        winning_bid = bids[-1] if bids else None
        accepted_offer = next((offer for offer in offers if offer.status == "accepted"), None)
        result["final_summary"] = {
            "final_price": getattr(auction, "final_price", None) or auction.current_price,
            "winner": (
                getattr(winning_bid, "user", None)
                or getattr(accepted_offer, "user", None)
                or None
            ),
            "finished_at": _iso(getattr(auction, "end_time", None)),
            "source": "accepted_offer" if accepted_offer else "accepted_bid" if winning_bid else "manual_finish",
        }

    if include_offers and include_private:
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
def get_profile(user_name: str, authorization: Optional[str] = Header(default=None)):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        allowed_names = {
            (current_user.username or "").strip().lower(),
            (current_user.email or "").strip().lower(),
            (current_user.display_name or current_user.username or "").strip().lower(),
        }
        normalized_user = user_name.strip().lower()
        if normalized_user not in allowed_names:
            raise HTTPException(status_code=403, detail="Нельзя открыть чужой кабинет")

        profile_name = current_user.display_name or current_user.username
        auctions = db.query(Auction).order_by(Auction.id.desc()).all()
        bids = db.query(Bid).order_by(Bid.id.desc()).all()
        offers = db.query(Offer).order_by(Offer.id.desc()).all()

        auction_by_id = {auction.id: auction for auction in auctions}
        seller_auctions = []
        for auction in auctions:
            if _is_auction_seller(current_user, auction):
                seller_auctions.append(auction)
                continue

            if getattr(auction, "seller_id", None) is None and _is_legacy_seller_name_match(current_user, auction):
                auction.seller_id = current_user.id
                seller_auctions.append(auction)
        seller_auction_ids = {auction.id for auction in seller_auctions}

        user_bids = [
            bid
            for bid in bids
            if getattr(bid, "user_id", None) == current_user.id
            or (bid.user or "").strip().lower() in allowed_names
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
                "auction": _serialize_auction(
                    db,
                    auction,
                    include_offers=False,
                    include_private=False,
                    viewer_user_id=current_user.id,
                ),
                "my_last_bid": _bid_to_dict(bid),
                "is_leading": float(auction.current_price or 0) == float(bid.amount or 0),
            })

        sent_offers = [
            {
                "offer": _offer_to_dict(offer),
                "auction": _serialize_auction(
                    db,
                    auction_by_id[offer.auction_id],
                    include_offers=False,
                    include_private=False,
                    viewer_user_id=current_user.id,
                ),
            }
            for offer in offers
            if (
                getattr(offer, "user_id", None) == current_user.id
                or (offer.user or "").strip().lower() in allowed_names
            )
            and offer.auction_id in auction_by_id
        ]

        favorite_interactions = (
            db.query(AuctionInteraction)
            .filter(
                AuctionInteraction.user_id == current_user.id,
                AuctionInteraction.favorited.is_(True),
            )
            .order_by(AuctionInteraction.favorited_at.desc())
            .all()
        )
        favorite_lots = [
            {
                "auction": _serialize_auction(
                    db,
                    auction_by_id[interaction.auction_id],
                    include_offers=False,
                    include_private=False,
                    viewer_user_id=current_user.id,
                ),
                "favorited_at": _iso(getattr(interaction, "favorited_at", None)),
            }
            for interaction in favorite_interactions
            if interaction.auction_id in auction_by_id
        ]

        incoming_offers = [
            {
                "offer": _offer_to_dict(offer),
                "auction": _serialize_auction(
                    db,
                    auction_by_id[offer.auction_id],
                    include_offers=False,
                    include_private=True,
                    viewer_user_id=current_user.id,
                ),
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
                "id": current_user.id,
                "username": current_user.username,
                "name": profile_name,
                "email": current_user.email,
                "phone": getattr(current_user, "phone", None),
                "age": getattr(current_user, "age", None),
                "city": getattr(current_user, "city", None),
                "bio": getattr(current_user, "bio", None),
                "is_incognito": bool(getattr(current_user, "is_incognito", False)),
                "roles": ["buyer", "seller"],
                "rating": 4.9,
                "verification": "demo_verified",
                "avatar_url": getattr(current_user, "avatar_url", None),
            },
            "buyer": {
                "stats": {
                    "active_bids": len(buyer_lots),
                    "leading_bids": sum(1 for item in buyer_lots if item["is_leading"]),
                    "sent_offers": len(sent_offers),
                    "pending_offers": sum(
                        1 for item in sent_offers if item["offer"]["status"] == "pending"
                    ),
                    "favorites": len(favorite_lots),
                },
                "bids": buyer_lots,
                "offers": sent_offers,
                "favorites": favorite_lots,
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
                    _serialize_auction(
                        db,
                        auction,
                        include_offers=True,
                        include_private=True,
                        viewer_user_id=current_user.id,
                    )
                    for auction in seller_auctions
                ],
                "incoming_offers": incoming_offers,
            },
        }
    finally:
        db.commit()
        db.close()


@router.get("/favorites")
def get_favorites(authorization: Optional[str] = Header(default=None)):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        interactions = (
            db.query(AuctionInteraction)
            .filter(
                AuctionInteraction.user_id == current_user.id,
                AuctionInteraction.favorited.is_(True),
            )
            .order_by(AuctionInteraction.favorited_at.desc())
            .all()
        )
        auction_ids = [interaction.auction_id for interaction in interactions]
        auctions = (
            db.query(Auction)
            .filter(Auction.id.in_(auction_ids))
            .all()
            if auction_ids
            else []
        )
        auction_by_id = {auction.id: auction for auction in auctions}

        favorites = [
            {
                "auction": _serialize_auction(
                    db,
                    auction_by_id[interaction.auction_id],
                    include_offers=False,
                    include_private=False,
                    viewer_user_id=current_user.id,
                ),
                "favorited_at": _iso(getattr(interaction, "favorited_at", None)),
            }
            for interaction in interactions
            if interaction.auction_id in auction_by_id
        ]
        db.commit()
        return {"favorites": favorites}
    finally:
        db.close()


@router.get("/{auction_id}")
def get_auction(
    auction_id: int,
    authorization: Optional[str] = Header(default=None),
    seller_view: bool = Query(default=False),
):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        current_user = _get_optional_current_user(db, authorization)
        is_seller = _is_auction_seller(current_user, auction)

        if current_user:
            interaction = _get_interaction(db, auction.id, current_user.id)
            if not interaction.viewed:
                interaction.viewed = True
                interaction.viewed_at = datetime.utcnow()
            interaction.updated_at = datetime.utcnow()
            db.flush()

        result = _serialize_auction(
            db,
            auction,
            include_offers=is_seller and seller_view,
            include_private=is_seller and seller_view,
            viewer_user_id=getattr(current_user, "id", None),
        )
        db.commit()
        return result
    finally:
        db.close()


@router.patch("/{auction_id}")
def update_auction(
    auction_id: int,
    payload: AuctionUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        current_user = _require_seller_access(db, auction, authorization)
        data = payload.dict(exclude_unset=True)
        bids_count = db.query(Bid).filter(Bid.auction_id == auction.id).count()

        if auction.status == "finished":
            locked_fields = set(data) - {"description"}
            if locked_fields:
                raise HTTPException(
                    status_code=400,
                    detail="Завершённый лот нельзя менять, кроме описания",
                )

        if "title" in data and data["title"] is not None:
            auction.title = data["title"].strip() or auction.title

        if "description" in data and data["description"] is not None:
            auction.description = data["description"].strip()

        if "image_url" in data and data["image_url"] is not None:
            auction.image_url = data["image_url"].strip() or auction.image_url

        if "image_urls" in data and data["image_urls"] is not None:
            clean_urls = [
                str(url).strip()
                for url in data["image_urls"]
                if str(url or "").strip()
            ]
            auction.image_urls = clean_urls
            if clean_urls:
                auction.image_url = clean_urls[0]

        if "start_price" in data and data["start_price"] is not None:
            start_price = float(data["start_price"])
            if start_price <= 0:
                raise HTTPException(status_code=400, detail="Стартовая цена должна быть больше 0")
            if bids_count > 0 and round(start_price, 2) != round(float(auction.start_price or 0), 2):
                raise HTTPException(
                    status_code=400,
                    detail="Стартовую цену можно менять только до первой ставки",
                )
            old_start = float(auction.start_price or 0)
            auction.start_price = round(start_price, 2)
            if bids_count == 0 or float(auction.current_price or 0) <= old_start:
                auction.current_price = round(start_price, 2)

        if "recommended_bid_step" in data and data["recommended_bid_step"] is not None:
            bid_step = float(data["recommended_bid_step"])
            if bid_step <= 0:
                raise HTTPException(status_code=400, detail="Шаг ставки должен быть больше 0")
            auction.recommended_bid_step = round(bid_step, 2)

        if "end_time" in data and data["end_time"] is not None:
            end_time = _to_utc_naive(data["end_time"])
            if end_time and auction.status == "active" and end_time <= datetime.utcnow():
                raise HTTPException(status_code=400, detail="Время окончания должно быть в будущем")
            auction.end_time = end_time

        if "status" in data and data["status"] is not None:
            status = data["status"].strip().lower()
            if status not in {"active", "finished"}:
                raise HTTPException(status_code=400, detail="Статус может быть только active или finished")
            auction.status = status
            if status == "finished":
                auction.final_price = float(auction.current_price or 0)
                auction.end_time = datetime.utcnow()
            else:
                auction.final_price = None

        auction_payload = _serialize_auction(
            db,
            auction,
            include_offers=True,
            include_private=True,
            viewer_user_id=current_user.id,
        )
        db.commit()

        return {
            "message": "Лот обновлён",
            "auction": auction_payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении лота: {exc}",
        )
    finally:
        db.close()


@router.post("/{auction_id}/like")
def like_auction(
    auction_id: int,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        interaction = _get_interaction(db, auction.id, current_user.id)
        interaction.liked = not bool(interaction.liked)
        interaction.liked_at = datetime.utcnow() if interaction.liked else None
        interaction.updated_at = datetime.utcnow()
        db.flush()

        auction_payload = _serialize_auction(db, auction, viewer_user_id=current_user.id)
        db.commit()
        return {"message": "Лайк учтён", "auction": auction_payload}
    finally:
        db.close()


@router.post("/{auction_id}/favorite")
def favorite_auction(
    auction_id: int,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        interaction = _get_interaction(db, auction.id, current_user.id)
        interaction.favorited = not bool(interaction.favorited)
        interaction.favorited_at = datetime.utcnow() if interaction.favorited else None
        interaction.updated_at = datetime.utcnow()
        db.flush()

        auction_payload = _serialize_auction(db, auction, viewer_user_id=current_user.id)
        db.commit()
        return {"message": "Избранное обновлено", "auction": auction_payload}
    finally:
        db.close()


@router.post("/")
def create_auction(
    lot: LotCreate,
    authorization: Optional[str] = Header(default=None),
):
    db = None
    try:
        db = SessionLocal()
        current_user = _get_current_user(db, authorization)
        questionnaire_dict = {
            **lot.questionnaire.dict(),
            "title": lot.title,
            "description": lot.description,
        }
        pricing_result = calculate_full_pricing(questionnaire_dict)
        final_start_price = (
            float(lot.start_price)
            if lot.start_price and lot.start_price > 0
            else pricing_result["recommended_start_price"]
        )
        pricing_questionnaire = {
            **questionnaire_dict,
            "start_price": round(final_start_price, 2),
            "current_price": round(final_start_price, 2),
            "status": "active",
        }
        pricing_result = calculate_full_pricing(pricing_questionnaire)
        final_bid_step = (
            float(lot.bid_step_override)
            if lot.bid_step_override and lot.bid_step_override > 0
            else pricing_result["recommended_bid_step"]
        )
        pricing_result["seller_final_start_price"] = round(final_start_price, 2)
        pricing_result["seller_final_bid_step"] = round(final_bid_step, 2)
        pricing_result["initial_expected_final_price"] = round(
            _safe_float(pricing_result.get("expected_final_price")),
            2,
        )
        now = datetime.utcnow()
        end_time = _to_utc_naive(lot.end_time) or now + timedelta(days=7)

        if end_time <= now:
            raise HTTPException(
                status_code=400,
                detail="Время окончания аукциона должно быть позже текущего времени",
            )

        new_auction = Auction(
            image_url=lot.image_url,
            image_urls=lot.image_urls,
            title=lot.title,
            brand=lot.questionnaire.brand or "unknown",
            seller_id=current_user.id,
            seller_name=current_user.display_name
            or current_user.username
            or current_user.email
            or lot.seller_name
            or "seller",
            current_price=round(final_start_price, 2),
            start_price=round(final_start_price, 2),
            description=lot.description,
            status="active",
            recommended_bid_step=round(final_bid_step, 2),
            questionnaire=pricing_questionnaire,
            analysis=pricing_result,
            created_at=now,
            end_time=end_time,
        )

        db.add(new_auction)
        db.commit()
        db.refresh(new_auction)

        auction_payload = _serialize_auction(
            db,
            new_auction,
            include_offers=True,
            include_private=True,
            viewer_user_id=current_user.id,
        )
        db.commit()

        return {
            "message": "Аукцион создан на основе математической модели ценообразования",
            "auction": auction_payload,
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
def place_bid(
    auction_id: int,
    bid: BidCreate,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")
        if _is_auction_seller(current_user, auction):
            raise HTTPException(status_code=400, detail="Продавец не может делать ставки на свой лот")

        now = datetime.utcnow()
        end_time = getattr(auction, "end_time", None)
        if end_time and end_time <= now:
            auction.status = "finished"
            if getattr(auction, "final_price", None) is None:
                auction.final_price = float(auction.current_price or 0)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Аукцион завершён: время торгов истекло, новые ставки не принимаются",
            )

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
            user_id=current_user.id,
            user=current_user.display_name or current_user.username,
            amount=float(bid.amount),
            created_at=now,
        )
        auction.current_price = float(bid.amount)

        auction_extended = False
        new_end_time = None
        if end_time and end_time - now <= timedelta(minutes=2):
            auction.end_time = end_time + timedelta(minutes=2)
            auction_extended = True
            new_end_time = _iso(auction.end_time)

        db.add(new_bid)
        db.commit()
        db.refresh(auction)

        auction_payload = _serialize_auction(db, auction)
        db.commit()

        return {
            "message": "Ставка успешно принята",
            "auction_id": auction.id,
            "previous_price": current_price,
            "new_price": auction.current_price,
            "bid_step": bid_step,
            "min_allowed_bid": min_allowed_bid,
            "auction_extended": auction_extended,
            "new_end_time": new_end_time,
            "rule_explanation": {
                "minimum_bid": "Ставка принимается только если amount >= current_price + recommended_bid_step.",
                "anti_sniping": "Если ставка сделана меньше чем за 2 минуты до конца торгов, end_time продлевается на 2 минуты.",
            },
            "auction": auction_payload,
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


@router.post("/{auction_id}/bids/{bid_id}/accept")
def accept_bid_as_seller(
    auction_id: int,
    bid_id: int,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        current_user = _require_seller_access(db, auction, authorization)

        bid = (
            db.query(Bid)
            .filter(Bid.id == bid_id, Bid.auction_id == auction_id)
            .first()
        )
        if not bid:
            raise HTTPException(status_code=404, detail="Ставка не найдена")

        auction.status = "finished"
        auction.current_price = float(bid.amount)
        auction.final_price = float(bid.amount)
        auction.end_time = datetime.utcnow()

        auction_payload = _serialize_auction(
            db,
            auction,
            include_offers=True,
            include_private=True,
            viewer_user_id=current_user.id,
        )
        db.commit()

        return {
            "message": "Продавец принял ставку и завершил аукцион",
            "accepted_bid": _bid_to_dict(bid),
            "auction": auction_payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при принятии ставки: {exc}",
        )
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
        recommendation_pricing_data = {
            **analysis,
            "recommended_bid_step": bid_step,
        }

        return {
            "message": "Рекомендация ставки рассчитана по функции полезности",
            "auction_id": auction.id,
            "current_price": current_price,
            "bid_step": bid_step,
            "min_allowed_bid": min_allowed_bid,
            "user_value": float(request.user_value),
            "recommended_bid": recommendation,
            "user_advice": generate_user_advice(
                recommendation_pricing_data,
                current_price,
                float(request.user_value),
            ),
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
def make_offer(
    auction_id: int,
    offer: OfferCreate,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")
        if _is_auction_seller(current_user, auction):
            raise HTTPException(status_code=400, detail="Продавец не может отправлять оффер по своему лоту")

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
        attractiveness = float(
            analysis.get("auction_activity_live", analysis.get("auction_attractiveness", 0.5))
        )
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
            user_id=current_user.id,
            user=current_user.display_name or current_user.username,
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
        auction_payload = _serialize_auction(db, auction, include_offers=True)
        db.commit()

        return {
            "message": "Оффер отправлен продавцу. Решение принимает владелец лота.",
            "offer": _offer_to_public_dict(new_offer),
            "decision": "pending",
            "offer_flow": _offer_flow(new_offer.status),
            "auction": auction_payload,
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
def decide_offer(
    auction_id: int,
    offer_id: int,
    decision: OfferDecisionRequest,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        current_user = _require_seller_access(db, auction, authorization)

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
            auction.final_price = float(offer.amount)
            auction.end_time = datetime.utcnow()
        elif action == "reject":
            offer.status = "rejected"
        else:
            counter_amount = (
                float(decision.counter_amount)
                if decision.counter_amount and decision.counter_amount > 0
                else float(offer.counter_amount or 0)
            )
            if counter_amount <= 0:
                raise HTTPException(status_code=400, detail="Укажите встречную цену продавца")
            if counter_amount <= float(offer.amount or 0):
                raise HTTPException(
                    status_code=400,
                    detail="Встречная цена должна быть выше оффера покупателя",
                )
            offer.status = "counteroffer"
            offer.counter_amount = round(counter_amount, 2)

        offer.decided_at = datetime.utcnow()
        db.commit()
        db.refresh(offer)
        db.refresh(auction)
        auction_payload = _serialize_auction(
            db,
            auction,
            include_offers=True,
            include_private=True,
            viewer_user_id=current_user.id,
        )
        db.commit()

        return {
            "message": "Решение продавца по офферу сохранено",
            "offer": _offer_to_dict(offer),
            "offer_flow": _offer_flow(offer.status),
            "auction": auction_payload,
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


@router.post("/{auction_id}/offers/{offer_id}/buyer-decision")
def decide_counteroffer_as_buyer(
    auction_id: int,
    offer_id: int,
    decision: OfferDecisionRequest,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        current_user = _get_current_user(db, authorization)
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

        allowed_names = {
            (current_user.username or "").strip().lower(),
            (current_user.email or "").strip().lower(),
            (current_user.display_name or current_user.username or "").strip().lower(),
        }
        offer_user_id = getattr(offer, "user_id", None)
        owns_offer = (
            offer_user_id == current_user.id
            if offer_user_id is not None
            else (offer.user or "").strip().lower() in allowed_names
        )
        if not owns_offer:
            raise HTTPException(status_code=403, detail="Можно отвечать только на свои офферы")

        if offer.status != "counteroffer":
            raise HTTPException(status_code=400, detail="Ответ покупателя возможен только на встречную цену продавца")

        action = decision.action.lower().strip()
        if action not in {"accept", "reject"}:
            raise HTTPException(status_code=400, detail="Действие должно быть accept или reject")

        if action == "accept":
            amount = float(offer.counter_amount or offer.amount)
            offer.status = "accepted"
            auction.status = "finished"
            auction.current_price = amount
            auction.final_price = amount
            auction.end_time = datetime.utcnow()
        else:
            offer.status = "rejected"

        offer.decided_at = datetime.utcnow()
        db.commit()
        db.refresh(offer)
        db.refresh(auction)
        auction_payload = _serialize_auction(
            db,
            auction,
            include_offers=False,
            include_private=False,
            viewer_user_id=current_user.id,
        )
        db.commit()

        return {
            "message": "Ответ покупателя на встречную цену сохранён",
            "offer": _offer_to_dict(offer),
            "offer_flow": _offer_flow(offer.status),
            "auction": auction_payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при ответе на встречную цену: {exc}",
        )
    finally:
        db.close()


@router.get("/{auction_id}/offers")
def get_auction_offers(
    auction_id: int,
    authorization: Optional[str] = Header(default=None),
):
    db = SessionLocal()
    try:
        auction = db.query(Auction).filter(Auction.id == auction_id).first()
        if not auction:
            raise HTTPException(status_code=404, detail="Аукцион не найден")

        _require_seller_access(db, auction, authorization)

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

    return {"image_url": f"{get_public_base_url()}/uploads/{filename}"}

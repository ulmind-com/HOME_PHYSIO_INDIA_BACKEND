"""Commission & payout endpoints for therapists and admin."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.exceptions import ForbiddenException
from app.core.responses import success_response
from app.dependencies.auth import ActorContext, get_current_active_user, require_permission
from app.models.user import User
from app.services.commission_service import commission_service

router = APIRouter(prefix="/commissions", tags=["Commissions & Payouts"])


# ── Schemas ──────────────────────────────────────────────────────────

class CreatePayoutRequest(BaseModel):
    therapist_id: str
    period_start: dt.date
    period_end: dt.date
    admin_notes: Optional[str] = None


class MarkPaidRequest(BaseModel):
    payment_method: str = Field(..., description="bank_transfer | upi | cash | other")
    transaction_reference: str = Field(..., description="UTR / UPI ref / receipt number")
    admin_notes: Optional[str] = None


class MarkFailedRequest(BaseModel):
    admin_notes: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _doc_to_dict(doc) -> dict:
    """Convert a Beanie document to a JSON-friendly dict."""
    d = doc.model_dump(mode="json")
    d["id"] = str(doc.id)
    d.pop("_id", None)
    return d


# ── Therapist Self-Service ───────────────────────────────────────────

@router.get("/my-summary", summary="Get my earnings summary (therapist)")
async def get_my_summary(user: User = Depends(get_current_active_user)) -> dict:
    """Therapist sees their total pending, settled, reversed earnings."""
    if user.role != "therapist":
        raise ForbiddenException("Only therapists can access this endpoint")
    summary = await commission_service.get_therapist_summary(str(user.id))
    return success_response(data=summary, message="Earnings summary fetched")


@router.get("/my-earnings", summary="List my earnings (therapist)")
async def get_my_earnings(
    status: Optional[str] = Query(None, description="pending | settled | reversed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_active_user),
) -> dict:
    """Therapist sees individual earning entries from completed bookings."""
    if user.role != "therapist":
        raise ForbiddenException("Only therapists can access this endpoint")
    items, total = await commission_service.get_therapist_earnings(
        str(user.id), status=status, page=page, page_size=page_size
    )
    return success_response(
        data={
            "items": [_doc_to_dict(e) for e in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="Earnings fetched",
    )


@router.get("/my-payouts", summary="List my payouts (therapist)")
async def get_my_payouts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_active_user),
) -> dict:
    """Therapist sees their payout settlement history."""
    if user.role != "therapist":
        raise ForbiddenException("Only therapists can access this endpoint")
    items, total = await commission_service.get_therapist_payouts(
        str(user.id), page=page, page_size=page_size
    )
    return success_response(
        data={
            "items": [_doc_to_dict(p) for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="Payouts fetched",
    )


# ── Admin Endpoints ─────────────────────────────────────────────────

@router.get("/therapist-summaries", summary="All therapist earnings summaries (admin)")
async def get_all_summaries(
    _: ActorContext = Depends(require_permission("commissions", "view")),
) -> dict:
    """Admin sees aggregated earnings per therapist."""
    summaries = await commission_service.get_all_therapist_summaries()
    return success_response(data=summaries, message="Therapist summaries fetched")


@router.get("/earnings", summary="List all earnings (admin)")
async def list_all_earnings(
    status: Optional[str] = Query(None),
    therapist_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _: ActorContext = Depends(require_permission("commissions", "view")),
) -> dict:
    items, total = await commission_service.list_all_earnings(
        page=page, page_size=page_size, status=status, therapist_id=therapist_id
    )
    return success_response(
        data={
            "items": [_doc_to_dict(e) for e in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="All earnings fetched",
    )


@router.get("/payouts", summary="List all payouts (admin)")
async def list_all_payouts(
    status: Optional[str] = Query(None),
    therapist_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _: ActorContext = Depends(require_permission("commissions", "view")),
) -> dict:
    items, total = await commission_service.list_all_payouts(
        page=page, page_size=page_size, status=status, therapist_id=therapist_id
    )
    return success_response(
        data={
            "items": [_doc_to_dict(p) for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        message="All payouts fetched",
    )


@router.post("/payouts", status_code=201, summary="Create a payout for a therapist (admin)")
async def create_payout(
    payload: CreatePayoutRequest,
    actor: ActorContext = Depends(require_permission("commissions", "update")),
) -> dict:
    payout = await commission_service.create_payout(
        therapist_id=payload.therapist_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        admin_id=actor.user_id,
        admin_name=actor.email,
        admin_notes=payload.admin_notes,
    )
    return success_response(data=_doc_to_dict(payout), message="Payout created — earnings marked as settled")


@router.patch("/payouts/{payout_id}/mark-paid", summary="Mark a payout as paid (admin)")
async def mark_payout_paid(
    payout_id: str,
    payload: MarkPaidRequest,
    actor: ActorContext = Depends(require_permission("commissions", "update")),
) -> dict:
    payout = await commission_service.mark_payout_paid(
        payout_id=payout_id,
        payment_method=payload.payment_method,
        transaction_reference=payload.transaction_reference,
        admin_id=actor.user_id,
        admin_name=actor.email,
        admin_notes=payload.admin_notes,
    )
    return success_response(data=_doc_to_dict(payout), message="Payout marked as paid")


@router.patch("/payouts/{payout_id}/mark-failed", summary="Mark a payout as failed (admin)")
async def mark_payout_failed(
    payout_id: str,
    payload: MarkFailedRequest,
    actor: ActorContext = Depends(require_permission("commissions", "update")),
) -> dict:
    payout = await commission_service.mark_payout_failed(
        payout_id=payout_id,
        admin_notes=payload.admin_notes,
    )
    return success_response(data=_doc_to_dict(payout), message="Payout marked as failed — earnings reverted to pending")

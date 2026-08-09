import math
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.elder_care import ElderCareRequest
from app.api.deps import current_superuser

router = APIRouter()

class ElderCareCreate(BaseModel):
    full_name: str
    phone_number: str
    city: str
    service_type: str
    patient_condition: Optional[str] = None
    preferred_duty_hours: Optional[str] = None

class ElderCareResponse(BaseModel):
    id: str
    full_name: str
    phone_number: str
    city: str
    service_type: str
    patient_condition: Optional[str] = None
    preferred_duty_hours: Optional[str] = None
    status: str
    created_at: str

    @classmethod
    def from_doc(cls, doc: ElderCareRequest) -> "ElderCareResponse":
        return cls(
            id=str(doc.id),
            full_name=doc.full_name,
            phone_number=doc.phone_number,
            city=doc.city,
            service_type=doc.service_type,
            patient_condition=doc.patient_condition,
            preferred_duty_hours=doc.preferred_duty_hours,
            status=doc.status,
            created_at=doc.created_at.isoformat() if doc.created_at else "",
        )

class ElderCareListResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[ElderCareResponse]

class ElderCareStatusUpdate(BaseModel):
    status: str

@router.post("", response_model=ElderCareResponse)
async def create_elder_care_request(req: ElderCareCreate):
    """Submit a new elder care request (Public)."""
    doc = ElderCareRequest(
        full_name=req.full_name,
        phone_number=req.phone_number,
        city=req.city,
        service_type=req.service_type,
        patient_condition=req.patient_condition,
        preferred_duty_hours=req.preferred_duty_hours,
    )
    await doc.insert()
    return ElderCareResponse.from_doc(doc)

@router.get("", response_model=ElderCareListResponse)
async def list_elder_care_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user=Depends(current_superuser),
):
    """List all elder care requests (Admin)."""
    query = {}
    if status:
        query["status"] = status
        
    total = await ElderCareRequest.find(query).count()
    docs = (
        await ElderCareRequest.find(query)
        .sort("-created_at")
        .skip((page - 1) * size)
        .limit(size)
        .to_list()
    )
    
    return ElderCareListResponse(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 1,
        items=[ElderCareResponse.from_doc(d) for d in docs],
    )

@router.patch("/{request_id}", response_model=ElderCareResponse)
async def update_elder_care_status(
    request_id: str,
    req: ElderCareStatusUpdate,
    current_user=Depends(current_superuser),
):
    """Update status of an elder care request (Admin)."""
    doc = await ElderCareRequest.get(request_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Request not found")
        
    doc.status = req.status
    await doc.save()
    return ElderCareResponse.from_doc(doc)

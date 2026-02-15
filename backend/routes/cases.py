from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime

from database import get_db
from models import InvestigationCase, ComplianceAudit, Provider

router = APIRouter(
    prefix="/api/cases",
    tags=["case-management"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
def list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List investigation cases with filters."""
    query = db.query(InvestigationCase)
    
    if status:
        query = query.filter(InvestigationCase.status == status)
    if priority:
        query = query.filter(InvestigationCase.priority == priority)
        
    total = query.count()
    cases = query.offset(skip).limit(limit).all()
    
    return {"total": total, "cases": cases}

@router.post("/")
def create_case(
    provider_id: int,
    description: str,
    priority: str = "medium",
    db: Session = Depends(get_db)
):
    """Create a new investigation case."""
    import uuid
    case_number = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    
    new_case = InvestigationCase(
        case_number=case_number,
        provider_id=provider_id,
        description=description,
        priority=priority,
        status="new"
    )
    
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    # Audit Log
    audit = ComplianceAudit(
        case_id=new_case.id,
        user_id="system",
        action="case_created",
        details={"priority": priority}
    )
    db.add(audit)
    db.commit()
    
    return new_case

@router.get("/{case_id}")
def get_case_details(case_id: int, db: Session = Depends(get_db)):
    """Get full details of a specific case."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.put("/{case_id}/status")
def update_case_status(
    case_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """Update case workflow status."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    old_status = case.status
    case.status = status
    
    # Audit Log
    audit = ComplianceAudit(
        case_id=case.id,
        user_id="system",
        action="status_change",
        details={"old": old_status, "new": status}
    )
    db.add(audit)
    db.commit()
    
    return case


@router.put("/{case_id}/assign")
def assign_investigator(
    case_id: int,
    investigator_id: str,
    db: Session = Depends(get_db),
):
    """Assign an investigator to a case."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    old_investigator = case.assigned_investigator_id
    case.assigned_investigator_id = investigator_id
    if case.status == "new":
        case.status = "assigned"

    audit = ComplianceAudit(
        case_id=case.id,
        user_id="system",
        action="investigator_assigned",
        details={"old": old_investigator, "new": investigator_id},
    )
    db.add(audit)
    db.commit()

    return case


@router.post("/{case_id}/notes")
def add_investigator_note(
    case_id: int,
    note: str,
    user_id: str = "system",
    db: Session = Depends(get_db),
):
    """Add an investigator note to the case audit trail."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    audit = ComplianceAudit(
        case_id=case.id,
        user_id=user_id,
        action="note_added",
        details={"note": note},
    )
    db.add(audit)
    db.commit()

    return {"case_id": case_id, "action": "note_added", "user_id": user_id}


@router.post("/{case_id}/tags")
def add_case_tag(
    case_id: int,
    tag: str,
    db: Session = Depends(get_db),
):
    """Add a tag to a case for categorization and filtering."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    audit = ComplianceAudit(
        case_id=case.id,
        user_id="system",
        action="tag_added",
        details={"tag": tag},
    )
    db.add(audit)
    db.commit()

    return {"case_id": case_id, "tag": tag, "action": "tag_added"}


@router.get("/{case_id}/audit-trail")
def get_case_audit_trail(
    case_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get the full audit trail for a case (notes, status changes, tags)."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    entries = (
        db.query(ComplianceAudit)
        .filter(ComplianceAudit.case_id == case_id)
        .order_by(ComplianceAudit.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "case_id": case_id,
        "audit_trail": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "action": e.action,
                "details": e.details,
                "timestamp": str(e.timestamp) if e.timestamp else None,
            }
            for e in entries
        ],
    }


@router.get("/queue/investigation")
def get_investigation_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_to: Optional[str] = Query(None, description="Filter by investigator"),
    min_fraud_amount: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("priority", description="Sort field"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get the investigation queue with filtering and sorting.

    This is the primary work queue for investigators and attorneys.
    Returns cases ranked by priority and estimated fraud amount.
    """
    query = db.query(InvestigationCase)

    if status:
        query = query.filter(InvestigationCase.status == status)
    else:
        # By default show active cases (exclude closed)
        query = query.filter(InvestigationCase.status != "closed")
    if priority:
        query = query.filter(InvestigationCase.priority == priority)
    if assigned_to:
        query = query.filter(
            InvestigationCase.assigned_investigator_id == assigned_to
        )
    if min_fraud_amount is not None:
        query = query.filter(
            InvestigationCase.estimated_fraud_amount >= min_fraud_amount
        )

    # Sort
    if sort_by == "fraud_amount":
        query = query.order_by(InvestigationCase.estimated_fraud_amount.desc().nullslast())
    elif sort_by == "date":
        query = query.order_by(InvestigationCase.opened_at.desc())
    else:
        # Default: high priority first, then by date
        # Use CASE to ensure correct priority ordering (not alphabetical)
        from sqlalchemy import case as sql_case
        priority_sort = sql_case(
            (InvestigationCase.priority == "high", 1),
            (InvestigationCase.priority == "medium", 2),
            (InvestigationCase.priority == "low", 3),
            else_=4,
        )
        query = query.order_by(
            priority_sort,
            InvestigationCase.opened_at.desc(),
        )

    total = query.count()
    cases = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "queue": [
            {
                "id": c.id,
                "case_number": c.case_number,
                "provider_id": c.provider_id,
                "status": c.status,
                "priority": c.priority,
                "assigned_to": c.assigned_investigator_id,
                "description": c.description,
                "estimated_fraud_amount": c.estimated_fraud_amount,
                "detection_source": c.detection_source,
                "opened_at": str(c.opened_at) if c.opened_at else None,
                "due_date": str(c.due_date) if c.due_date else None,
            }
            for c in cases
        ],
    }

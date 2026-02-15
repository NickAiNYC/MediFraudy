from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

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
    # Generate Case Number (Simple implementation)
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
        user_id="system", # Replace with actual user
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

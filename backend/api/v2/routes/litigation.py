"""
Litigation and evidence package API routes for law offices
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database_v2 import get_async_db
from services.evidence_builder_v2 import EvidencePackageBuilder
from background_jobs import job_manager, schedule_evidence_package
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/litigation", tags=["Litigation"])

@router.post("/evidence-package/{provider_id}")
async def generate_evidence_package(
    provider_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Generate complete litigation-ready evidence package"""
    
    try:
        # Quick validation
        result = await db.execute(text("SELECT COUNT(*) FROM providers WHERE id = :provider_id"), {"provider_id": provider_id})
        if result.scalar() == 0:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Schedule background job for evidence generation
        job_id = await schedule_evidence_package(provider_id)
        
        return {
            "status": "evidence_package_generating",
            "job_id": job_id,
            "provider_id": provider_id,
            "estimated_completion": "5-10 minutes",
            "package_contents": [
                "Provider Intelligence Dossier",
                "Fraud Pattern Analysis", 
                "Damage Calculations",
                "Expert Report Foundation",
                "Evidence Timeline",
                "Similar Cases Precedent",
                "FCA Complaint Template"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error generating evidence package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evidence-package/{job_id}")
async def get_evidence_package(job_id: str):
    """Get generated evidence package"""
    
    job = await job_manager.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Evidence generation failed: {job.get('error', 'Unknown error')}")
    
    if job["status"] != "completed":
        return {
            "status": job["status"],
            "progress": job.get("progress", 0),
            "message": "Evidence package is being generated..."
        }
    
    return {
        "status": "completed",
        "evidence_package": job.get("result", {}),
        "generated_at": job.get("completed_at"),
        "package_id": job.get("result", {}).get("package_id")
    }

@router.get("/case-assessment/{provider_id}")
async def quick_case_assessment(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Quick case assessment for initial client consultation"""
    
    try:
        builder = EvidencePackageBuilder(db)
        
        # Quick provider stats
        result = await db.execute(text("""
            SELECT 
                p.name,
                p.npi,
                p.city,
                p.state,
                COUNT(c.id) as claim_count,
                COALESCE(SUM(c.amount), 0) as total_amount,
                COALESCE(AVG(c.amount), 0) as avg_amount,
                COUNT(DISTINCT c.beneficiary_id) as unique_beneficiaries
            FROM providers p
            LEFT JOIN claims c ON p.id = c.provider_id
            WHERE p.id = :provider_id
            GROUP BY p.id, p.name, p.npi, p.city, p.state
        """), {"provider_id": provider_id})
        
        provider_stats = result.fetchone()
        if not provider_stats:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Quick red flags
        red_flags = []
        
        if provider_stats.claim_count > 1000:
            red_flags.append("High claim volume")
        
        if provider_stats.total_amount > 1000000:
            red_flags.append("High total billing amount")
        
        if provider_stats.avg_amount > 500:
            red_flags.append("High average claim amount")
        
        # Quick damage estimate
        estimated_exposure = float(provider_stats.total_amount) * 3 + (provider_stats.claim_count * 11665)
        
        return {
            "provider": {
                "name": provider_stats.name,
                "npi": provider_stats.npi,
                "location": f"{provider_stats.city}, {provider_stats.state}"
            },
            "case_metrics": {
                "total_claims": provider_stats.claim_count,
                "total_amount": float(provider_stats.total_amount),
                "average_claim": float(provider_stats.avg_amount),
                "unique_beneficiaries": provider_stats.unique_beneficiaries
            },
            "assessment": {
                "red_flags": red_flags,
                "case_strength": "STRONG" if len(red_flags) >= 2 else "MODERATE" if len(red_flags) == 1 else "WEAK",
                "estimated_exposure": estimated_exposure,
                "potential_attorney_fees": estimated_exposure * 0.30,
                "recommended_action": "PROCEED WITH FULL INVESTIGATION" if len(red_flags) >= 2 else "GATHER ADDITIONAL EVIDENCE"
            },
            "next_steps": [
                "Generate full evidence package",
                "Review fraud patterns",
                "Calculate precise damages",
                "Prepare expert testimony foundation"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in case assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fraud-patterns/{provider_id}")
async def analyze_fraud_patterns(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Detailed fraud pattern analysis"""
    
    try:
        builder = EvidencePackageBuilder(db)
        patterns = await builder._analyze_fraud_patterns(provider_id)
        
        return {
            "provider_id": provider_id,
            "analysis_date": datetime.now().isoformat(),
            "fraud_patterns": patterns,
            "pattern_count": len(patterns),
            "high_risk_patterns": [p for p in patterns if p["severity"] == "high"],
            "legal_theories": list(set(p["legal_theory"] for p in patterns))
        }
        
    except Exception as e:
        logger.error(f"Error analyzing fraud patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/damage-calculator/{provider_id}")
async def calculate_damages(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Detailed damage calculations for FCA case"""
    
    try:
        builder = EvidencePackageBuilder(db)
        damages = await builder._calculate_damages(provider_id)
        
        return {
            "provider_id": provider_id,
            "calculation_date": datetime.now().isoformat(),
            "damages": damages,
            "summary": {
                "total_fraud": f"${damages['total_fraudulent_amount']:,.2f}",
                "treble_damages": f"${damages['treble_damages']:,.2f}",
                "civil_penalties": f"${damages['civil_penalties']:,.2f}",
                "total_exposure": f"${damages['total_exposure']:,.2f}",
                "attorney_fees": f"${damages['estimated_attorney_fees']:,.2f}",
                "net_recovery": f"${damages['potential_recovery']:,.2f}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating damages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/similar-cases")
async def get_similar_cases(
    pattern_type: Optional[str] = Query(None),
    settlement_range: Optional[str] = Query(None)
):
    """Get similar successful FCA cases for precedent"""
    
    # This would integrate with legal database
    # For now, return mock data
    
    cases = [
        {
            "name": "United States v. ABC Home Care Agency",
            "court": "E.D.N.Y.",
            "year": 2023,
            "settlement": "$2.1M",
            "pattern": "excessive_billing_frequency",
            "citation": "No. 22-CV-1234",
            "summary": "Home care agency billed for services not rendered"
        },
        {
            "name": "United States v. XYZ Medical Services", 
            "court": "S.D.N.Y.",
            "year": 2022,
            "settlement": "$5.8M",
            "pattern": "temporal_spike",
            "citation": "No. 21-CV-5678",
            "summary": "Medical provider showed suspicious billing spikes"
        },
        {
            "name": "United States v. DEF Pharmacy",
            "court": "E.D.N.Y.",
            "year": 2021,
            "settlement": "$3.4M",
            "pattern": "beneficiary_concentration",
            "citation": "No. 20-CV-9012",
            "summary": "Pharmacy concentrated billing on few beneficiaries"
        }
    ]
    
    if pattern_type:
        cases = [c for c in cases if c["pattern"] == pattern_type]
    
    return {
        "cases": cases,
        "total_cases": len(cases),
        "total_settlements": "$11.3M",
        "average_settlement": "$3.8M"
    }

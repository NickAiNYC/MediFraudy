"""
ClaimSwarm API Routes
Autonomous claims processing and fraud detection
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel, Field

from database_v2 import get_async_db
from services.claimswarm_engine import claimswarm_engine, ClaimData, ClaimComplexity, ClaimStatus
from background_jobs import job_manager, schedule_claim_processing
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/claimswarm", tags=["ClaimSwarm"])

# Pydantic models for API
class ClaimSubmission(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier")
    policy_number: str = Field(..., description="Insurance policy number")
    claimant_name: str = Field(..., description="Name of the claimant")
    claim_type: str = Field(..., description="Type of claim (auto, property, liability)")
    incident_date: str = Field(..., description="Date of incident (ISO format)")
    incident_location: str = Field(..., description="Location of incident")
    description: str = Field(..., description="Description of the incident")
    photos: List[str] = Field(default=[], description="List of photo URLs")
    documents: List[str] = Field(default=[], description="List of document URLs")
    estimated_amount: float = Field(default=0.0, description="Estimated claim amount")
    police_report: Optional[str] = Field(None, description="Police report number or URL")
    witnesses: List[str] = Field(default=[], description="List of witness names")
    repair_shops: List[str] = Field(default=[], description="List of repair shop names")
    medical_providers: List[str] = Field(default=[], description="List of medical provider names")

class ClaimProcessingRequest(BaseModel):
    claim: ClaimSubmission
    priority: str = Field(default="normal", description="Processing priority (low, normal, high, urgent)")
    auto_approve_threshold: float = Field(default=0.3, description="Auto-approval threshold")

class BatchClaimRequest(BaseModel):
    claims: List[ClaimSubmission]
    priority: str = Field(default="normal", description="Processing priority for batch")

# Claim processing endpoints
@router.post("/process-claim")
async def process_claim(
    request: ClaimProcessingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Process a single claim through the ClaimSwarm"""
    
    try:
        # Schedule claim processing as background job
        job_id = await schedule_claim_processing(request.dict())
        
        return {
            "status": "claim_processing_scheduled",
            "job_id": job_id,
            "claim_id": request.claim.claim_id,
            "priority": request.priority,
            "estimated_processing_time": "2-5 minutes",
            "processing_features": [
                "AI-powered triage",
                "Multi-agent investigation",
                "Computer vision estimation",
                "Intelligent settlement",
                "Blockchain evidence"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error scheduling claim processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-process")
async def batch_process_claims(
    request: BatchClaimRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Process multiple claims in batch"""
    
    try:
        # Schedule batch processing
        job_ids = []
        for claim in request.claims:
            batch_request = ClaimProcessingRequest(
                claim=claim,
                priority=request.priority
            )
            job_id = await schedule_claim_processing(batch_request.dict())
            job_ids.append(job_id)
        
        return {
            "status": "batch_processing_scheduled",
            "total_claims": len(request.claims),
            "job_ids": job_ids,
            "priority": request.priority,
            "estimated_processing_time": f"{len(request.claims) * 2-5} minutes",
            "processing_features": [
                "Parallel processing",
                "Fraud graph analysis",
                "Batch optimization",
                "Comprehensive reporting"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error scheduling batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/claim/{claim_id}/status")
async def get_claim_status(
    claim_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get the status of a processed claim"""
    
    try:
        # Check if claim exists in database
        result = await db.execute(text("""
            SELECT * FROM claim_results WHERE claim_id = :claim_id
        """), {"claim_id": claim_id})
        
        claim_result = result.fetchone()
        
        if not claim_result:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        return {
            "status": "success",
            "claim": {
                "claim_id": claim_result.claim_id,
                "complexity": claim_result.complexity,
                "status": claim_result.status,
                "fraud_score": float(claim_result.fraud_score),
                "estimated_cost": float(claim_result.estimated_cost),
                "confidence": float(claim_result.confidence),
                "recommendation": claim_result.recommendation,
                "processing_time": float(claim_result.processing_time),
                "blockchain_hash": claim_result.blockchain_hash,
                "created_at": claim_result.created_at.isoformat(),
                "updated_at": claim_result.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting claim status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/claim/{claim_id}/details")
async def get_claim_details(
    claim_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed claim processing results"""
    
    try:
        # Get claim result
        result = await db.execute(text("""
            SELECT * FROM claim_results WHERE claim_id = :claim_id
        """), {"claim_id": claim_id})
        
        claim_result = result.fetchone()
        
        if not claim_result:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Get investigation details
        investigation_result = await db.execute(text("""
            SELECT * FROM claim_investigations WHERE claim_id = :claim_id
        """), {"claim_id": claim_id})
        
        investigation = investigation_result.fetchone()
        
        # Get estimation details
        estimation_result = await db.execute(text("""
            SELECT * FROM claim_estimations WHERE claim_id = :claim_id
        """), {"claim_id": claim_id})
        
        estimation = estimation_result.fetchone()
        
        return {
            "status": "success",
            "claim_result": {
                "claim_id": claim_result.claim_id,
                "complexity": claim_result.complexity,
                "status": claim_result.status,
                "fraud_score": float(claim_result.fraud_score),
                "estimated_cost": float(claim_result.estimated_cost),
                "confidence": float(claim_result.confidence),
                "suspicious_patterns": claim_result.suspicious_patterns or [],
                "evidence_links": claim_result.evidence_links or [],
                "recommendation": claim_result.recommendation,
                "processing_time": float(claim_result.processing_time),
                "blockchain_hash": claim_result.blockchain_hash
            },
            "investigation": {
                "fraud_indicators": investigation.fraud_indicators or [] if investigation else [],
                "suspicious_patterns": investigation.suspicious_patterns or [] if investigation else [],
                "entity_connections": investigation.entity_connections or [] if investigation else [],
                "risk_score": float(investigation.risk_score) if investigation else 0.0
            },
            "estimation": {
                "damage_assessment": estimation.damage_assessment or {} if estimation else {},
                "cost_breakdown": estimation.cost_breakdown or {} if estimation else {},
                "confidence_score": float(estimation.confidence_score) if estimation else 0.0,
                "estimated_total": float(estimation.estimated_total) if estimation else 0.0,
                "recommended_settlement": float(estimation.recommended_settlement) if estimation else 0.0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting claim details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Fraud graph endpoints
@router.get("/fraud-graph/metrics")
async def get_fraud_graph_metrics(db: AsyncSession = Depends(get_async_db)):
    """Get fraud graph analytics and metrics"""
    
    try:
        metrics = await claimswarm_engine.get_fraud_graph_metrics()
        
        return {
            "status": "success",
            "fraud_graph_metrics": metrics,
            "analysis_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting fraud graph metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fraud-graph/rings")
async def find_fraud_rings(
    min_size: int = Query(3, description="Minimum size of fraud ring to detect"),
    db: AsyncSession = Depends(get_async_db)
):
    """Find potential fraud rings in the fraud graph"""
    
    try:
        fraud_rings = await claimswarm_engine.find_fraud_rings(min_size)
        
        return {
            "status": "success",
            "fraud_rings": fraud_rings,
            "total_rings": len(fraud_rings),
            "min_size_filter": min_size,
            "analysis_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error finding fraud rings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoints
@router.get("/analytics/dashboard")
async def get_claimswarm_analytics(db: AsyncSession = Depends(get_async_db)):
    """Get ClaimSwarm analytics dashboard data"""
    
    try:
        # Get claim processing statistics
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total_claims,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_claims,
                COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated_claims,
                COUNT(CASE WHEN complexity = 'simple' THEN 1 END) as simple_claims,
                COUNT(CASE WHEN complexity = 'moderate' THEN 1 END) as moderate_claims,
                COUNT(CASE WHEN complexity = 'complex' THEN 1 END) as complex_claims,
                COUNT(CASE WHEN complexity = 'critical' THEN 1 END) as critical_claims,
                AVG(fraud_score) as avg_fraud_score,
                AVG(processing_time) as avg_processing_time,
                SUM(estimated_cost) as total_estimated_cost
            FROM claim_results
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """))
        
        daily_stats = result.fetchone()
        
        # Get fraud graph metrics
        fraud_metrics = await claimswarm_engine.get_fraud_graph_metrics()
        
        return {
            "status": "success",
            "daily_statistics": {
                "total_claims": daily_stats.total_claims,
                "approved_claims": daily_stats.approved_claims,
                "escalated_claims": daily_stats.escalated_claims,
                "approval_rate": (daily_stats.approved_claims / max(daily_stats.total_claims, 1)) * 100,
                "complexity_breakdown": {
                    "simple": daily_stats.simple_claims,
                    "moderate": daily_stats.moderate_claims,
                    "complex": daily_stats.complex_claims,
                    "critical": daily_stats.critical_claims
                },
                "avg_fraud_score": float(daily_stats.avg_fraud_score) if daily_stats.avg_fraud_score else 0.0,
                "avg_processing_time": float(daily_stats.avg_processing_time) if daily_stats.avg_processing_time else 0.0,
                "total_estimated_cost": float(daily_stats.total_estimated_cost) if daily_stats.total_estimated_cost else 0.0
            },
            "fraud_graph_metrics": fraud_metrics,
            "dashboard_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/fraud-trends")
async def get_fraud_trends(
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get fraud detection trends over time"""
    
    try:
        # Get daily fraud scores
        result = await db.execute(text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as claim_count,
                AVG(fraud_score) as avg_fraud_score,
                COUNT(CASE WHEN fraud_score > 0.7 THEN 1 END) as high_risk_claims,
                COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated_claims
            FROM claim_results
            WHERE created_at >= NOW() - INTERVAL :days days
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """), {"days": days})
        
        trends = result.fetchall()
        
        return {
            "status": "success",
            "fraud_trends": [
                {
                    "date": trend.date.isoformat(),
                    "claim_count": trend.claim_count,
                    "avg_fraud_score": float(trend.avg_fraud_score) if trend.avg_fraud_score else 0.0,
                    "high_risk_claims": trend.high_risk_claims,
                    "escalated_claims": trend.escalated_claims,
                    "escalation_rate": (trend.escalated_claims / max(trend.claim_count, 1)) * 100
                }
                for trend in trends
            ],
            "analysis_period": f"{days} days",
            "trend_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting fraud trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoints
@router.get("/config/agents")
async def get_agent_configuration():
    """Get ClaimSwarm agent configuration"""
    
    return {
        "status": "success",
        "agent_configuration": {
            "triage_agent": {
                "complexity_thresholds": {
                    "amount": 10000,
                    "injuries": 3,
                    "vehicles": 2,
                    "locations": 1
                }
            },
            "investigator_swarm": {
                "agents": [
                    "PoliceReportAgent",
                    "SocialMediaAgent", 
                    "WeatherAgent",
                    "RepairShopAgent",
                    "MedicalProviderAgent",
                    "LocationAgent"
                ]
            },
            "estimator_agent": {
                "damage_models": [
                    "auto_damage_v2.pt",
                    "property_damage_v1.pt", 
                    "injury_detection_v1.pt"
                ]
            },
            "settler_agent": {
                "approval_thresholds": {
                    "simple": 0.3,
                    "moderate": 0.2,
                    "complex": 0.1,
                    "critical": 0.05
                }
            }
        }
    }

@router.post("/config/thresholds")
async def update_processing_thresholds(
    thresholds: Dict[str, float],
    db: AsyncSession = Depends(get_async_db)
):
    """Update ClaimSwarm processing thresholds"""
    
    try:
        # Validate thresholds
        valid_thresholds = ["simple", "moderate", "complex", "critical"]
        for threshold_name, value in thresholds.items():
            if threshold_name not in valid_thresholds:
                raise HTTPException(status_code=400, detail=f"Invalid threshold: {threshold_name}")
            if not 0 <= value <= 1:
                raise HTTPException(status_code=400, detail=f"Threshold must be between 0 and 1: {threshold_name}")
        
        # Update thresholds in database
        for threshold_name, value in thresholds.items():
            await db.execute(text("""
                INSERT INTO claimswarm_config (config_key, config_value, updated_at)
                VALUES (:key, :value, NOW())
                ON CONFLICT (config_key) DO UPDATE SET
                config_value = :value, updated_at = NOW()
            """), {"key": f"approval_threshold_{threshold_name}", "value": str(value)})
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "Processing thresholds updated successfully",
            "updated_thresholds": thresholds,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@router.get("/health")
async def claimswarm_health_check():
    """ClaimSwarm health check"""
    
    try:
        # Check if ClaimSwarm engine is initialized
        if not claimswarm_engine:
            raise HTTPException(status_code=503, detail="ClaimSwarm engine not initialized")
        
        return {
            "status": "healthy",
            "service": "ClaimSwarm",
            "version": "1.0.2026",
            "components": {
                "triage_agent": "operational",
                "investigator_swarm": "operational",
                "estimator_agent": "operational",
                "settler_agent": "operational",
                "fraud_graph": "operational"
            },
            "health_check_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ClaimSwarm health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

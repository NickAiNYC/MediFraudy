"""
Elite Political Intelligence API Routes
Connects Medicaid fraud to political corruption across party lines
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database_v2 import get_async_db
from services.political_intelligence import political_intelligence
from background_jobs import job_manager, schedule_political_analysis
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/political", tags=["Political Intelligence"])

@router.get("/analysis/{provider_id}")
async def get_political_analysis(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get complete political intelligence analysis"""
    
    try:
        analysis = await political_intelligence.analyze_political_connections(provider_id)
        
        return {
            "status": "completed",
            "analysis": analysis,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in political analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/{provider_id}")
async def start_political_analysis(
    provider_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Start comprehensive political intelligence analysis"""
    
    try:
        # Validate provider exists
        result = await db.execute(text("SELECT COUNT(*) FROM providers WHERE id = :provider_id"), {"provider_id": provider_id})
        if result.scalar() == 0:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Schedule background analysis
        job_id = await schedule_political_analysis(provider_id)
        
        return {
            "status": "analysis_started",
            "job_id": job_id,
            "provider_id": provider_id,
            "estimated_completion": "10-15 minutes",
            "analysis_components": [
                "Campaign Contribution Analysis",
                "Lobbying Connection Investigation", 
                "Political Appointment Review",
                "Legislation Cross-Reference",
                "Corruption Risk Scoring",
                "Bipartisan Pattern Detection"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error starting political analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/corruption-score/{provider_id}")
async def get_corruption_score(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get corruption risk score for provider"""
    
    try:
        analysis = await political_intelligence.analyze_political_connections(provider_id)
        corruption_score = analysis["corruption_risk_score"]
        
        return {
            "provider_id": provider_id,
            "corruption_score": corruption_score,
            "investigation_priority": analysis["investigation_priority"],
            "analysis_date": analysis["analysis_date"],
            "risk_factors": corruption_score["contributing_factors"],
            "component_breakdown": corruption_score["component_scores"]
        }
        
    except Exception as e:
        logger.error(f"Error calculating corruption score: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaign-contributions/{provider_id}")
async def get_campaign_contributions(
    provider_id: int,
    party: Optional[str] = Query(None),
    min_amount: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed campaign contribution analysis"""
    
    try:
        analysis = await political_intelligence.analyze_political_connections(provider_id)
        contributions = analysis["campaign_contributions"]
        
        # Filter results
        filtered_contributions = contributions["contributions"]
        
        if party:
            filtered_contributions = [c for c in filtered_contributions if c.get("party") == party]
        
        if min_amount:
            filtered_contributions = [c for c in filtered_contributions if c.get("amount", 0) >= min_amount]
        
        return {
            "provider_id": provider_id,
            "total_contributions": contributions["total_contributions"],
            "contribution_count": len(filtered_contributions),
            "party_breakdown": contributions["party_breakdown"],
            "suspicious_patterns": contributions["suspicious_patterns"],
            "contributions": filtered_contributions
        }
        
    except Exception as e:
        logger.error(f"Error analyzing campaign contributions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lobbying-connections/{provider_id}")
async def get_lobbying_connections(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get lobbying connection analysis"""
    
    try:
        analysis = await political_intelligence.analyze_political_connections(provider_id)
        lobbying = analysis["lobbying_connections"]
        
        return {
            "provider_id": provider_id,
            "lobbying_firms": lobbying["lobbying_firms"],
            "total_lobbying_spend": lobbying["total_lobbying_spend"],
            "issues_lobbied": lobbying["issues_lobbied"],
            "suspicious_patterns": lobbying["suspicious_patterns"],
            "connections": lobbying["connections"]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing lobbying connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bipartisan-analysis")
async def get_bipartisan_analysis(
    min_corruption_score: int = Query(60),
    party_focus: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    """Get bipartisan corruption analysis across all providers"""
    
    try:
        # Get all providers with high corruption scores
        result = await db.execute(text("""
            SELECT id, name, city, state FROM providers 
            WHERE id IN (
                SELECT DISTINCT provider_id FROM claims 
                WHERE amount > 1000
            )
            LIMIT 50
        """))
        
        providers = result.fetchall()
        
        bipartisan_analysis = []
        
        for provider in providers:
            try:
                analysis = await political_intelligence.analyze_political_connections(provider.id)
                corruption_score = analysis["corruption_risk_score"]["overall_score"]
                
                if corruption_score >= min_corruption_score:
                    contributions = analysis["campaign_contributions"]
                    
                    # Check for bipartisan contributions
                    has_bipartisan = len(contributions["party_breakdown"]) > 1
                    
                    if party_focus:
                        has_party_focus = party_focus in contributions["party_breakdown"]
                    else:
                        has_party_focus = True
                    
                    if has_bipartisan or has_party_focus:
                        bipartisan_analysis.append({
                            "provider_id": provider.id,
                            "provider_name": provider.name,
                            "location": f"{provider.city}, {provider.state}",
                            "corruption_score": corruption_score,
                            "risk_level": analysis["corruption_risk_score"]["risk_level"],
                            "party_breakdown": contributions["party_breakdown"],
                            "total_contributions": contributions["total_contributions"],
                            "bipartisan": has_bipartisan,
                            "investigation_priority": analysis["investigation_priority"]
                        })
            except Exception as e:
                logger.warning(f"Error analyzing provider {provider.id}: {e}")
                continue
        
        # Sort by corruption score
        bipartisan_analysis.sort(key=lambda x: x["corruption_score"], reverse=True)
        
        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "min_corruption_score": min_corruption_score,
            "party_focus": party_focus,
            "total_providers": len(bipartisan_analysis),
            "bipartisan_count": sum(1 for p in bipartisan_analysis if p["bipartisan"]),
            "average_corruption_score": sum(p["corruption_score"] for p in bipartisan_analysis) / len(bipartisan_analysis) if bipartisan_analysis else 0,
            "providers": bipartisan_analysis[:20]  # Top 20
        }
        
    except Exception as e:
        logger.error(f"Error in bipartisan analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/kickback-networks")
async def get_kickback_networks(
    min_network_size: int = Query(3),
    db: AsyncSession = Depends(get_async_db)
):
    """Identify political kickback networks"""
    
    try:
        # Get high-risk providers
        result = await db.execute(text("""
            SELECT id, name, city, state FROM providers 
            WHERE total_amount > 1000000
            LIMIT 100
        """))
        
        providers = result.fetchall()
        
        networks = []
        
        for provider in providers:
            try:
                analysis = await political_intelligence.analyze_political_connections(provider.id)
                corruption_score = analysis["corruption_risk_score"]["overall_score"]
                
                if corruption_score >= 70:  # High corruption risk
                    # Check for network connections
                    network_connections = []
                    
                    # Political connections
                    contributions = analysis["campaign_contributions"]
                    for recipient in contributions["recipients"]:
                        network_connections.append({
                            "type": "political_contribution",
                            "target": recipient,
                            "amount": next(c["amount"] for c in contributions["contributions"] if c["recipient"] == recipient)
                        })
                    
                    # Lobbying connections
                    lobbying = analysis["lobbying_connections"]
                    for firm in lobbying["lobbying_firms"]:
                        network_connections.append({
                            "type": "lobbying_firm",
                            "target": firm,
                            "amount": lobbying["total_lobbying_spend"]
                        })
                    
                    if len(network_connections) >= min_network_size:
                        networks.append({
                            "provider_id": provider.id,
                            "provider_name": provider.name,
                            "location": f"{provider.city}, {provider.state}",
                            "corruption_score": corruption_score,
                            "network_size": len(network_connections),
                            "connections": network_connections,
                            "investigation_priority": analysis["investigation_priority"]
                        })
            except Exception as e:
                logger.warning(f"Error analyzing provider {provider.id}: {e}")
                continue
        
        # Sort by network size
        networks.sort(key=lambda x: x["network_size"], reverse=True)
        
        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "min_network_size": min_network_size,
            "total_networks": len(networks),
            "average_network_size": sum(n["network_size"] for n in networks) / len(networks) if networks else 0,
            "networks": networks[:10]  # Top 10 networks
        }
        
    except Exception as e:
        logger.error(f"Error analyzing kickback networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/party-comparison")
async def get_party_comparison(
    db: AsyncSession = Depends(get_async_db)
):
    """Compare corruption patterns across Democratic and Republican connections"""
    
    try:
        # Get sample providers
        result = await db.execute(text("""
            SELECT id, name, city, state FROM providers 
            WHERE total_amount > 500000
            LIMIT 50
        """))
        
        providers = result.fetchall()
        
        party_analysis = {
            "Democratic": {"providers": [], "total_contributions": 0, "avg_corruption_score": 0},
            "Republican": {"providers": [], "total_contributions": 0, "avg_corruption_score": 0},
            "Bipartisan": {"providers": [], "total_contributions": 0, "avg_corruption_score": 0}
        }
        
        for provider in providers:
            try:
                analysis = await political_intelligence.analyze_political_connections(provider.id)
                contributions = analysis["campaign_contributions"]
                corruption_score = analysis["corruption_risk_score"]["overall_score"]
                
                party_breakdown = contributions["party_breakdown"]
                
                if len(party_breakdown) > 1:
                    category = "Bipartisan"
                elif "Democratic" in party_breakdown:
                    category = "Democratic"
                elif "Republican" in party_breakdown:
                    category = "Republican"
                else:
                    continue
                
                party_analysis[category]["providers"].append({
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "corruption_score": corruption_score,
                    "contributions": contributions["total_contributions"]
                })
                
                party_analysis[category]["total_contributions"] += contributions["total_contributions"]
                
            except Exception as e:
                logger.warning(f"Error analyzing provider {provider.id}: {e}")
                continue
        
        # Calculate averages
        for party in party_analysis:
            providers = party_analysis[party]["providers"]
            if providers:
                party_analysis[party]["avg_corruption_score"] = sum(p["corruption_score"] for p in providers) / len(providers)
                party_analysis[party]["provider_count"] = len(providers)
            else:
                party_analysis[party]["provider_count"] = 0
        
        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "party_comparison": party_analysis,
            "total_providers_analyzed": len(providers),
            "highest_corruption": max(party_analysis[party]["avg_corruption_score"] for party in party_analysis),
            "most_active_party": max(party_analysis, key=lambda x: x["total_contributions"])
        }
        
    except Exception as e:
        logger.error(f"Error in party comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/investigation-priority")
async def get_investigation_priority_list(
    min_score: int = Query(70),
    limit: int = Query(20),
    db: AsyncSession = Depends(get_async_db)
):
    """Get prioritized list for investigation"""
    
    try:
        # Get high-value providers
        result = await db.execute(text("""
            SELECT id, name, city, state, total_amount FROM providers 
            WHERE total_amount > 100000
            ORDER BY total_amount DESC
            LIMIT 100
        """))
        
        providers = result.fetchall()
        
        priority_list = []
        
        for provider in providers:
            try:
                analysis = await political_intelligence.analyze_political_connections(provider.id)
                corruption_score = analysis["corruption_risk_score"]["overall_score"]
                
                if corruption_score >= min_score:
                    priority_list.append({
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "location": f"{provider.city}, {provider.state}",
                        "total_medicaid_amount": float(provider.total_amount),
                        "corruption_score": corruption_score,
                        "risk_level": analysis["corruption_risk_score"]["risk_level"],
                        "investigation_priority": analysis["investigation_priority"],
                        "political_connections": len(analysis["campaign_contributions"]["recipients"]) + len(analysis["lobbying_connections"]["lobbying_firms"]),
                        "suspicious_patterns": len(analysis["campaign_contributions"]["suspicious_patterns"]) + len(analysis["lobbying_connections"]["suspicious_patterns"])
                    })
            except Exception as e:
                logger.warning(f"Error analyzing provider {provider.id}: {e}")
                continue
        
        # Sort by corruption score and total amount
        priority_list.sort(key=lambda x: (x["corruption_score"], x["total_medicaid_amount"]), reverse=True)
        
        return {
            "analysis_date": datetime.utcnow().isoformat(),
            "min_corruption_score": min_score,
            "total_prioritized": len(priority_list),
            "priority_list": priority_list[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error generating investigation priority list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

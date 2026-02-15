"""
FastAPI routes for fraud ring detection and graph analytics.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional, List
from pydantic import BaseModel, Field
import logging

from sqlalchemy.orm import Session
from database import get_db
from analytics.graph_analyzer import FraudRingDetector

router = APIRouter(prefix="/api/graph", tags=["graph"])
logger = logging.getLogger(__name__)


# Response models
class NodeResponse(BaseModel):
    id: int
    name: str
    type: str
    risk_score: float
    capacity: Optional[int] = None
    npi: Optional[str] = None

class EdgeResponse(BaseModel):
    source: int
    target: int
    weight: float
    claims: Optional[int] = None

class NetworkResponse(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    center_node: Optional[int] = None
    depth: Optional[int] = None
    total_nodes: int
    total_edges: int


@router.get("/network/{provider_id}", response_model=NetworkResponse)
async def get_provider_network(
    provider_id: int,
    depth: int = Query(2, ge=1, le=4, description="Depth of ego network"),
    db: Session = Depends(get_db)
):
    """
    Get ego network for a specific provider.
    
    Returns all providers within `depth` connections of the specified provider.
    """
    try:
        logger.info(f"Fetching network for provider {provider_id} with depth {depth}")
        
        detector = FraudRingDetector(db)
        detector.build_provider_network()
        
        result = detector.get_ego_network(provider_id, depth)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
    
    except Exception as e:
        logger.error(f"Error fetching provider network: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch network: {str(e)}")


@router.get("/fraud-rings")
async def get_fraud_rings(
    min_score: int = Query(70, ge=0, le=100, description="Minimum fraud score threshold"),
    min_size: int = Query(3, ge=2, le=20, description="Minimum ring size"),
    db: Session = Depends(get_db)
):
    """
    Get all detected fraud rings above threshold.
    
    Returns communities of providers with suspicious patterns:
    - High density networks
    - Shared beneficiaries
    - High risk scores
    - Triangular relationships
    """
    try:
        logger.info(f"Detecting fraud rings with min_score={min_score}, min_size={min_size}")
        
        detector = FraudRingDetector(db)
        detector.build_provider_network()
        
        rings = detector.detect_fraud_rings(min_size=min_size)
        filtered_rings = [r for r in rings if r['fraud_score'] >= min_score]
        
        logger.info(f"Found {len(filtered_rings)} fraud rings above threshold")
        return filtered_rings
    
    except Exception as e:
        logger.error(f"Error detecting fraud rings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to detect fraud rings: {str(e)}")


@router.get("/network-stats")
async def get_network_stats(db: Session = Depends(get_db)):
    """
    Get overall network statistics and comprehensive analysis.
    
    Returns:
    - Network topology metrics
    - Detected fraud rings
    - Kickback cycles
    - Beneficiary concentration patterns
    - Most central providers
    """
    try:
        logger.info("Generating network statistics")
        
        detector = FraudRingDetector(db)
        insights = detector.generate_network_insights()
        
        logger.info("Network statistics generated successfully")
        return insights
    
    except Exception as e:
        logger.error(f"Error generating network stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate stats: {str(e)}")


@router.get("/kickback-cycles")
async def get_kickback_cycles(
    min_volume: int = Query(10, ge=1, description="Minimum referral volume"),
    db: Session = Depends(get_db)
):
    """
    Detect potential kickback cycles.
    
    Identifies circular referral patterns (A→B→C→A) which are indicative
    of kickback schemes like the Brooklyn $68M case.
    """
    try:
        logger.info(f"Detecting kickback cycles with min_volume={min_volume}")
        
        detector = FraudRingDetector(db)
        detector.build_referral_network()
        
        cycles = detector.detect_kickback_cycles(min_volume=min_volume)
        
        logger.info(f"Detected {len(cycles)} kickback cycles")
        return cycles
    
    except Exception as e:
        logger.error(f"Error detecting kickback cycles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to detect cycles: {str(e)}")


@router.get("/beneficiary-concentration")
async def get_beneficiary_concentration(
    min_overlap: int = Query(5, ge=1, description="Minimum overlapping beneficiaries"),
    overlap_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum overlap ratio"),
    db: Session = Depends(get_db)
):
    """
    Find beneficiary concentration patterns.
    
    Detects provider pairs sharing an unusually high proportion of beneficiaries,
    indicating potential patient brokering or coordinated fraud.
    """
    try:
        logger.info(f"Finding beneficiary concentration with min_overlap={min_overlap}, threshold={overlap_threshold}")
        
        detector = FraudRingDetector(db)
        detector.build_provider_network()
        
        patterns = detector.find_beneficiary_concentration_rings(
            min_overlap=min_overlap,
            overlap_threshold=overlap_threshold
        )
        
        logger.info(f"Found {len(patterns)} beneficiary concentration patterns")
        return patterns
    
    except Exception as e:
        logger.error(f"Error finding beneficiary concentration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to find patterns: {str(e)}")


@router.get("/export/{format}")
async def export_network_data(
    format: str = Path(..., pattern="^(json|graphml|csv)$"),
    db: Session = Depends(get_db)
):
    """
    Export network data in various formats.
    
    Formats:
    - json: Full network data with metadata
    - graphml: Graph structure for Gephi/Cytoscape
    - csv: Edge list for spreadsheet analysis
    """
    try:
        logger.info(f"Exporting network data in {format} format")
        
        detector = FraudRingDetector(db)
        detector.build_provider_network()
        
        if format == "json":
            # Full network export
            import networkx as nx
            data = nx.node_link_data(detector.graph)
            return data
        
        elif format == "graphml":
            # GraphML for visualization tools
            import networkx as nx
            import io
            
            output = io.StringIO()
            nx.write_graphml(detector.graph, output)
            return {"graphml": output.getvalue()}
        
        elif format == "csv":
            # Edge list CSV
            edges = []
            for u, v, data in detector.graph.edges(data=True):
                edges.append({
                    'source': u,
                    'target': v,
                    'weight': data.get('weight', 1),
                    'claims': data.get('claims', 0)
                })
            return {"edges": edges}
    
    except Exception as e:
        logger.error(f"Error exporting network data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")


@router.post("/refresh")
async def refresh_network(
    lookback_days: int = Query(730, ge=30, le=1825, description="Days of data to analyze"),
    db: Session = Depends(get_db)
):
    """
    Rebuild network analysis with updated parameters.
    
    Forces a fresh computation of the provider network and fraud detection.
    """
    try:
        logger.info(f"Refreshing network with {lookback_days} day lookback")
        
        detector = FraudRingDetector(db)
        detector.build_provider_network(lookback_days=lookback_days)
        detector.build_referral_network(lookback_days=lookback_days)
        
        insights = detector.generate_network_insights()
        
        return {
            "status": "success",
            "message": f"Network refreshed with {lookback_days} days of data",
            "summary": {
                "total_providers": insights['total_providers'],
                "total_connections": insights['total_connections'],
                "fraud_rings_detected": len(insights['fraud_rings']),
                "kickback_cycles_detected": len(insights['kickback_cycles'])
            }
        }
    
    except Exception as e:
        logger.error(f"Error refreshing network: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh: {str(e)}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if graph analytics service is operational."""
    try:
        import networkx as nx
        return {
            "status": "healthy",
            "networkx_version": nx.__version__,
            "features": [
                "fraud_ring_detection",
                "kickback_cycle_detection",
                "beneficiary_concentration",
                "ego_network_extraction"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

"""Network analysis service for provider relationship mapping.

Wraps the existing graph_analyzer module to provide service-layer
network intelligence with fraud ring detection, betweenness centrality,
shared address clusters, and cross-borough cluster mapping.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

import networkx as nx
from analytics.graph_analyzer import FraudRingDetector

logger = logging.getLogger(__name__)


def analyze_provider_network(
    db: Session,
    provider_id: int,
    depth: int = 2,
) -> Dict[str, Any]:
    """Analyze the network surrounding a specific provider.

    Args:
        db: Database session.
        provider_id: Center node provider.
        depth: How many hops to traverse from center.

    Returns:
        Ego network data with nodes, edges, and risk metadata.
    """
    detector = FraudRingDetector(db)
    detector.build_provider_network()
    ego = detector.get_ego_network(provider_id, depth=depth)
    ego["analyzed_at"] = datetime.utcnow().isoformat()
    return ego


def detect_fraud_rings(
    db: Session,
    min_size: int = 3,
    min_shared_patients: int = 5,
) -> Dict[str, Any]:
    """Run full fraud ring detection across the provider network.

    Args:
        db: Database session.
        min_size: Minimum community size to report.
        min_shared_patients: Minimum shared beneficiaries for an edge.

    Returns:
        Dictionary with detected fraud rings and network statistics.
    """
    detector = FraudRingDetector(db)
    detector.build_provider_network(min_shared_patients=min_shared_patients)
    rings = detector.detect_fraud_rings(min_size=min_size)
    insights = detector.generate_network_insights()

    return {
        "fraud_rings": rings,
        "network_stats": {
            "total_providers": insights.get("total_providers", 0),
            "total_connections": insights.get("total_connections", 0),
            "density": insights.get("network_density", 0),
            "communities": insights.get("num_communities", 0),
        },
        "most_central_providers": insights.get("most_central_providers", []),
        "top_betweenness_brokers": insights.get("top_betweenness_brokers", []),
        "shared_address_clusters": insights.get("shared_address_clusters", []),
        "cross_borough_clusters": insights.get("cross_borough_clusters", []),
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def get_network_summary(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """Get a summary of a provider's network connections for evidence packages.

    Args:
        db: Database session.
        provider_id: Target provider.

    Returns:
        Summary suitable for inclusion in litigation evidence.
    """
    detector = FraudRingDetector(db)
    detector.build_provider_network()

    if provider_id not in detector.graph:
        return {
            "provider_id": provider_id,
            "connected_entities": 0,
            "connections": [],
            "in_fraud_ring": False,
        }

    neighbors = list(detector.graph.neighbors(provider_id))

    # Calculate betweenness centrality for this provider
    betweenness = 0.0
    try:
        bc = nx.betweenness_centrality(detector.graph)
        betweenness = bc.get(provider_id, 0.0)
    except Exception:
        pass

    connections = []
    for n in neighbors:
        edge_data = detector.graph.edges[provider_id, n]
        node_data = detector.graph.nodes[n]
        connections.append({
            "provider_id": n,
            "name": node_data.get("name", f"Provider {n}"),
            "type": node_data.get("type", "Unknown"),
            "shared_patients": edge_data.get("weight", 0),
            "risk_score": node_data.get("risk_score", 0),
        })

    # Check if this provider is in any detected fraud ring
    rings = detector.detect_fraud_rings(min_size=3)
    in_ring = False
    ring_info = None
    for ring in rings:
        ring_ids = [p["id"] for p in ring.get("providers", [])]
        if provider_id in ring_ids:
            in_ring = True
            ring_info = {
                "ring_size": ring["size"],
                "fraud_score": ring["fraud_score"],
                "suspicion_level": ring["suspicion_level"],
            }
            break

    high_risk_connections = sum(1 for c in connections if c.get("risk_score", 0) > 70)

    return {
        "provider_id": provider_id,
        "connected_entities": len(connections),
        "high_risk_connections": high_risk_connections,
        "betweenness_centrality": round(betweenness, 4),
        "connections": connections[:20],
        "in_fraud_ring": in_ring,
        "fraud_ring_info": ring_info,
    }

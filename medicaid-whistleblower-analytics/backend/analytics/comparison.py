"""Provider peer comparison analytics."""

import logging

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Provider, Claim

logger = logging.getLogger(__name__)


def compare_provider_to_peers(db: Session, provider_id: int) -> dict:
    """Compare a single provider's billing to peer averages.

    Peers are defined as providers with the same facility_type in the same state.

    Args:
        db: Database session.
        provider_id: ID of the provider to compare.

    Returns:
        Dictionary with provider stats and peer group stats.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return {"error": "Provider not found"}

    # Provider's own stats
    provider_stats = (
        db.query(
            func.avg(Claim.amount).label("avg_amount"),
            func.sum(Claim.amount).label("total_amount"),
            func.count(Claim.id).label("claim_count"),
        )
        .filter(Claim.provider_id == provider_id)
        .first()
    )

    # Peer group stats (same facility type and state)
    peer_query = (
        db.query(
            Provider.id,
            func.avg(Claim.amount).label("avg_amount"),
        )
        .join(Claim, Claim.provider_id == Provider.id)
        .filter(
            Provider.facility_type == provider.facility_type,
            Provider.state == provider.state,
            Provider.id != provider_id,
        )
        .group_by(Provider.id)
    )
    peer_rows = peer_query.all()

    if not peer_rows:
        return {
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "avg_amount": float(provider_stats.avg_amount or 0),
                "total_amount": float(provider_stats.total_amount or 0),
                "claim_count": int(provider_stats.claim_count or 0),
            },
            "peer_group": {"count": 0, "avg_amount": None, "std_dev": None},
            "z_score": None,
        }

    peer_avgs = np.array([float(r.avg_amount) for r in peer_rows])
    peer_mean = float(np.mean(peer_avgs))
    peer_std = float(np.std(peer_avgs))

    prov_avg = float(provider_stats.avg_amount or 0)
    z_score = (prov_avg - peer_mean) / peer_std if peer_std > 0 else 0.0

    return {
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "avg_amount": prov_avg,
            "total_amount": float(provider_stats.total_amount or 0),
            "claim_count": int(provider_stats.claim_count or 0),
        },
        "peer_group": {
            "count": len(peer_rows),
            "avg_amount": peer_mean,
            "std_dev": peer_std,
        },
        "z_score": float(z_score),
    }

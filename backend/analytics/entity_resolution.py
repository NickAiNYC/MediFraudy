"""
Entity Resolution & Deduplication Engine.

Detects duplicate providers, links shell companies, and identifies
phoenix companies (dissolved/reactivated entities). Uses fuzzy matching,
address clustering, and confidence scoring to resolve entity identities
across NPIs, addresses, and name variations.

Key capabilities:
- Deduplicate providers across NPIs, EINs, addresses, phone numbers
- Link shell companies through shared addresses, principals, bank accounts
- Detect name variations using Levenshtein-like fuzzy matching
- Phone number normalization and clustering
- Address parsing and radius-based clustering
- Entity confidence scoring (0-100)
- Phoenix company detection (dissolved/reactivated entities)
"""

import logging
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models import Claim, Provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Common business suffixes stripped during name normalization
_BUSINESS_SUFFIXES = re.compile(
    r"\b(llc|llp|inc|corp|corporation|company|co|ltd|limited|pllc|pc|pa|md"
    r"|dba|group|associates|services|enterprises|holdings|partners)\b",
    re.IGNORECASE,
)

# Weights for composite similarity scoring (must sum to 1.0)
_SIMILARITY_WEIGHTS: Dict[str, float] = {
    "name": 0.30,
    "address": 0.25,
    "npi": 0.15,
    "phone": 0.10,
    "specialty": 0.10,
    "facility_type": 0.10,
}

# Earth radius in miles for Haversine calculation
_EARTH_RADIUS_MILES = 3958.8

# US state abbreviation mapping for normalization
_STATE_ABBREVIATIONS: Dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# Common address abbreviations for normalization
_ADDRESS_ABBREVIATIONS: Dict[str, str] = {
    r"\bstreet\b": "st",
    r"\bavenue\b": "ave",
    r"\bboulevard\b": "blvd",
    r"\bdrive\b": "dr",
    r"\broad\b": "rd",
    r"\blane\b": "ln",
    r"\bcourt\b": "ct",
    r"\bplace\b": "pl",
    r"\bsuite\b": "ste",
    r"\bapartment\b": "apt",
    r"\bbuilding\b": "bldg",
    r"\bfloor\b": "fl",
    r"\bnorth\b": "n",
    r"\bsouth\b": "s",
    r"\beast\b": "e",
    r"\bwest\b": "w",
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize a provider name for comparison.

    Strips legal suffixes (LLC, Inc, etc.), collapses whitespace,
    removes punctuation, and lowercases the result.

    Args:
        name: Raw provider name.

    Returns:
        Normalized name string suitable for fuzzy comparison.
    """
    if not name:
        return ""

    normalized = name.lower().strip()
    # Remove punctuation except hyphens (they may be part of names)
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    # Strip business suffixes
    normalized = _BUSINESS_SUFFIXES.sub("", normalized)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to a 10-digit US format.

    Strips country code, extensions, and non-digit characters.

    Args:
        phone: Raw phone string (e.g., "+1 (718) 555-1234 ext 5").

    Returns:
        10-digit string or empty string if unparseable.
    """
    if not phone:
        return ""

    digits = re.sub(r"\D", "", phone)

    # Strip leading country code "1" if 11 digits
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return ""

    return digits


def normalize_address(address: str) -> str:
    """Normalize a street address for comparison.

    Lowercases, expands/contracts common abbreviations, strips
    unit/suite numbers, and collapses whitespace.

    Args:
        address: Raw address string.

    Returns:
        Normalized address string.
    """
    if not address:
        return ""

    normalized = address.lower().strip()
    # Remove punctuation
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    # Apply standard abbreviations
    for pattern, replacement in _ADDRESS_ABBREVIATIONS.items():
        normalized = re.sub(pattern, replacement, normalized)

    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_zip(zip_code: str) -> str:
    """Return the 5-digit ZIP prefix."""
    if not zip_code:
        return ""
    digits = re.sub(r"\D", "", zip_code)
    return digits[:5] if len(digits) >= 5 else digits


# ---------------------------------------------------------------------------
# Similarity scoring
# ---------------------------------------------------------------------------


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return SequenceMatcher ratio between two strings (0.0 – 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _exact_match_score(a: Optional[str], b: Optional[str]) -> float:
    """Return 1.0 if both non-empty and equal, else 0.0."""
    if not a or not b:
        return 0.0
    return 1.0 if a.strip().lower() == b.strip().lower() else 0.0


def calculate_entity_similarity(entity_a: Dict[str, Any],
                                entity_b: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate a weighted similarity score between two entity records.

    Compares name (fuzzy), address (fuzzy), NPI (exact), phone (exact after
    normalization), specialty (exact), and facility type (exact).

    Args:
        entity_a: Dict with provider fields (name, address, npi, etc.).
        entity_b: Dict with provider fields.

    Returns:
        Dict containing per-field scores, the composite ``confidence``
        (0–100), and a list of ``matching_fields``.
    """
    scores: Dict[str, float] = {}

    # Name similarity (fuzzy)
    name_a = normalize_name(entity_a.get("name", ""))
    name_b = normalize_name(entity_b.get("name", ""))
    scores["name"] = _fuzzy_ratio(name_a, name_b)

    # Address similarity (fuzzy on normalized address + zip)
    addr_a = normalize_address(entity_a.get("address", ""))
    addr_b = normalize_address(entity_b.get("address", ""))
    addr_score = _fuzzy_ratio(addr_a, addr_b)

    zip_a = _normalize_zip(entity_a.get("zip_code", ""))
    zip_b = _normalize_zip(entity_b.get("zip_code", ""))
    zip_score = _exact_match_score(zip_a, zip_b)

    # Blend address text similarity with zip match
    scores["address"] = 0.7 * addr_score + 0.3 * zip_score

    # NPI exact match
    scores["npi"] = _exact_match_score(
        entity_a.get("npi"), entity_b.get("npi")
    )

    # Phone (normalized exact match)
    phone_a = normalize_phone(entity_a.get("phone", ""))
    phone_b = normalize_phone(entity_b.get("phone", ""))
    scores["phone"] = _exact_match_score(phone_a, phone_b) if phone_a and phone_b else 0.0

    # Specialty exact match
    scores["specialty"] = _exact_match_score(
        entity_a.get("specialty"), entity_b.get("specialty")
    )

    # Facility type exact match
    scores["facility_type"] = _exact_match_score(
        entity_a.get("facility_type"), entity_b.get("facility_type")
    )

    # Composite weighted confidence
    composite = sum(
        scores[field] * _SIMILARITY_WEIGHTS[field]
        for field in _SIMILARITY_WEIGHTS
    )
    confidence = round(composite * 100, 2)

    matching_fields = [f for f, s in scores.items() if s >= 0.8]

    return {
        "scores": scores,
        "confidence": confidence,
        "matching_fields": matching_fields,
    }


# ---------------------------------------------------------------------------
# Haversine distance for address clustering
# ---------------------------------------------------------------------------


def _haversine_miles(lat1: float, lon1: float,
                     lat2: float, lon2: float) -> float:
    """Haversine great-circle distance between two points in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Provider dict helper
# ---------------------------------------------------------------------------


def _provider_to_dict(provider: Provider) -> Dict[str, Any]:
    """Convert a Provider ORM instance to a plain dict."""
    return {
        "id": provider.id,
        "npi": provider.npi,
        "name": provider.name or "",
        "address": provider.address or "",
        "city": provider.city or "",
        "state": provider.state or "",
        "zip_code": provider.zip_code or "",
        "facility_type": provider.facility_type or "",
        "specialty": provider.specialty or "",
        "licensed_capacity": provider.licensed_capacity,
    }


# ---------------------------------------------------------------------------
# EntityResolver class
# ---------------------------------------------------------------------------


class EntityResolver:
    """Resolve, deduplicate, and link provider entities.

    Combines fuzzy name matching, address clustering, phone normalization,
    and NPI/EIN cross-referencing to produce entity resolution clusters
    with confidence scores.

    Usage::

        resolver = EntityResolver(db_session)
        results = resolver.resolve(similarity_threshold=0.7)
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Run the full entity resolution pipeline.

        Equivalent to the module-level ``resolve_entities`` function.

        Args:
            similarity_threshold: Minimum composite score (0–1) to consider
                two entities as potential duplicates.

        Returns:
            Dict with ``duplicates``, ``address_clusters``,
            ``phoenix_companies``, and summary ``stats``.
        """
        logger.info(
            "Starting entity resolution with threshold=%.2f",
            similarity_threshold,
        )

        duplicates = self._find_duplicates(similarity_threshold)
        address_clusters = self._cluster_by_address(radius_miles=0.1)
        phoenix = self._detect_phoenix_companies()
        shell_links = self._link_shell_companies()

        stats = {
            "total_providers": self.db.query(func.count(Provider.id)).scalar() or 0,
            "duplicate_groups": len(duplicates),
            "address_clusters": len(address_clusters),
            "phoenix_companies": len(phoenix),
            "shell_company_links": len(shell_links),
            "resolved_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Entity resolution complete: %d duplicate groups, "
            "%d address clusters, %d phoenix companies detected",
            stats["duplicate_groups"],
            stats["address_clusters"],
            stats["phoenix_companies"],
        )

        return {
            "duplicates": duplicates,
            "address_clusters": address_clusters,
            "phoenix_companies": phoenix,
            "shell_company_links": shell_links,
            "stats": stats,
        }

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def _find_duplicates(self, threshold: float) -> List[Dict[str, Any]]:
        """Find potential duplicate providers above *threshold*.

        Providers are first bucketed by normalized ZIP code (blocking) to
        reduce the O(n²) comparison space, then pairwise fuzzy-matched.
        """
        providers = self.db.query(Provider).all()
        if not providers:
            return []

        # Blocking: group by 5-digit ZIP to limit comparisons
        zip_buckets: Dict[str, List[Provider]] = defaultdict(list)
        for p in providers:
            bucket_key = _normalize_zip(p.zip_code or "")
            zip_buckets[bucket_key].append(p)

        # Also add a global bucket for providers without ZIP
        if "" in zip_buckets and len(zip_buckets) > 1:
            no_zip = zip_buckets.pop("")
            for bucket in zip_buckets.values():
                bucket.extend(no_zip)

        duplicate_groups: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[int, int]] = set()

        for _zip, bucket in zip_buckets.items():
            for pa, pb in combinations(bucket, 2):
                pair_key = (min(pa.id, pb.id), max(pa.id, pb.id))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                dict_a = _provider_to_dict(pa)
                dict_b = _provider_to_dict(pb)
                sim = calculate_entity_similarity(dict_a, dict_b)

                if sim["confidence"] >= threshold * 100:
                    duplicate_groups.append({
                        "entity_a": dict_a,
                        "entity_b": dict_b,
                        "confidence": sim["confidence"],
                        "matching_fields": sim["matching_fields"],
                        "scores": sim["scores"],
                    })

        duplicate_groups.sort(key=lambda g: g["confidence"], reverse=True)
        logger.info("Found %d potential duplicate pairs", len(duplicate_groups))
        return duplicate_groups

    # ------------------------------------------------------------------
    # Address clustering
    # ------------------------------------------------------------------

    def _cluster_by_address(self, radius_miles: float = 0.1) -> List[Dict[str, Any]]:
        """Cluster providers that share the same normalized address.

        When geocoordinates are unavailable (as with the current schema)
        we fall back to exact normalized-address + ZIP matching, which is
        equivalent to a 0-mile radius.  If lat/lon were available,
        Haversine-based radius clustering would be used.

        Args:
            radius_miles: Clustering radius (used when geo data is available).

        Returns:
            List of clusters, each a dict with ``address``, ``providers``,
            and ``count``.
        """
        providers = self.db.query(Provider).filter(
            Provider.address.isnot(None),
            Provider.address != "",
        ).all()

        addr_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for p in providers:
            key = (
                normalize_address(p.address or "")
                + "|"
                + _normalize_zip(p.zip_code or "")
            )
            addr_map[key].append(_provider_to_dict(p))

        clusters = [
            {
                "address_key": key,
                "address": members[0].get("address", ""),
                "zip_code": members[0].get("zip_code", ""),
                "providers": members,
                "count": len(members),
                "radius_miles": radius_miles,
            }
            for key, members in addr_map.items()
            if len(members) > 1
        ]

        clusters.sort(key=lambda c: c["count"], reverse=True)
        logger.info(
            "Found %d address clusters (radius=%.2f mi)",
            len(clusters),
            radius_miles,
        )
        return clusters

    # ------------------------------------------------------------------
    # Phoenix company detection
    # ------------------------------------------------------------------

    def _detect_phoenix_companies(self) -> List[Dict[str, Any]]:
        """Detect dissolved/reactivated (phoenix) entities.

        A phoenix company is flagged when a new provider appears at the
        same address (and optionally with a similar name) shortly after
        another provider at that address stops billing.

        Heuristic:
        1. Group providers by normalized address + ZIP.
        2. For each group, find providers whose last claim date is
           followed by another provider's first claim date within 180 days
           and whose names are somewhat similar.
        """
        providers = self.db.query(Provider).filter(
            Provider.address.isnot(None),
            Provider.address != "",
        ).all()

        if not providers:
            return []

        # Build address groups
        addr_groups: Dict[str, List[Provider]] = defaultdict(list)
        for p in providers:
            key = (
                normalize_address(p.address or "")
                + "|"
                + _normalize_zip(p.zip_code or "")
            )
            addr_groups[key].append(p)

        phoenix_results: List[Dict[str, Any]] = []

        for _addr_key, group in addr_groups.items():
            if len(group) < 2:
                continue

            # Fetch billing date ranges per provider in this group
            provider_ranges: List[Tuple[Provider, Any, Any]] = []
            for p in group:
                date_range = (
                    self.db.query(
                        func.min(Claim.claim_date),
                        func.max(Claim.claim_date),
                    )
                    .filter(Claim.provider_id == p.id)
                    .first()
                )
                first_date, last_date = date_range if date_range else (None, None)
                if first_date and last_date:
                    provider_ranges.append((p, first_date, last_date))

            # Compare all pairs for phoenix pattern
            for (pa, first_a, last_a), (pb, first_b, last_b) in combinations(provider_ranges, 2):
                gap_days: Optional[int] = None

                # Determine which provider preceded the other
                predecessor, successor = pa, pb
                if last_a < first_b:
                    gap_days = (first_b - last_a).days
                elif last_b < first_a:
                    gap_days = (first_a - last_b).days
                    predecessor, successor = pb, pa

                if gap_days is not None and gap_days <= 180:
                    name_sim = _fuzzy_ratio(
                        normalize_name(predecessor.name or ""),
                        normalize_name(successor.name or ""),
                    )
                    phoenix_results.append({
                        "predecessor": _provider_to_dict(predecessor),
                        "successor": _provider_to_dict(successor),
                        "gap_days": gap_days,
                        "name_similarity": round(name_sim, 4),
                        "same_address": True,
                        "risk_level": (
                            "high" if name_sim >= 0.6 else
                            "medium" if name_sim >= 0.3 else
                            "low"
                        ),
                    })

        phoenix_results.sort(
            key=lambda r: (r["risk_level"] == "high", r["name_similarity"]),
            reverse=True,
        )
        logger.info("Detected %d potential phoenix companies", len(phoenix_results))
        return phoenix_results

    # ------------------------------------------------------------------
    # Shell company linking
    # ------------------------------------------------------------------

    def _link_shell_companies(self) -> List[Dict[str, Any]]:
        """Link potential shell companies through shared attributes.

        Shell companies often share addresses, phone numbers, or
        principals with other entities.  This method identifies providers
        that share a normalized address *and* have suspiciously similar
        names or identical facility types.
        """
        providers = self.db.query(Provider).filter(
            Provider.address.isnot(None),
            Provider.address != "",
        ).all()

        addr_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for p in providers:
            key = (
                normalize_address(p.address or "")
                + "|"
                + _normalize_zip(p.zip_code or "")
            )
            addr_groups[key].append(_provider_to_dict(p))

        links: List[Dict[str, Any]] = []
        for key, members in addr_groups.items():
            if len(members) < 2:
                continue

            for a, b in combinations(members, 2):
                shared_attrs: List[str] = ["address"]

                if (a.get("facility_type") and b.get("facility_type")
                        and a["facility_type"].lower() == b["facility_type"].lower()):
                    shared_attrs.append("facility_type")

                name_sim = _fuzzy_ratio(
                    normalize_name(a.get("name", "")),
                    normalize_name(b.get("name", "")),
                )
                if name_sim >= 0.5:
                    shared_attrs.append("similar_name")

                if len(shared_attrs) >= 2:
                    links.append({
                        "entity_a": a,
                        "entity_b": b,
                        "shared_attributes": shared_attrs,
                        "name_similarity": round(name_sim, 4),
                        "risk_indicator": "shell_company",
                    })

        links.sort(key=lambda lnk: len(lnk["shared_attributes"]), reverse=True)
        logger.info("Found %d shell company links", len(links))
        return links


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def resolve_entities(db: Session,
                     similarity_threshold: float = 0.7) -> Dict[str, Any]:
    """Run the full entity resolution pipeline.

    Main entry point for entity resolution. Detects duplicates, clusters
    addresses, flags phoenix companies, and links shell entities.

    Args:
        db: SQLAlchemy database session.
        similarity_threshold: Minimum similarity (0–1) for duplicate
            detection.  Default ``0.7`` (70 %).

    Returns:
        Dict with keys ``duplicates``, ``address_clusters``,
        ``phoenix_companies``, ``shell_company_links``, and ``stats``.
    """
    resolver = EntityResolver(db)
    return resolver.resolve(similarity_threshold)


def find_duplicate_providers(db: Session,
                             threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Find potential duplicate providers above *threshold*.

    Args:
        db: SQLAlchemy database session.
        threshold: Similarity threshold (0–1).

    Returns:
        List of dicts, each with ``entity_a``, ``entity_b``,
        ``confidence`` (0–100), ``matching_fields``, and ``scores``.
    """
    resolver = EntityResolver(db)
    return resolver._find_duplicates(threshold)


def detect_phoenix_companies(db: Session) -> List[Dict[str, Any]]:
    """Detect dissolved/reactivated (phoenix) entities.

    Looks for providers that stopped billing at an address followed
    shortly by a new provider at the same address.

    Args:
        db: SQLAlchemy database session.

    Returns:
        List of dicts describing predecessor/successor pairs.
    """
    resolver = EntityResolver(db)
    return resolver._detect_phoenix_companies()


def cluster_by_address(db: Session,
                       radius_miles: float = 0.1) -> List[Dict[str, Any]]:
    """Cluster providers that share the same address.

    Args:
        db: SQLAlchemy database session.
        radius_miles: Clustering radius in miles (used when geo data is
            available; falls back to exact address matching otherwise).

    Returns:
        List of cluster dicts with ``address``, ``providers``, ``count``.
    """
    resolver = EntityResolver(db)
    return resolver._cluster_by_address(radius_miles)

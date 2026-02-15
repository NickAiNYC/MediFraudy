"""
Cryptographic signing and chain of custody for evidence packages.
Ensures court-admissible forensic integrity.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
import secrets

logger = logging.getLogger(__name__)


class EvidenceIntegrityService:
    """
    Handles cryptographic signing and verification of evidence packages.
    Implements chain of custody tracking for forensic admissibility.
    """
    
    SIGNATURE_ALGORITHM = "SHA-256"
    EVIDENCE_VERSION = "1.0"
    
    def sign_package(
        self,
        package_id: str,
        package_data: Dict[str, Any],
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Sign evidence package with cryptographic hash.
        
        Args:
            package_id: Unique package identifier
            package_data: Complete evidence package data
            user_id: User generating the evidence
            db: Database session
        
        Returns:
            Signed package with integrity metadata
        """
        # Add metadata
        package_data["metadata"] = {
            "package_id": package_id,
            "version": self.EVIDENCE_VERSION,
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by_user_id": user_id,
            "algorithm": self.SIGNATURE_ALGORITHM
        }
        
        # Create canonical JSON (sorted keys for consistent hashing)
        canonical_json = json.dumps(package_data, sort_keys=True, indent=None)
        
        # Generate SHA-256 hash
        package_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Add signature to package
        package_data["signature"] = {
            "algorithm": self.SIGNATURE_ALGORITHM,
            "hash": package_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store signature in database (immutable record)
        try:
            from models import EvidenceSignature, AuditLog
            
            signature_record = EvidenceSignature(
                package_id=package_id,
                hash_algorithm=self.SIGNATURE_ALGORITHM,
                signature_hash=package_hash,
                user_id=user_id,
                package_version=self.EVIDENCE_VERSION
            )
            db.add(signature_record)
            
            # Create audit log entry
            audit_entry = AuditLog(
                user_id=user_id,
                action="EVIDENCE_PACKAGE_SIGNED",
                resource_type="evidence_package",
                resource_id=package_id,
                metadata_json=json.dumps({
                    "hash": package_hash,
                    "algorithm": self.SIGNATURE_ALGORITHM
                })
            )
            db.add(audit_entry)
            
            db.commit()
            
            logger.info(f"Evidence package {package_id} signed with hash {package_hash[:16]}...")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store evidence signature: {e}")
            raise
        
        return package_data
    
    def verify_package(
        self,
        package_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Verify integrity of evidence package.
        
        Args:
            package_data: Evidence package with signature
            db: Database session
        
        Returns:
            Verification result with tamper detection
        """
        if "signature" not in package_data or "metadata" not in package_data:
            return {
                "valid": False,
                "reason": "Missing signature or metadata"
            }
        
        package_id = package_data["metadata"].get("package_id")
        stored_hash = package_data["signature"]["hash"]
        
        # Retrieve signature from database
        from models import EvidenceSignature, AuditLog
        
        signature_record = db.query(EvidenceSignature).filter(
            EvidenceSignature.package_id == package_id
        ).first()
        
        if not signature_record:
            return {
                "valid": False,
                "reason": "Signature not found in database"
            }
        
        # Remove signature for re-computation
        package_copy = package_data.copy()
        del package_copy["signature"]
        
        # Re-compute hash
        canonical_json = json.dumps(package_copy, sort_keys=True, indent=None)
        computed_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Compare hashes (constant-time comparison)
        hashes_match = secrets.compare_digest(computed_hash, stored_hash)
        db_match = secrets.compare_digest(computed_hash, signature_record.signature_hash)
        
        # Log verification attempt
        audit_entry = AuditLog(
            user_id=None,  # System action
            action="EVIDENCE_PACKAGE_VERIFIED",
            resource_type="evidence_package",
            resource_id=package_id,
            metadata_json=json.dumps({
                "valid": hashes_match and db_match,
                "stored_hash": stored_hash[:16] + "...",
                "computed_hash": computed_hash[:16] + "..."
            })
        )
        db.add(audit_entry)
        db.commit()
        
        if not (hashes_match and db_match):
            logger.warning(f"Evidence package {package_id} FAILED integrity check!")
            return {
                "valid": False,
                "reason": "Hash mismatch - package has been tampered with",
                "stored_hash": stored_hash,
                "computed_hash": computed_hash
            }
        
        return {
            "valid": True,
            "package_id": package_id,
            "generated_at": package_data["metadata"]["generated_at"],
            "signature_hash": stored_hash[:16] + "...",
            "algorithm": self.SIGNATURE_ALGORITHM
        }
    
    def get_chain_of_custody(
        self,
        package_id: str,
        db: Session
    ) -> list:
        """
        Retrieve complete chain of custody for evidence package.
        
        Args:
            package_id: Package identifier
            db: Database session
        
        Returns:
            Chronological list of all access/modification events
        """
        from models import AuditLog
        
        audit_logs = db.query(AuditLog).filter(
            AuditLog.resource_type == "evidence_package",
            AuditLog.resource_id == package_id
        ).order_by(AuditLog.timestamp.asc()).all()
        
        chain = []
        for log in audit_logs:
            chain.append({
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "action": log.action,
                "metadata": json.loads(log.metadata_json) if log.metadata_json else {}
            })
        
        return chain


# Global instance
evidence_integrity = EvidenceIntegrityService()

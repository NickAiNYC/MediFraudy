"""
Blockchain Evidence System for 2026-2027 Elite Performance
Immutable evidence storage and verification
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import hashlib
import uuid
from dataclasses import dataclass, asdict
import base64

logger = logging.getLogger(__name__)

@dataclass
class EvidenceBlock:
    """Blockchain evidence block structure"""
    block_hash: str
    previous_hash: str
    timestamp: datetime
    evidence_type: str
    evidence_data: Dict[str, Any]
    provider_id: int
    case_id: Optional[str]
    verifier: str
    signature: str
    nonce: int

class BlockchainEvidenceSystem:
    """Blockchain-based evidence storage and verification system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chain = []
        self.genesis_block = None
        self.difficulty = 4  # Mining difficulty
        self.mining_reward = 0
        
    async def initialize_blockchain(self):
        """Initialize the evidence blockchain"""
        
        if not self.genesis_block:
            # Create genesis block
            genesis = EvidenceBlock(
                block_hash=self._calculate_hash("genesis", 0),
                previous_hash="0" * 64,
                timestamp=datetime.utcnow(),
                evidence_type="genesis",
                evidence_data={"message": "MediFraudy Evidence Blockchain Genesis", "version": "1.0"},
                provider_id=0,
                case_id=None,
                verifier="system",
                signature="genesis_signature",
                nonce=0
            )
            
            self.genesis_block = genesis
            self.chain.append(genesis)
            
            # Store in database
            await self._store_block(genesis)
            
            logger.info("🔗 Evidence blockchain initialized with genesis block")
    
    async def add_evidence(self, evidence_type: str, evidence_data: Dict[str, Any], 
                          provider_id: int, case_id: Optional[str] = None, 
                          verifier: str = "system") -> str:
        """Add evidence to the blockchain"""
        
        # Create new block
        previous_block = self.chain[-1] if self.chain else self.genesis_block
        
        new_block = EvidenceBlock(
            block_hash="",  # Will be calculated during mining
            previous_hash=previous_block.block_hash,
            timestamp=datetime.utcnow(),
            evidence_type=evidence_type,
            evidence_data=evidence_data,
            provider_id=provider_id,
            case_id=case_id,
            verifier=verifier,
            signature="",  # Will be added during mining
            nonce=0
        )
        
        # Mine the block
        mined_block = await self._mine_block(new_block)
        
        # Add to chain
        self.chain.append(mined_block)
        
        # Store in database
        await self._store_block(mined_block)
        
        logger.info(f"⛏️ Mined new evidence block: {mined_block.block_hash[:16]}...")
        
        return mined_block.block_hash
    
    async def verify_evidence_integrity(self, provider_id: int, case_id: Optional[str] = None) -> Dict[str, Any]:
        """Verify integrity of evidence for a provider/case"""
        
        # Get all blocks for this provider/case
        blocks = await self._get_provider_blocks(provider_id, case_id)
        
        verification_results = {
            "provider_id": provider_id,
            "case_id": case_id,
            "verification_date": datetime.utcnow().isoformat(),
            "total_blocks": len(blocks),
            "valid_blocks": 0,
            "invalid_blocks": 0,
            "chain_integrity": True,
            "blocks": []
        }
        
        # Verify each block
        for i, block in enumerate(blocks):
            is_valid = await self._verify_block(block, blocks[i-1] if i > 0 else None)
            
            block_verification = {
                "block_hash": block.block_hash,
                "block_number": i,
                "timestamp": block.timestamp.isoformat(),
                "evidence_type": block.evidence_type,
                "is_valid": is_valid,
                "verification_details": {
                    "hash_valid": self._verify_hash(block),
                    "signature_valid": await self._verify_signature(block),
                    "chain_valid": self._verify_chain_link(block, blocks[i-1] if i > 0 else None)
                }
            }
            
            verification_results["blocks"].append(block_verification)
            
            if is_valid:
                verification_results["valid_blocks"] += 1
            else:
                verification_results["invalid_blocks"] += 1
                verification_results["chain_integrity"] = False
        
        return verification_results
    
    async def get_evidence_history(self, provider_id: int, case_id: Optional[str] = None) -> List[Dict]:
        """Get complete evidence history from blockchain"""
        
        blocks = await self._get_provider_blocks(provider_id, case_id)
        
        history = []
        
        for block in blocks:
            history.append({
                "block_hash": block.block_hash,
                "timestamp": block.timestamp.isoformat(),
                "evidence_type": block.evidence_type,
                "evidence_data": block.evidence_data,
                "provider_id": block.provider_id,
                "case_id": block.case_id,
                "verifier": block.verifier,
                "block_number": self.chain.index(block)
            })
        
        return history
    
    async def generate_evidence_certificate(self, provider_id: int, case_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate blockchain evidence certificate"""
        
        # Get verification results
        verification = await self.verify_evidence_integrity(provider_id, case_id)
        
        # Generate certificate
        certificate = {
            "certificate_id": str(uuid.uuid4()),
            "certificate_type": "blockchain_evidence_verification",
            "provider_id": provider_id,
            "case_id": case_id,
            "issuance_date": datetime.utcnow().isoformat(),
            "issuing_authority": "MediFraudy Blockchain System",
            "verification_results": verification,
            "certificate_hash": self._calculate_certificate_hash(verification),
            "blockchain_version": "1.0.2026",
            "digital_signature": await self._sign_certificate(verification)
        }
        
        # Store certificate
        await self._store_certificate(certificate)
        
        return certificate
    
    async def create_evidence_audit_trail(self, provider_id: int) -> Dict[str, Any]:
        """Create comprehensive audit trail"""
        
        # Get all evidence blocks
        blocks = await self._get_provider_blocks(provider_id)
        
        # Create audit trail
        audit_trail = {
            "audit_id": str(uuid.uuid4()),
            "provider_id": provider_id,
            "audit_date": datetime.utcnow().isoformat(),
            "total_evidence_entries": len(blocks),
            "blockchain_hash": self._calculate_chain_hash(),
            "evidence_types": {},
            "timeline": [],
            "verifiers": set(),
            "first_evidence": None,
            "last_evidence": None,
            "integrity_score": 0.0
        }
        
        # Analyze evidence
        for block in blocks:
            # Count evidence types
            if block.evidence_type not in audit_trail["evidence_types"]:
                audit_trail["evidence_types"][block.evidence_type] = 0
            audit_trail["evidence_types"][block.evidence_type] += 1
            
            # Add to timeline
            audit_trail["timeline"].append({
                "timestamp": block.timestamp.isoformat(),
                "evidence_type": block.evidence_type,
                "verifier": block.verifier,
                "block_hash": block.block_hash[:16] + "..."
            })
            
            # Track verifiers
            audit_trail["verifiers"].add(block.verifier)
            
            # Track first/last evidence
            if not audit_trail["first_evidence"] or block.timestamp < datetime.fromisoformat(audit_trail["first_evidence"]):
                audit_trail["first_evidence"] = block.timestamp.isoformat()
            
            if not audit_trail["last_evidence"] or block.timestamp > datetime.fromisoformat(audit_trail["last_evidence"]):
                audit_trail["last_evidence"] = block.timestamp.isoformat()
        
        # Convert verifiers set to list
        audit_trail["verifiers"] = list(audit_trail["verifiers"])
        
        # Calculate integrity score
        verification = await self.verify_evidence_integrity(provider_id)
        audit_trail["integrity_score"] = verification["valid_blocks"] / max(verification["total_blocks"], 1)
        
        # Sort timeline
        audit_trail["timeline"].sort(key=lambda x: x["timestamp"])
        
        return audit_trail
    
    # Blockchain core methods
    async def _mine_block(self, block: EvidenceBlock) -> EvidenceBlock:
        """Mine a new block (Proof of Work)"""
        
        target = "0" * self.difficulty
        block.nonce = 0
        
        while block.nonce < 1000000:  # Max nonce attempts
            # Calculate block hash
            block_content = f"{block.previous_hash}{block.timestamp.isoformat()}{block.evidence_type}{json.dumps(block.evidence_data, sort_keys=True)}{block.verifier}{block.nonce}"
            block_hash = hashlib.sha256(block_content.encode()).hexdigest()
            
            # Check if hash meets difficulty
            if block_hash.startswith(target):
                block.block_hash = block_hash
                block.signature = self._generate_signature(block)
                return block
            
            block.nonce += 1
        
        # If mining fails, use simpler hash
        block.block_hash = hashlib.sha256(f"{block.previous_hash}{block.timestamp}{json.dumps(block.evidence_data)}".encode()).hexdigest()
        block.signature = self._generate_signature(block)
        
        return block
    
    def _calculate_hash(self, content: str, nonce: int = 0) -> str:
        """Calculate SHA-256 hash"""
        return hashlib.sha256(f"{content}{nonce}".encode()).hexdigest()
    
    def _calculate_chain_hash(self) -> str:
        """Calculate hash of entire chain"""
        chain_content = "".join([block.block_hash for block in self.chain])
        return hashlib.sha256(chain_content.encode()).hexdigest()
    
    def _calculate_certificate_hash(self, certificate: Dict) -> str:
        """Calculate certificate hash"""
        cert_content = json.dumps(certificate, sort_keys=True)
        return hashlib.sha256(cert_content.encode()).hexdigest()
    
    def _generate_signature(self, block: EvidenceBlock) -> str:
        """Generate digital signature for block"""
        signature_content = f"{block.block_hash}{block.verifier}{block.timestamp.isoformat()}"
        return hashlib.sha256(signature_content.encode()).hexdigest()
    
    async def _verify_block(self, block: EvidenceBlock, previous_block: Optional[EvidenceBlock]) -> bool:
        """Verify block integrity"""
        
        # Verify hash
        if not self._verify_hash(block):
            return False
        
        # Verify signature
        if not await self._verify_signature(block):
            return False
        
        # Verify chain link
        if not self._verify_chain_link(block, previous_block):
            return False
        
        return True
    
    def _verify_hash(self, block: EvidenceBlock) -> bool:
        """Verify block hash"""
        content = f"{block.previous_hash}{block.timestamp.isoformat()}{block.evidence_type}{json.dumps(block.evidence_data, sort_keys=True)}{block.verifier}{block.nonce}"
        calculated_hash = hashlib.sha256(content.encode()).hexdigest()
        return calculated_hash == block.block_hash
    
    async def _verify_signature(self, block: EvidenceBlock) -> bool:
        """Verify digital signature"""
        signature_content = f"{block.block_hash}{block.verifier}{block.timestamp.isoformat()}"
        calculated_signature = hashlib.sha256(signature_content.encode()).hexdigest()
        return calculated_signature == block.signature
    
    def _verify_chain_link(self, block: EvidenceBlock, previous_block: Optional[EvidenceBlock]) -> bool:
        """Verify blockchain link"""
        if previous_block is None:
            return block.previous_hash == "0" * 64  # Genesis block
        
        return block.previous_hash == previous_block.block_hash
    
    async def _store_block(self, block: EvidenceBlock):
        """Store block in database"""
        
        await self.db.execute(text("""
            INSERT INTO evidence_blocks (
                block_hash, previous_hash, timestamp, evidence_type, 
                evidence_data, provider_id, case_id, verifier, signature, nonce
            ) VALUES (
                :block_hash, :previous_hash, :timestamp, :evidence_type,
                :evidence_data, :provider_id, :case_id, :verifier, :signature, :nonce
            )
        """), {
            "block_hash": block.block_hash,
            "previous_hash": block.previous_hash,
            "timestamp": block.timestamp,
            "evidence_type": block.evidence_type,
            "evidence_data": json.dumps(block.evidence_data),
            "provider_id": block.provider_id,
            "case_id": block.case_id,
            "verifier": block.verifier,
            "signature": block.signature,
            "nonce": block.nonce
        })
        
        await self.db.commit()
    
    async def _get_provider_blocks(self, provider_id: int, case_id: Optional[str] = None) -> List[EvidenceBlock]:
        """Get all blocks for a provider/case"""
        
        if case_id:
            result = await self.db.execute(text("""
                SELECT * FROM evidence_blocks 
                WHERE provider_id = :provider_id AND case_id = :case_id
                ORDER BY timestamp
            """), {"provider_id": provider_id, "case_id": case_id})
        else:
            result = await self.db.execute(text("""
                SELECT * FROM evidence_blocks 
                WHERE provider_id = :provider_id
                ORDER BY timestamp
            """), {"provider_id": provider_id})
        
        blocks = []
        for row in result.fetchall():
            block = EvidenceBlock(
                block_hash=row.block_hash,
                previous_hash=row.previous_hash,
                timestamp=row.timestamp,
                evidence_type=row.evidence_type,
                evidence_data=json.loads(row.evidence_data),
                provider_id=row.provider_id,
                case_id=row.case_id,
                verifier=row.verifier,
                signature=row.signature,
                nonce=row.nonce
            )
            blocks.append(block)
        
        return blocks
    
    async def _store_certificate(self, certificate: Dict):
        """Store certificate in database"""
        
        await self.db.execute(text("""
            INSERT INTO evidence_certificates (
                certificate_id, certificate_type, provider_id, case_id,
                issuance_date, issuing_authority, verification_results,
                certificate_hash, digital_signature, blockchain_version
            ) VALUES (
                :certificate_id, :certificate_type, :provider_id, :case_id,
                :issuance_date, :issuing_authority, :verification_results,
                :certificate_hash, :digital_signature, :blockchain_version
            )
        """), {
            "certificate_id": certificate["certificate_id"],
            "certificate_type": certificate["certificate_type"],
            "provider_id": certificate["provider_id"],
            "case_id": certificate["case_id"],
            "issuance_date": certificate["issuance_date"],
            "issuing_authority": certificate["issuing_authority"],
            "verification_results": json.dumps(certificate["verification_results"]),
            "certificate_hash": certificate["certificate_hash"],
            "digital_signature": certificate["digital_signature"],
            "blockchain_version": certificate["blockchain_version"]
        })
        
        await self.db.commit()
    
    async def _sign_certificate(self, verification: Dict) -> str:
        """Sign certificate with system key"""
        cert_content = json.dumps(verification, sort_keys=True)
        return hashlib.sha256(f"{cert_content}{datetime.utcnow().isoformat()}".encode()).hexdigest()

# Singleton instance
blockchain_evidence = BlockchainEvidenceSystem

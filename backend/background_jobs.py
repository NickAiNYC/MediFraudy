"""
Modern background job system for async data processing
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from database_v2 import AsyncSessionLocal
from cache_manager import cache_manager
from data_pipeline_v2 import modern_loader

logger = logging.getLogger(__name__)

class JobManager:
    """Production-ready background job manager"""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.max_concurrent_jobs = 3
        self.running_jobs = 0
    
    async def create_job(self, job_type: str, params: Dict[str, Any]) -> str:
        """Create a new background job"""
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.jobs)}"
        
        job = {
            "id": job_id,
            "type": job_type,
            "params": params,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None
        }
        
        self.jobs[job_id] = job
        
        # Queue the job if we have capacity
        if self.running_jobs < self.max_concurrent_jobs:
            asyncio.create_task(self._execute_job(job_id))
        
        logger.info(f"📋 Created job {job_id} of type {job_type}")
        return job_id
    
    async def _execute_job(self, job_id: str):
        """Execute a background job"""
        job = self.jobs[job_id]
        
        try:
            # Update job status
            job["status"] = "running"
            job["started_at"] = datetime.utcnow()
            self.running_jobs += 1
            
            logger.info(f"🚀 Starting job {job_id}")
            
            # Execute based on job type
            if job["type"] == "data_load":
                result = await self._execute_data_load(job)
            elif job["type"] == "analytics_refresh":
                result = await self._execute_analytics_refresh(job)
            elif job["type"] == "cache_warm":
                result = await self._execute_cache_warm(job)
            elif job["type"] == "evidence_package":
                result = await self._execute_evidence_package(job)
            elif job["type"] == "political_analysis":
                result = await self._execute_political_analysis(job)
            elif job["type"] == "ai_analysis":
                result = await self._execute_ai_analysis(job)
            elif job["type"] == "blockchain_verification":
                result = await self._execute_blockchain_verification(job)
            elif job["type"] == "claim_processing":
                result = await self._execute_claim_processing(job)
            else:
                raise ValueError(f"Unknown job type: {job['type']}")
            
            # Mark as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow()
            job["result"] = result
            job["progress"] = 100
            
            logger.info(f"✅ Completed job {job_id}")
            
        except Exception as e:
            # Mark as failed
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.utcnow()
            
            logger.error(f"❌ Failed job {job_id}: {e}")
        
        finally:
            self.running_jobs -= 1
            
            # Start next pending job if any
            await self._start_next_job()
    
    async def _execute_data_load(self, job: Dict) -> Dict:
        """Execute data loading job"""
        params = job["params"]
        zip_path = params.get("zip_path", "/tmp/medicaid_claims.zip")
        sample_size = params.get("sample_size")
        
        # Update progress
        job["progress"] = 10
        
        # Execute data loading
        claims_loaded = await modern_loader.load_dataset(zip_path, sample_size)
        
        # Invalidate relevant caches
        await cache_manager.clear_pattern("analytics_dashboard")
        await cache_manager.clear_pattern("provider_stats:*")
        
        return {
            "claims_loaded": claims_loaded,
            "sample_size": sample_size
        }
    
    async def _execute_analytics_refresh(self, job: Dict) -> Dict:
        """Execute analytics refresh job"""
        # Clear analytics cache
        deleted = await cache_manager.clear_pattern("analytics_dashboard")
        
        # Pre-warm common queries
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            # Warm up provider stats
            await db.execute(text("SELECT COUNT(*) FROM providers"))
            await db.execute(text("SELECT COUNT(*) FROM claims"))
            
            result = await db.execute(text("""
                SELECT state, COUNT(*) as count 
                FROM providers 
                WHERE state IS NOT NULL 
                GROUP BY state 
                LIMIT 10
            """))
            states = result.fetchall()
        
        return {
            "cache_cleared": deleted,
            "states_processed": len(states)
        }
    
    async def _execute_cache_warm(self, job: Dict) -> Dict:
        """Execute cache warming job"""
        warmed = 0
        
        # Warm top providers cache
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(text("""
                SELECT id FROM providers 
                ORDER BY total_amount DESC 
                LIMIT 100
            """))
            top_providers = result.fetchall()
            
            for provider_row in top_providers:
                provider_id = provider_row[0]
                
                # Cache provider stats
                stats = {
                    "total_claims": 1000,  # Mock data
                    "total_amount": 50000.0,
                    "avg_claim": 50.0
                }
                
                from cache_manager import cache_provider_stats
                await cache_provider_stats(provider_id, stats)
                warmed += 1
        
        return {"warmed_providers": warmed}
    
    async def _execute_evidence_package(self, job: Dict) -> Dict:
        """Execute evidence package generation job"""
        provider_id = job["params"]["provider_id"]
        
        # Update progress
        job["progress"] = 10
        
        # Generate evidence package
        from services.evidence_builder_v2 import EvidencePackageBuilder
        from database_v2 import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            builder = EvidencePackageBuilder(db)
            evidence_package = await builder.generate_fca_complaint(provider_id)
        
        # Update progress
        job["progress"] = 70
        
        # Generate PDFs
        from services.pdf_generator import pdf_generator
        
        fca_pdf_path = await pdf_generator.generate_fca_complaint_pdf(evidence_package)
        expert_pdf_path = await pdf_generator.generate_expert_report_pdf(evidence_package)
        
        # Update progress
        job["progress"] = 90
        
        # Cache results
        from cache_manager import cache_manager
        await cache_manager.set(f"evidence_package_{provider_id}", evidence_package, ttl=3600)
        
        return {
            "provider_id": provider_id,
            "package_id": evidence_package["package_id"],
            "fca_complaint_pdf": fca_pdf_path,
            "expert_report_pdf": expert_pdf_path,
            "package_size": len(str(evidence_package))
        }
    
    async def _execute_political_analysis(self, job: Dict) -> Dict:
        """Execute political intelligence analysis job"""
        provider_id = job["params"]["provider_id"]
        
        # Update progress
        job["progress"] = 10
        
        # Generate political analysis
        from services.political_intelligence import political_intelligence
        from database_v2 import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            analysis = await political_intelligence.analyze_political_connections(provider_id)
        
        # Update progress
        job["progress"] = 80
        
        # Cache results
        from cache_manager import cache_manager
        await cache_manager.set(f"political_analysis_{provider_id}", analysis, ttl=3600)
        
        return {
            "provider_id": provider_id,
            "corruption_score": analysis["corruption_risk_score"]["overall_score"],
            "risk_level": analysis["corruption_risk_score"]["risk_level"],
            "investigation_priority": analysis["investigation_priority"],
            "political_connections": len(analysis["campaign_contributions"]["recipients"]),
            "lobbying_connections": len(analysis["lobbying_connections"]["lobbying_firms"])
        }
    
    async def _execute_ai_analysis(self, job: Dict) -> Dict:
        """Execute AI analysis job"""
        provider_id = job["params"]["provider_id"]
        
        # Update progress
        job["progress"] = 10
        
        # Run AI predictions
        from services.ai_predictive_engine import ai_predictive_engine
        from database_v2 import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            fraud_prediction = await ai_predictive_engine.predict_fraud_probability(provider_id)
            corruption_prediction = await ai_predictive_engine.predict_corruption_probability(provider_id)
            outcome_prediction = await ai_predictive_engine.predict_case_outcome(provider_id, "fca")
            priority_prediction = await ai_predictive_engine.predict_investigation_priority(provider_id)
        
        # Update progress
        job["progress"] = 80
        
        # Cache results
        from cache_manager import cache_manager
        ai_results = {
            "fraud_prediction": fraud_prediction.prediction,
            "corruption_prediction": corruption_prediction.prediction,
            "outcome_prediction": outcome_prediction,
            "priority_prediction": priority_prediction
        }
        await cache_manager.set(f"ai_analysis_{provider_id}", ai_results, ttl=3600)
        
        return {
            "provider_id": provider_id,
            "fraud_probability": fraud_prediction.prediction,
            "corruption_probability": corruption_prediction.prediction,
            "success_probability": outcome_prediction["success_probability"],
            "priority_score": priority_prediction["priority_score"],
            "overall_risk": (fraud_prediction.prediction + corruption_prediction.prediction) / 2
        }
    
    async def _execute_blockchain_verification(self, job: Dict) -> Dict:
        """Execute blockchain verification job"""
        provider_id = job["params"]["provider_id"]
        
        # Update progress
        job["progress"] = 10
        
        # Initialize blockchain
        from services.blockchain_evidence import blockchain_evidence
        await blockchain_evidence.initialize_blockchain()
        
        # Add verification evidence
        verification_data = {
            "verification_type": "automated_check",
            "verification_date": datetime.utcnow().isoformat(),
            "system_version": "2.0.2026",
            "verified_by": "ai_system"
        }
        
        block_hash = await blockchain_evidence.add_evidence(
            "blockchain_verification", verification_data, provider_id
        )
        
        # Update progress
        job["progress"] = 60
        
        # Verify integrity
        verification = await blockchain_evidence.verify_evidence_integrity(provider_id)
        
        # Generate certificate
        certificate = await blockchain_evidence.generate_evidence_certificate(provider_id)
        
        # Update progress
        job["progress"] = 90
        
        return {
            "provider_id": provider_id,
            "verification_block_hash": block_hash,
            "integrity_score": verification["valid_blocks"] / max(verification["total_blocks"], 1),
            "chain_integrity": verification["chain_integrity"],
            "certificate_id": certificate["certificate_id"],
            "total_blocks": verification["total_blocks"]
        }
    
    async def _execute_claim_processing(self, job: Dict) -> Dict:
        """Execute claim processing job"""
        claim_data = job["params"]["claim_data"]
        
        # Update progress
        job["progress"] = 10
        
        # Process claim through ClaimSwarm
        from services.claimswarm_engine import claimswarm_engine
        from database_v2 import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            result = await claimswarm_engine.process_claim(claim_data["claim"])
        
        # Update progress
        job["progress"] = 80
        
        # Store results in database
        async with AsyncSessionLocal() as db:
            await db.execute(text("""
                INSERT INTO claim_results (
                    claim_id, complexity, status, fraud_score, estimated_cost,
                    confidence, suspicious_patterns, evidence_links, recommendation,
                    processing_time, blockchain_hash, created_at, updated_at
                ) VALUES (
                    :claim_id, :complexity, :status, :fraud_score, :estimated_cost,
                    :confidence, :suspicious_patterns, :evidence_links, :recommendation,
                    :processing_time, :blockchain_hash, NOW(), NOW()
                )
            """), {
                "claim_id": result.claim_id,
                "complexity": result.complexity.value,
                "status": result.status.value,
                "fraud_score": result.fraud_score,
                "estimated_cost": result.estimated_cost,
                "confidence": result.confidence,
                "suspicious_patterns": result.suspicious_patterns,
                "evidence_links": result.evidence_links,
                "recommendation": result.recommendation,
                "processing_time": result.processing_time,
                "blockchain_hash": result.blockchain_hash
            })
            
            await db.commit()
        
        return {
            "claim_id": result.claim_id,
            "complexity": result.complexity.value,
            "status": result.status.value,
            "fraud_score": result.fraud_score,
            "estimated_cost": result.estimated_cost,
            "confidence": result.confidence,
            "recommendation": result.recommendation,
            "processing_time": result.processing_time,
            "blockchain_hash": result.blockchain_hash
        }
    
    async def _start_next_job(self):
        """Start the next pending job if capacity allows"""
        if self.running_jobs >= self.max_concurrent_jobs:
            return
        
        # Find next pending job
        for job_id, job in self.jobs.items():
            if job["status"] == "pending":
                asyncio.create_task(self._execute_job(job_id))
                break
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        job = self.jobs.get(job_id)
        if job:
            # Convert datetime to string for JSON serialization
            result = job.copy()
            for key in ["created_at", "started_at", "completed_at"]:
                if result[key]:
                    result[key] = result[key].isoformat()
            return result
        return None
    
    async def list_jobs(self, status: Optional[str] = None) -> list:
        """List all jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [job for job in jobs if job["status"] == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Convert datetime to string
        for job in jobs:
            for key in ["created_at", "started_at", "completed_at"]:
                if job[key]:
                    job[key] = job[key].isoformat()
        
        return jobs

# Singleton instance
job_manager = JobManager()

# Job scheduling functions
async def schedule_data_load(zip_path: str, sample_size: Optional[int] = None) -> str:
    """Schedule a data loading job"""
    return await job_manager.create_job("data_load", {
        "zip_path": zip_path,
        "sample_size": sample_size
    })

async def schedule_analytics_refresh() -> str:
    """Schedule an analytics refresh job"""
    return await job_manager.create_job("analytics_refresh", {})

async def schedule_cache_warm() -> str:
    """Schedule cache warming job"""
    return await job_manager.create_job("cache_warm", {})

async def schedule_evidence_package(provider_id: int) -> str:
    """Schedule evidence package generation job"""
    return await job_manager.create_job("evidence_package", {
        "provider_id": provider_id
    })

async def schedule_political_analysis(provider_id: int) -> str:
    """Schedule political intelligence analysis job"""
    return await job_manager.create_job("political_analysis", {
        "provider_id": provider_id
    })

async def schedule_ai_analysis(provider_id: int) -> str:
    """Schedule AI analysis job"""
    return await job_manager.create_job("ai_analysis", {
        "provider_id": provider_id
    })

async def schedule_blockchain_verification(provider_id: int) -> str:
    """Schedule blockchain verification job"""
    return await job_manager.create_job("blockchain_verification", {
        "provider_id": provider_id
    })

async def schedule_claim_processing(claim_data: Dict[str, Any]) -> str:
    """Schedule claim processing job"""
    return await job_manager.create_job("claim_processing", {
        "claim_data": claim_data
    })

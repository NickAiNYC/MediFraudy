"""
Client portal for law offices - case management and client access
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import secrets

logger = logging.getLogger(__name__)

class ClientPortalManager:
    """Manage client portal access and case information"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_client_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new client case with portal access"""
        
        case_id = f"CASE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)[:8].upper()}"
        access_token = secrets.token_urlsafe(32)
        
        # Store case information (in production, this would be in a proper cases table)
        case_info = {
            "case_id": case_id,
            "access_token": access_token,
            "client_name": case_data.get("client_name"),
            "contact_email": case_data.get("contact_email"),
            "provider_id": case_data.get("provider_id"),
            "case_type": "FCA_MEDICAID_FRAUD",
            "status": "investigation",
            "created_at": datetime.utcnow().isoformat(),
            "attorney_assigned": case_data.get("attorney_id"),
            "estimated_value": case_data.get("estimated_value", 0),
            "description": case_data.get("description", "")
        }
        
        # Generate client portal link
        portal_link = f"https://medifraudy.app/portal/{case_id}?token={access_token}"
        
        return {
            "case_id": case_id,
            "access_token": access_token,
            "portal_link": portal_link,
            "case_info": case_info,
            "next_steps": [
                "Share portal link with client",
                "Client uploads supporting documents",
                "Attorney reviews case progress",
                "Evidence package generation"
            ]
        }
    
    async def get_client_case_status(self, case_id: str, access_token: str) -> Dict[str, Any]:
        """Get case status for client portal"""
        
        # Mock case data - in production, this would query a cases table
        mock_cases = {
            "CASE_20260219_120000_ABC123": {
                "case_id": "CASE_20260219_120000_ABC123",
                "status": "investigation",
                "progress": 35,
                "attorney": "Sarah Johnson, Esq.",
                "firm": "Johnson & Associates LLP",
                "last_update": datetime.utcnow().isoformat(),
                "next_milestone": "Evidence package generation",
                "estimated_completion": "2026-02-26",
                "documents": [
                    {
                        "name": "Initial Consultation Notes",
                        "uploaded": "2026-02-19",
                        "type": "attorney_notes"
                    },
                    {
                        "name": "Provider Background Check",
                        "uploaded": "2026-02-19", 
                        "type": "investigation"
                    }
                ],
                "timeline": [
                    {
                        "date": "2026-02-19",
                        "event": "Case opened",
                        "status": "completed"
                    },
                    {
                        "date": "2026-02-20",
                        "event": "Evidence package generation",
                        "status": "pending"
                    },
                    {
                        "date": "2026-02-26",
                        "event": "FCA complaint filing",
                        "status": "scheduled"
                    }
                ]
            }
        }
        
        case_info = mock_cases.get(case_id)
        
        if not case_info:
            raise ValueError("Case not found or invalid access token")
        
        return case_info
    
    async def generate_client_report(self, case_id: str) -> Dict[str, Any]:
        """Generate client-friendly progress report"""
        
        case_status = await self.get_client_case_status(case_id, "mock_token")
        
        report = {
            "case_id": case_id,
            "report_date": datetime.now().strftime("%B %d, %Y"),
            "attorney": case_status["attorney"],
            "firm": case_status["firm"],
            "status_summary": {
                "current_phase": self._get_phase_description(case_status["status"]),
                "progress_percentage": case_status["progress"],
                "estimated_completion": case_status["estimated_completion"]
            },
            "key_developments": [
                "Initial case assessment completed",
                "Provider fraud patterns identified",
                "Evidence package in preparation"
            ],
            "next_steps": [
                "Review evidence package with attorney",
                "Approve FCA complaint filing",
                "Prepare for expert testimony"
            ],
            "contact_information": {
                "attorney": case_status["attorney"],
                "firm": case_status["firm"],
                "phone": "(212) 555-0123",
                "email": "sjohnson@johnsonlaw.com"
            }
        }
        
        return report
    
    async def update_case_progress(self, case_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update case progress and notify client"""
        
        # In production, this would update the cases table
        update = {
            "case_id": case_id,
            "update_type": update_data.get("type"),
            "description": update_data.get("description"),
            "timestamp": datetime.utcnow().isoformat(),
            "updated_by": update_data.get("updated_by", "system")
        }
        
        # Send client notification (email, SMS, etc.)
        await self._notify_client_update(case_id, update)
        
        return {
            "status": "updated",
            "case_id": case_id,
            "update": update,
            "notification_sent": True
        }
    
    async def _get_phase_description(self, status: str) -> str:
        """Get human-readable phase description"""
        
        phases = {
            "investigation": "Initial Investigation & Evidence Gathering",
            "analysis": "Fraud Pattern Analysis & Damage Calculation",
            "preparation": "Complaint Preparation & Expert Review",
            "filing": "FCA Complaint Filing",
            "discovery": "Discovery Phase",
            "settlement": "Settlement Negotiations",
            "trial": "Trial Preparation & Proceedings"
        }
        
        return phases.get(status, "Unknown Phase")
    
    async def _notify_client_update(self, case_id: str, update: Dict[str, Any]):
        """Send notification to client about case update"""
        
        # In production, this would integrate with email/SMS services
        logger.info(f"📧 Client notification sent for case {case_id}: {update['description']}")
        
        # Mock notification
        notification = {
            "case_id": case_id,
            "type": "case_update",
            "message": update["description"],
            "timestamp": update["timestamp"],
            "delivery_method": "email"
        }
        
        return notification

# Singleton instance
client_portal_manager = ClientPortalManager

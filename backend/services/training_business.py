"""
Training & Certification Business Unit
Fraud investigator certification, system training, executive workshops, online courses
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import uuid
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CourseType(Enum):
    CERTIFICATION = "certification"
    TECHNICAL_TRAINING = "technical_training"
    EXECUTIVE_WORKSHOP = "executive_workshop"
    ONLINE_COURSE = "online_course"
    HANDS_ON_LAB = "hands_on_lab"
    WEBINAR = "webinar"

class CertificationLevel(Enum):
    FOUNDATION = "foundation"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class CourseStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ACTIVE = "active"
    ARCHIVED = "archived"

@dataclass
class TrainingCourse:
    id: str
    title: str
    description: str
    course_type: CourseType
    certification_level: Optional[CertificationLevel]
    duration_hours: int
    price: float
    max_participants: int
    prerequisites: List[str]
    learning_objectives: List[str]
    modules: List[Dict[str, Any]]
    assessment_criteria: Dict[str, Any]
    instructor_id: str
    materials: List[str]
    status: CourseStatus
    created_at: datetime
    updated_at: datetime

@dataclass
class Certification:
    id: str
    name: str
    description: str
    level: CertificationLevel
    requirements: List[str]
    validity_period_months: int
    renewal_requirements: List[str]
    price: float
    certified_individuals: int
    created_at: datetime

@dataclass
class TrainingSession:
    id: str
    course_id: str
    instructor_id: str
    start_date: datetime
    end_date: datetime
    participants: List[str]
    status: str
    location: str
    delivery_method: str  # online, in_person, hybrid
    materials_provided: List[str]
    assessment_results: Dict[str, Any]
    feedback_scores: Dict[str, float]
    created_at: datetime

class TrainingCourseManager:
    """Manage training courses and curriculum"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.courses = {}
        self.certifications = {}
        self.sessions = {}
        self._initialize_course_catalog()
        
    def _initialize_course_catalog(self):
        """Initialize training course catalog"""
        
        # Fraud Investigator Certification
        self.certifications["cfi"] = Certification(
            id="cfi",
            name="Certified Fraud Investigator",
            description="Professional certification for fraud investigators using AI-powered tools",
            level=CertificationLevel.INTERMEDIATE,
            requirements=[
                "3 years fraud investigation experience",
                "Complete MediFraudy training program",
                "Pass certification exam",
                "Background check"
            ],
            validity_period_months=24,
            renewal_requirements=[
                "40 hours continuing education",
                "Pass renewal exam",
                "Active practice verification"
            ],
            price=2500,
            certified_individuals=0,
            created_at=datetime.utcnow()
        )
        
        # AI Fraud Detection Specialist
        self.certifications["cafds"] = Certification(
            id="cafds",
            name="Certified AI Fraud Detection Specialist",
            description="Advanced certification for AI and machine learning in fraud detection",
            level=CertificationLevel.ADVANCED,
            requirements=[
                "5 years fraud detection experience",
                "2 years AI/ML experience",
                "Complete advanced AI training",
                "Pass practical exam",
                "Submit case study"
            ],
            validity_period_months=36,
            renewal_requirements=[
                "60 hours advanced training",
                "Pass renewal exam",
                "Submit new case study"
            ],
            price=4500,
            certified_individuals=0,
            created_at=datetime.utcnow()
        )
        
        # Create training courses
        self._create_training_courses()
    
    def _create_training_courses(self):
        """Create comprehensive training courses"""
        
        # Foundation Course
        self.courses["fraud_detection_foundation"] = TrainingCourse(
            id="fraud_detection_foundation",
            title="Fraud Detection Foundation",
            description="Introduction to fraud detection using AI and modern techniques",
            course_type=CourseType.CERTIFICATION,
            certification_level=CertificationLevel.FOUNDATION,
            duration_hours=40,
            price=3500,
            max_participants=25,
            prerequisites=["Basic understanding of fraud concepts"],
            learning_objectives=[
                "Understand fraud detection fundamentals",
                "Learn AI basics for fraud detection",
                "Identify common fraud schemes",
                "Use basic MediFraudy features"
            ],
            modules=[
                {
                    "title": "Fraud Detection Overview",
                    "duration": 8,
                    "topics": ["Fraud types", "Industry impact", "Detection methods"]
                },
                {
                    "title": "AI in Fraud Detection",
                    "duration": 12,
                    "topics": ["Machine learning basics", "Pattern recognition", "Predictive analytics"]
                },
                {
                    "title": "MediFraudy System Basics",
                    "duration": 16,
                    "topics": ["System overview", "Basic navigation", "Report interpretation"]
                },
                {
                    "title": "Practical Applications",
                    "duration": 4,
                    "topics": ["Case studies", "Hands-on exercises", "Q&A"]
                }
            ],
            assessment_criteria={
                "exam_score": 80,
                "practical_exercise": 75,
                "participation": 90
            },
            instructor_id="instructor_001",
            materials=["training_manual", "case_studies", "system_access"],
            status=CourseStatus.PUBLISHED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Advanced Technical Training
        self.courses["advanced_technical"] = TrainingCourse(
            id="advanced_technical",
            title="Advanced MediFraudy Technical Training",
            description="Deep dive into MediFraudy technical architecture and advanced features",
            course_type=CourseType.TECHNICAL_TRAINING,
            certification_level=CertificationLevel.ADVANCED,
            duration_hours=60,
            price=7500,
            max_participants=15,
            prerequisites=["Fraud Detection Foundation", "Technical background"],
            learning_objectives=[
                "Master advanced MediFraudy features",
                "Configure custom fraud detection rules",
                "Integrate with external systems",
                "Optimize system performance"
            ],
            modules=[
                {
                    "title": "System Architecture",
                    "duration": 12,
                    "topics": ["Microservices", "Database design", "API integration"]
                },
                {
                    "title": "Advanced Configuration",
                    "duration": 16,
                    "topics": ["Custom rules", "Threshold tuning", "Workflow design"]
                },
                {
                    "title": "Integration & APIs",
                    "duration": 20,
                    "topics": ["REST APIs", "Webhooks", "Data mapping"]
                },
                {
                    "title": "Performance Optimization",
                    "duration": 12,
                    "topics": ["Query optimization", "Caching", "Scaling"]
                }
            ],
            assessment_criteria={
                "lab_exercises": 85,
                "integration_project": 80,
                "performance_test": 75
            },
            instructor_id="instructor_002",
            materials=["technical_manual", "api_documentation", "lab_environment"],
            status=CourseStatus.PUBLISHED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Executive Workshop
        self.courses["executive_strategy"] = TrainingCourse(
            id="executive_strategy",
            title="Fraud Detection Strategy for Executives",
            description="Strategic workshop for C-level executives on fraud detection ROI and implementation",
            course_type=CourseType.EXECUTIVE_WORKSHOP,
            certification_level=None,
            duration_hours=16,
            price=12000,
            max_participants=20,
            prerequisites=["Executive level position"],
            learning_objectives=[
                "Understand fraud detection business impact",
                "Evaluate technology investments",
                "Develop implementation strategy",
                "Measure ROI and success metrics"
            ],
            modules=[
                {
                    "title": "Business Impact of Fraud",
                    "duration": 4,
                    "topics": ["Financial impact", "Reputation risk", "Regulatory compliance"]
                },
                {
                    "title": "Technology Evaluation",
                    "duration": 4,
                    "topics": ["ROI analysis", "Vendor selection", "Integration planning"]
                },
                {
                    "title": "Implementation Strategy",
                    "duration": 4,
                    "topics": ["Change management", "Stakeholder alignment", "Phased rollout"]
                },
                {
                    "title": "Success Metrics",
                    "duration": 4,
                    "topics": ["KPI development", "Performance tracking", "Continuous improvement"]
                }
            ],
            assessment_criteria={
                "strategy_document": 90,
                "participation": 85,
                "case_presentation": 80
            },
            instructor_id="instructor_003",
            materials=["executive_briefing", "roi_calculator", "implementation_guide"],
            status=CourseStatus.PUBLISHED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Online Course
        self.courses["online_fraud_basics"] = TrainingCourse(
            id="online_fraud_basics",
            title="Fraud Detection Basics - Online",
            description="Self-paced online course covering fraud detection fundamentals",
            course_type=CourseType.ONLINE_COURSE,
            certification_level=CertificationLevel.FOUNDATION,
            duration_hours=20,
            price=995,
            max_participants=1000,
            prerequisites=[],
            learning_objectives=[
                "Basic fraud awareness",
                "Identify red flags",
                "Report suspicious activity",
                "Understand detection technology"
            ],
            modules=[
                {
                    "title": "Introduction to Fraud",
                    "duration": 5,
                    "topics": ["What is fraud", "Types of fraud", "Impact on organizations"]
                },
                {
                    "title": "Red Flags and Indicators",
                    "duration": 5,
                    "topics": ["Common red flags", "Behavioral indicators", "Document anomalies"]
                },
                {
                    "title": "Reporting and Prevention",
                    "duration": 5,
                    "topics": ["Reporting procedures", "Prevention strategies", "Whistleblowing"]
                },
                {
                    "title": "Technology in Fraud Detection",
                    "duration": 5,
                    "topics": ["AI basics", "Data analytics", "System overview"]
                }
            ],
            assessment_criteria={
                "quiz_scores": 80,
                "final_exam": 75
            },
            instructor_id="auto_instructor",
            materials=["video_lectures", "reading_materials", "quizzes"],
            status=CourseStatus.PUBLISHED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def create_training_session(self, course_id: str, 
                                     session_data: Dict[str, Any]) -> TrainingSession:
        """Create new training session"""
        if course_id not in self.courses:
            raise ValueError(f"Course {course_id} not found")
        
        course = self.courses[course_id]
        session_id = str(uuid.uuid4())
        
        session = TrainingSession(
            id=session_id,
            course_id=course_id,
            instructor_id=session_data.get("instructor_id", course.instructor_id),
            start_date=datetime.fromisoformat(session_data["start_date"]),
            end_date=datetime.fromisoformat(session_data["end_date"]),
            participants=session_data.get("participants", []),
            status="scheduled",
            location=session_data.get("location", "Online"),
            delivery_method=session_data.get("delivery_method", "online"),
            materials_provided=course.materials,
            assessment_results={},
            feedback_scores={},
            created_at=datetime.utcnow()
        )
        
        # Store in database
        await self.db.execute(text("""
            INSERT INTO training_sessions (
                id, course_id, instructor_id, start_date, end_date, participants,
                status, location, delivery_method, materials_provided,
                assessment_results, feedback_scores, created_at
            ) VALUES (
                :id, :course_id, :instructor_id, :start_date, :end_date, :participants,
                :status, :location, :delivery_method, :materials_provided,
                :assessment_results, :feedback_scores, :created_at
            )
        """), {
            "id": session.id,
            "course_id": session.course_id,
            "instructor_id": session.instructor_id,
            "start_date": session.start_date,
            "end_date": session.end_date,
            "participants": json.dumps(session.participants),
            "status": session.status,
            "location": session.location,
            "delivery_method": session.delivery_method,
            "materials_provided": json.dumps(session.materials_provided),
            "assessment_results": json.dumps(session.assessment_results),
            "feedback_scores": json.dumps(session.feedback_scores),
            "created_at": session.created_at
        })
        
        await self.db.commit()
        
        self.sessions[session_id] = session
        return session
    
    async def enroll_participant(self, session_id: str, participant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enroll participant in training session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        course = self.courses[session.course_id]
        
        # Check capacity
        if len(session.participants) >= course.max_participants:
            raise ValueError("Session is full")
        
        # Add participant
        participant_id = str(uuid.uuid4())
        enrollment = {
            "participant_id": participant_id,
            "participant_data": participant_data,
            "enrollment_date": datetime.utcnow(),
            "status": "enrolled",
            "payment_status": "pending"
        }
        
        session.participants.append(participant_id)
        
        # Update database
        await self.db.execute(text("""
            UPDATE training_sessions 
            SET participants = :participants 
            WHERE id = :session_id
        """), {
            "session_id": session_id,
            "participants": json.dumps(session.participants)
        })
        
        await self.db.commit()
        
        return enrollment
    
    async def generate_certificate(self, participant_id: str, 
                                 course_id: str, 
                                 assessment_results: Dict[str, float]) -> Dict[str, Any]:
        """Generate training certificate"""
        
        certificate = {
            "certificate_id": str(uuid.uuid4()),
            "participant_id": participant_id,
            "course_id": course_id,
            "course_title": self.courses[course_id].title,
            "completion_date": datetime.utcnow(),
            "assessment_results": assessment_results,
            "overall_score": sum(assessment_results.values()) / len(assessment_results),
            "certificate_hash": hashlib.sha256(
                f"{participant_id}{course_id}{datetime.utcnow()}".encode()
            ).hexdigest(),
            "verification_url": f"https://medifraudy.com/verify/{participant_id}"
        }
        
        # Store certificate
        await self.db.execute(text("""
            INSERT INTO training_certificates (
                certificate_id, participant_id, course_id, completion_date,
                assessment_results, overall_score, certificate_hash, verification_url
            ) VALUES (
                :certificate_id, :participant_id, :course_id, :completion_date,
                :assessment_results, :overall_score, :certificate_hash, :verification_url
            )
        """), certificate)
        
        await self.db.commit()
        
        return certificate

class CertificationManager:
    """Manage professional certifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.certified_individuals = {}
        
    async def issue_certification(self, participant_id: str, 
                                certification_id: str,
                                evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Issue professional certification"""
        
        certification_record = {
            "certification_id": str(uuid.uuid4()),
            "participant_id": participant_id,
            "certification_type": certification_id,
            "issue_date": datetime.utcnow(),
            "expiry_date": datetime.utcnow() + timedelta(days=730),  # 2 years
            "evidence": evidence,
            "status": "active",
            "verification_code": str(uuid.uuid4())[:8].upper()
        }
        
        # Store certification
        await self.db.execute(text("""
            INSERT INTO professional_certifications (
                certification_id, participant_id, certification_type, issue_date,
                expiry_date, evidence, status, verification_code
            ) VALUES (
                :certification_id, :participant_id, :certification_type, :issue_date,
                :expiry_date, :evidence, :status, :verification_code
            )
        """), certification_record)
        
        await self.db.commit()
        
        return certification_record
    
    async def verify_certification(self, verification_code: str) -> Optional[Dict[str, Any]]:
        """Verify certification status"""
        
        result = await self.db.execute(text("""
            SELECT * FROM professional_certifications 
            WHERE verification_code = :verification_code AND status = 'active'
        """), {"verification_code": verification_code})
        
        certification = result.fetchone()
        
        if certification:
            return {
                "valid": True,
                "certification_type": certification.certification_type,
                "issue_date": certification.issue_date.isoformat(),
                "expiry_date": certification.expiry_date.isoformat(),
                "status": certification.status
            }
        
        return {"valid": False}
    
    async def renew_certification(self, certification_id: str, 
                                 renewal_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Renew professional certification"""
        
        # Update certification
        new_expiry = datetime.utcnow() + timedelta(days=1095)  # 3 years
        
        await self.db.execute(text("""
            UPDATE professional_certifications 
            SET expiry_date = :expiry_date, 
                renewal_evidence = :renewal_evidence,
                updated_at = :updated_at
            WHERE certification_id = :certification_id
        """), {
            "certification_id": certification_id,
            "expiry_date": new_expiry,
            "renewal_evidence": json.dumps(renewal_evidence),
            "updated_at": datetime.utcnow()
        })
        
        await self.db.commit()
        
        return {
            "certification_id": certification_id,
            "new_expiry_date": new_expiry.isoformat(),
            "status": "renewed"
        }

class TrainingBusinessManager:
    """Main training business unit manager"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.course_manager = TrainingCourseManager(db)
        self.certification_manager = CertificationManager(db)
        self.instructors = self._initialize_instructors()
        
    def _initialize_instructors(self) -> Dict[str, Dict[str, Any]]:
        """Initialize instructor database"""
        return {
            "instructor_001": {
                "name": "Dr. Sarah Johnson",
                "title": "Senior Fraud Detection Expert",
                "specialties": ["Healthcare fraud", "AI applications", "Investigation techniques"],
                "experience_years": 15,
                "certifications": ["CFE", "CAMS", "CAFD"],
                "rating": 4.8,
                "hourly_rate": 500
            },
            "instructor_002": {
                "name": "Michael Chen",
                "title": "Technical Architect",
                "specialties": ["System integration", "API development", "Performance optimization"],
                "experience_years": 12,
                "certifications": ["AWS", "Azure", "GCP"],
                "rating": 4.9,
                "hourly_rate": 600
            },
            "instructor_003": {
                "name": "Lisa Rodriguez",
                "title": "Executive Strategy Consultant",
                "specialties": ["Business strategy", "ROI analysis", "Change management"],
                "experience_years": 20,
                "certifications": ["MBA", "PMP", "CAFD"],
                "rating": 4.7,
                "hourly_rate": 800
            }
        }
    
    async def get_business_metrics(self) -> Dict[str, Any]:
        """Get training business metrics"""
        
        # Calculate total revenue
        total_revenue = 0
        total_participants = 0
        courses_offered = len(self.course_manager.courses)
        certifications_issued = 0
        
        # Get session data from database
        result = await self.db.execute(text("""
            SELECT COUNT(*) as total_sessions,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions
            FROM training_sessions
        """))
        session_stats = result.fetchone()
        
        # Get participant data
        result = await self.db.execute(text("""
            SELECT COUNT(DISTINCT participant_id) as total_participants
            FROM training_sessions
            WHERE JSON_VALID(participants)
        """))
        participant_stats = result.fetchone()
        
        # Get certification data
        result = await self.db.execute(text("""
            SELECT COUNT(*) as total_certifications
            FROM professional_certifications
            WHERE status = 'active'
        """))
        cert_stats = result.fetchone()
        
        return {
            "total_revenue": total_revenue,
            "total_participants": participant_stats.total_participants or 0,
            "courses_offered": courses_offered,
            "certifications_issued": cert_stats.total_certifications or 0,
            "total_sessions": session_stats.total_sessions or 0,
            "completed_sessions": session_stats.completed_sessions or 0,
            "completion_rate": (session_stats.completed_sessions / max(session_stats.total_sessions, 1)) * 100,
            "top_courses": self._get_top_courses(),
            "revenue_by_course_type": self._calculate_revenue_by_type(),
            "instructor_utilization": self._calculate_instructor_utilization()
        }
    
    def _get_top_courses(self) -> List[Dict[str, Any]]:
        """Get top performing courses"""
        # Mock implementation - would query actual data
        return [
            {
                "course_id": "fraud_detection_foundation",
                "title": "Fraud Detection Foundation",
                "participants": 125,
                "revenue": 437500,
                "satisfaction_score": 4.7
            },
            {
                "course_id": "executive_strategy",
                "title": "Executive Strategy Workshop",
                "participants": 45,
                "revenue": 540000,
                "satisfaction_score": 4.9
            }
        ]
    
    def _calculate_revenue_by_type(self) -> Dict[str, float]:
        """Calculate revenue by course type"""
        revenue_by_type = {}
        
        for course in self.course_manager.courses.values():
            course_type = course.course_type.value
            revenue_by_type[course_type] = revenue_by_type.get(course_type, 0) + course.price
        
        return revenue_by_type
    
    def _calculate_instructor_utilization(self) -> Dict[str, Any]:
        """Calculate instructor utilization rates"""
        utilization = {}
        
        for instructor_id, instructor in self.instructors.items():
            # Mock calculation - would query actual session data
            utilization[instructor_id] = {
                "name": instructor["name"],
                "utilization_rate": 0.75,
                "sessions_taught": 12,
                "average_rating": instructor["rating"]
            }
        
        return utilization
    
    async def generate_training_catalog(self) -> Dict[str, Any]:
        """Generate comprehensive training catalog"""
        
        catalog = {
            "catalog_date": datetime.utcnow().isoformat(),
            "courses": [],
            "certifications": [],
            "instructors": [],
            "pricing_tiers": self._get_pricing_tiers(),
            "upcoming_sessions": await self._get_upcoming_sessions(),
            "special_offers": self._get_special_offers()
        }
        
        # Add courses
        for course in self.course_manager.courses.values():
            catalog["courses"].append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "type": course.course_type.value,
                "level": course.certification_level.value if course.certification_level else None,
                "duration": course.duration_hours,
                "price": course.price,
                "max_participants": course.max_participants,
                "prerequisites": course.prerequisites,
                "learning_objectives": course.learning_objectives
            })
        
        # Add certifications
        for cert in self.course_manager.certifications.values():
            catalog["certifications"].append({
                "id": cert.id,
                "name": cert.name,
                "description": cert.description,
                "level": cert.level.value,
                "requirements": cert.requirements,
                "validity_period": cert.validity_period_months,
                "price": cert.price
            })
        
        # Add instructors
        for instructor_id, instructor in self.instructors.items():
            catalog["instructors"].append({
                "id": instructor_id,
                "name": instructor["name"],
                "title": instructor["title"],
                "specialties": instructor["specialties"],
                "experience": instructor["experience_years"],
                "rating": instructor["rating"]
            })
        
        return catalog
    
    def _get_pricing_tiers(self) -> Dict[str, Any]:
        """Get pricing tiers for different customer segments"""
        return {
            "enterprise": {
                "discount_percentage": 15,
                "min_purchase": 5,
                "benefits": ["Priority scheduling", "Custom content", "Dedicated support"]
            },
            "mid_market": {
                "discount_percentage": 10,
                "min_purchase": 3,
                "benefits": ["Flexible scheduling", "Standard customization"]
            },
            "small_business": {
                "discount_percentage": 5,
                "min_purchase": 1,
                "benefits": ["Standard courses", "Group discounts"]
            }
        }
    
    async def _get_upcoming_sessions(self) -> List[Dict[str, Any]]:
        """Get upcoming training sessions"""
        # Mock implementation - would query actual database
        return [
            {
                "session_id": "session_001",
                "course_title": "Fraud Detection Foundation",
                "start_date": "2026-03-01T09:00:00",
                "end_date": "2026-03-05T17:00:00",
                "instructor": "Dr. Sarah Johnson",
                "available_spots": 8,
                "location": "New York, NY"
            },
            {
                "session_id": "session_002",
                "course_title": "Executive Strategy Workshop",
                "start_date": "2026-03-15T09:00:00",
                "end_date": "2026-03-16T17:00:00",
                "instructor": "Lisa Rodriguez",
                "available_spots": 12,
                "location": "Virtual"
            }
        ]
    
    def _get_special_offers(self) -> List[Dict[str, Any]]:
        """Get current special offers"""
        return [
            {
                "title": "Early Bird Discount",
                "description": "20% off courses booked 30 days in advance",
                "valid_until": "2026-04-01",
                "discount_code": "EARLYBIRD20"
            },
            {
                "title": "Group Training Package",
                "description": "Buy 4 seats, get 1 free",
                "valid_until": "2026-03-31",
                "discount_code": "GROUP5FOR4"
            }
        ]

# Singleton instance
training_business_manager = TrainingBusinessManager

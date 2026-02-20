"""
Professional Services Business Unit
Implementation services, custom development, optimization consulting, integration services
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

class ServiceType(Enum):
    IMPLEMENTATION = "implementation"
    CUSTOM_DEVELOPMENT = "custom_development"
    OPTIMIZATION_CONSULTING = "optimization_consulting"
    INTEGRATION_SERVICES = "integration_services"
    MIGRATION_SERVICES = "migration_services"
    SUPPORT_CONTRACTS = "support_contracts"
    TRAINING_SERVICES = "training_services"
    AUDIT_SERVICES = "audit_services"

class ProjectStatus(Enum):
    PROSPECT = "prospect"
    SCOPING = "scoping"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DEPLOYED = "deployed"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class ServiceTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    ENTERPRISE = "enterprise"

@dataclass
class ProfessionalService:
    id: str
    name: str
    description: str
    service_type: ServiceType
    tier: ServiceTier
    base_price: float
    estimated_duration_days: int
    required_resources: List[str]
    deliverables: List[str]
    success_criteria: List[str]
    prerequisites: List[str]
    optional_addons: List[Dict[str, Any]]
    created_at: datetime

@dataclass
class ServiceProject:
    id: str
    client_id: str
    service_id: str
    project_name: str
    status: ProjectStatus
    start_date: datetime
    end_date: Optional[datetime]
    project_manager: str
    team_members: List[str]
    budget: float
        actual_cost: float
    milestones: List[Dict[str, Any]]
    deliverables: List[Dict[str, Any]]
    risks: List[Dict[str, Any]]
    progress_percentage: float
    client_satisfaction: float
    created_at: datetime
    updated_at: datetime

@dataclass
class ServiceTeam:
    id: str
    name: str
    specialization: str
    members: List[Dict[str, Any]]
    skills: List[str]
    availability: Dict[str, float]  # skill_id -> availability_percentage
    hourly_rate: float
    utilization_rate: float
    current_projects: List[str]

class ProfessionalServicesManager:
    """Manage professional services operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.services = {}
        self.projects = {}
        self.teams = {}
        self._initialize_services()
        self._initialize_teams()
        
    def _initialize_services(self):
        """Initialize professional services catalog"""
        
        # Implementation Service
        self.services["standard_implementation"] = ProfessionalService(
            id="standard_implementation",
            name="Standard MediFraudy Implementation",
            description="Complete implementation of MediFraudy system with standard configuration",
            service_type=ServiceType.IMPLEMENTATION,
            tier=ServiceTier.SILVER,
            base_price=75000,
            estimated_duration_days=60,
            required_resources=["project_manager", "technical_lead", "data_engineer", "2_developers"],
            deliverables=[
                "Configured MediFraudy system",
                "Data migration completed",
                "Staff training completed",
                "Go-live support",
                "Documentation package"
            ],
            success_criteria=[
                "System processes test data successfully",
                "All integrations working",
                "Staff trained and certified",
                "Client sign-off received"
            ],
            prerequisites=[
                "Infrastructure ready",
                "Data sources identified",
                "Stakeholder commitment",
                "Project budget approved"
            ],
            optional_addons=[
                {"name": "Advanced AI Configuration", "price": 25000},
                {"name": "Custom Dashboard Development", "price": 15000},
                {"name": "Extended Support (6 months)", "price": 30000}
            ],
            created_at=datetime.utcnow()
        )
        
        # Enterprise Implementation
        self.services["enterprise_implementation"] = ProfessionalService(
            id="enterprise_implementation",
            name="Enterprise Implementation",
            description="Full-scale enterprise implementation with custom configurations",
            service_type=ServiceType.IMPLEMENTATION,
            tier=ServiceTier.PLATINUM,
            base_price=250000,
            estimated_duration_days=120,
            required_resources=["program_manager", "architect", "2_technical_leads", "4_developers", "2_data_engineers"],
            deliverables=[
                "Custom-configured MediFraudy system",
                "Multi-site deployment",
                "Advanced integrations",
                "Custom reporting",
                "Comprehensive training",
                "Change management support"
            ],
            success_criteria=[
                "All sites operational",
                "Custom workflows working",
                "Performance targets met",
                "User adoption > 80%",
                "ROI targets achieved"
            ],
            prerequisites=[
                "Executive sponsorship",
                "Dedicated project team",
                "Comprehensive requirements",
                "Infrastructure capacity"
            ],
            optional_addons=[
                {"name": "Global Deployment", "price": 100000},
                {"name": "Advanced Analytics Package", "price": 75000},
                {"name": "24/7 Support (1 year)", "price": 150000}
            ],
            created_at=datetime.utcnow()
        )
        
        # Custom Development
        self.services["custom_development"] = ProfessionalService(
            id="custom_development",
            name="Custom Feature Development",
            description="Development of custom features and integrations",
            service_type=ServiceType.CUSTOM_DEVELOPMENT,
            tier=ServiceTier.GOLD,
            base_price=50000,
            estimated_duration_days=45,
            required_resources=["solution_architect", "2_developers", "qa_engineer"],
            deliverables=[
                "Custom feature specification",
                "Developed and tested feature",
                "Integration documentation",
                "User training materials",
                "Maintenance guide"
            ],
            success_criteria=[
                "Feature meets requirements",
                "Integration successful",
                "Performance acceptable",
                "Client approval received"
            ],
            prerequisites=[
                "Detailed requirements",
                "Technical specifications",
                "Development environment",
                "Testing data"
            ],
            optional_addons=[
                {"name": "Mobile App Development", "price": 75000},
                {"name": "Advanced Analytics Module", "price": 40000},
                {"name": "API Development", "price": 30000}
            ],
            created_at=datetime.utcnow()
        )
        
        # Optimization Consulting
        self.services["optimization_consulting"] = ProfessionalService(
            id="optimization_consulting",
            name="System Optimization Consulting",
            description="Comprehensive system optimization and performance tuning",
            service_type=ServiceType.OPTIMIZATION_CONSULTING,
            tier=ServiceTier.GOLD,
            base_price=35000,
            estimated_duration_days=30,
            required_resources=["optimization_expert", "performance_engineer", "data_analyst"],
            deliverables=[
                "Performance assessment report",
                "Optimization recommendations",
                "Implemented improvements",
                "Performance benchmarks",
                "Monitoring setup"
            ],
            success_criteria=[
                "Performance improvement > 30%",
                "Processing time reduction",
                "Resource utilization optimized",
                "Client satisfaction > 90%"
            ],
            prerequisites=[
                "System operational for 3+ months",
                "Performance data available",
                "Access to system metrics",
                "Stakeholder cooperation"
            ],
            optional_addons=[
                {"name": "Advanced Analytics Setup", "price": 20000},
                {"name": "Continuous Monitoring", "price": 15000},
                {"name": "Staff Training", "price": 10000}
            ],
            created_at=datetime.utcnow()
        )
        
        # Integration Services
        self.services["integration_services"] = ProfessionalService(
            id="integration_services",
            name="System Integration Services",
            description="Integration with external systems and third-party applications",
            service_type=ServiceType.INTEGRATION_SERVICES,
            tier=ServiceTier.SILVER,
            base_price=40000,
            estimated_duration_days=35,
            required_resources=["integration_specialist", "2_developers", "qa_engineer"],
            deliverables=[
                "Integration design document",
                "Developed integrations",
                "Tested interfaces",
                "Error handling procedures",
                "Monitoring setup"
            ],
            success_criteria=[
                "All integrations functional",
                "Data flow successful",
                "Error handling working",
                "Performance acceptable"
            ],
            prerequisites=[
                "API documentation available",
                "Test environment ready",
                "Security clearance",
                "Data mapping completed"
            ],
            optional_addons=[
                {"name": "Real-time Integration", "price": 15000},
                {"name": "Advanced Error Handling", "price": 10000},
                {"name": "Custom API Development", "price": 25000}
            ],
            created_at=datetime.utcnow()
        )
        
        # Support Contracts
        self.services["premium_support"] = ProfessionalService(
            id="premium_support",
            name="Premium Support Contract",
            description="Comprehensive support and maintenance services",
            service_type=ServiceType.SUPPORT_CONTRACTS,
            tier=ServiceTier.PLATINUM,
            base_price=60000,  # Annual
            estimated_duration_days=365,
            required_resources=["support_manager", "2_support_engineers", "1_specialist"],
            deliverables=[
                "24/7 support availability",
                "Proactive monitoring",
                "Regular maintenance",
                "Performance optimization",
                "Emergency response",
                "Quarterly reviews"
            ],
            success_criteria=[
                "Response time < 1 hour",
                "Resolution time < 4 hours",
                "System uptime > 99.9%",
                "Customer satisfaction > 95%"
            ],
            prerequisites=[
                "System operational",
                "Support infrastructure",
                "Service level agreement",
                "Emergency contacts"
            ],
            optional_addons=[
                {"name": "On-site Support", "price": 25000},
                {"name": "Dedicated Specialist", "price": 40000},
                {"name": "Training Updates", "price": 15000}
            ],
            created_at=datetime.utcnow()
        )
    
    def _initialize_teams(self):
        """Initialize professional services teams"""
        
        # Implementation Team
        self.teams["implementation_team"] = ServiceTeam(
            id="implementation_team",
            name="Elite Implementation Team",
            specialization="System Implementation",
            members=[
                {
                    "id": "pm_001",
                    "name": "Alex Thompson",
                    "role": "Project Manager",
                    "experience_years": 12,
                    "certifications": ["PMP", "CSM", "CAFD"]
                },
                {
                    "id": "tl_001",
                    "name": "Dr. Emily Chen",
                    "role": "Technical Lead",
                    "experience_years": 10,
                    "certifications": ["AWS", "Azure", "GCP", "CAFD"]
                },
                {
                    "id": "dev_001",
                    "name": "Michael Rodriguez",
                    "role": "Senior Developer",
                    "experience_years": 8,
                    "certifications": ["AWS", "Python", "React"]
                },
                {
                    "id": "de_001",
                    "name": "Sarah Kim",
                    "role": "Data Engineer",
                    "experience_years": 7,
                    "certifications": ["AWS", "Snowflake", "Python"]
                }
            ],
            skills=["project_management", "system_architecture", "python", "sql", "cloud_platforms", "data_migration"],
            availability={"project_management": 0.8, "system_architecture": 0.7, "python": 0.6, "sql": 0.8},
            hourly_rate=200,
            utilization_rate=0.75,
            current_projects=[]
        )
        
        # Custom Development Team
        self.teams["development_team"] = ServiceTeam(
            id="development_team",
            name="Custom Development Team",
            specialization="Custom Software Development",
            members=[
                {
                    "id": "arch_001",
                    "name": "David Park",
                    "role": "Solution Architect",
                    "experience_years": 15,
                    "certifications": ["TOGAF", "AWS", "Azure"]
                },
                {
                    "id": "dev_002",
                    "name": "Jennifer Liu",
                    "role": "Full Stack Developer",
                    "experience_years": 9,
                    "certifications": ["React", "Node.js", "Python"]
                },
                {
                    "id": "dev_003",
                    "name": "Robert Wilson",
                    "role": "Backend Developer",
                    "experience_years": 8,
                    "certifications": ["Python", "Java", "AWS"]
                }
            ],
            skills=["solution_architecture", "full_stack_development", "backend_development", "api_design", "database_design"],
            availability={"solution_architecture": 0.6, "full_stack_development": 0.7, "backend_development": 0.8},
            hourly_rate=225,
            utilization_rate=0.82,
            current_projects=[]
        )
        
        # Optimization Team
        self.teams["optimization_team"] = ServiceTeam(
            id="optimization_team",
            name="Performance Optimization Team",
            specialization="System Optimization",
            members=[
                {
                    "id": "opt_001",
                    "name": "Dr. Lisa Anderson",
                    "role": "Optimization Expert",
                    "experience_years": 14,
                    "certifications": ["CAFD", "AWS", "Performance_Tuning"]
                },
                {
                    "id": "perf_001",
                    "name": "James Taylor",
                    "role": "Performance Engineer",
                    "experience_years": 10,
                    "certifications": ["Linux", "Docker", "Kubernetes"]
                }
            ],
            skills=["performance_optimization", "database_tuning", "system_monitoring", "capacity_planning"],
            availability={"performance_optimization": 0.7, "database_tuning": 0.8, "system_monitoring": 0.9},
            hourly_rate=250,
            utilization_rate=0.70,
            current_projects=[]
        )
    
    async def create_service_project(self, client_id: str, 
                                     service_id: str,
                                     project_data: Dict[str, Any]) -> ServiceProject:
        """Create new professional services project"""
        
        if service_id not in self.services:
            raise ValueError(f"Service {service_id} not found")
        
        service = self.services[service_id]
        project_id = str(uuid.uuid4())
        
        project = ServiceProject(
            id=project_id,
            client_id=client_id,
            service_id=service_id,
            project_name=project_data.get("project_name", f"{service.name} - {client_id}"),
            status=ProjectStatus.PROSPECT,
            start_date=datetime.fromisoformat(project_data["start_date"]),
            end_date=datetime.fromisoformat(project_data["end_date"]) if "end_date" in project_data else None,
            project_manager=project_data.get("project_manager", "pm_001"),
            team_members=service.required_resources,
            budget=project_data.get("budget", service.base_price * 1.2),
            actual_cost=0,
            milestones=[],
            deliverables=[],
            risks=[],
            progress_percentage=0,
            client_satisfaction=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create initial milestones
        project.milestones = self._create_project_milestones(service, project)
        
        # Store in database
        await self.db.execute(text("""
            INSERT INTO service_projects (
                id, client_id, service_id, project_name, status, start_date, end_date,
                project_manager, team_members, budget, actual_cost, milestones,
                deliverables, risks, progress_percentage, client_satisfaction,
                created_at, updated_at
            ) VALUES (
                :id, :client_id, :service_id, :project_name, :status, :start_date, :end_date,
                :project_manager, :team_members, :budget, :actual_cost, :milestones,
                :deliverables, :risks, :progress_percentage, :client_satisfaction,
                :created_at, :updated_at
            )
        """), {
            "id": project.id,
            "client_id": project.client_id,
            "service_id": project.service_id,
            "project_name": project.project_name,
            "status": project.status.value,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "project_manager": project.project_manager,
            "team_members": json.dumps(project.team_members),
            "budget": project.budget,
            "actual_cost": project.actual_cost,
            "milestones": json.dumps(project.milestones),
            "deliverables": json.dumps(project.deliverables),
            "risks": json.dumps(project.risks),
            "progress_percentage": project.progress_percentage,
            "client_satisfaction": project.client_satisfaction,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        })
        
        await self.db.commit()
        
        self.projects[project_id] = project
        return project
    
    def _create_project_milestones(self, service: ProfessionalService, project: ServiceProject) -> List[Dict[str, Any]]:
        """Create project milestones based on service type"""
        milestones = []
        
        if service.service_type == ServiceType.IMPLEMENTATION:
            milestones = [
                {
                    "id": "kickoff",
                    "name": "Project Kickoff",
                    "target_date": project.start_date + timedelta(days=5),
                    "status": "pending",
                    "deliverables": ["Project plan", "Team assignments", "Communication plan"]
                },
                {
                    "id": "requirements",
                    "name": "Requirements Finalization",
                    "target_date": project.start_date + timedelta(days=15),
                    "status": "pending",
                    "deliverables": ["Detailed requirements", "Technical specifications", "Data mapping"]
                },
                {
                    "id": "development",
                    "name": "System Configuration",
                    "target_date": project.start_date + timedelta(days=35),
                    "status": "pending",
                    "deliverables": ["Configured system", "Initial data load", "Basic testing"]
                },
                {
                    "id": "testing",
                    "name": "User Acceptance Testing",
                    "target_date": project.start_date + timedelta(days=50),
                    "status": "pending",
                    "deliverables": ["Test results", "Bug fixes", "Performance validation"]
                },
                {
                    "id": "deployment",
                    "name": "Go-Live",
                    "target_date": project.start_date + timedelta(days=60),
                    "status": "pending",
                    "deliverables": ["Production deployment", "User training", "Support handover"]
                }
            ]
        elif service.service_type == ServiceType.CUSTOM_DEVELOPMENT:
            milestones = [
                {
                    "id": "design",
                    "name": "Solution Design",
                    "target_date": project.start_date + timedelta(days=10),
                    "status": "pending",
                    "deliverables": ["Design document", "Technical specifications"]
                },
                {
                    "id": "development",
                    "name": "Feature Development",
                    "target_date": project.start_date + timedelta(days=30),
                    "status": "pending",
                    "deliverables": ["Developed feature", "Unit tests", "Documentation"]
                },
                {
                    "id": "integration",
                    "name": "Integration & Testing",
                    "target_date": project.start_date + timedelta(days=40),
                    "status": "pending",
                    "deliverables": ["Integrated feature", "Test results", "Performance report"]
                },
                {
                    "id": "delivery",
                    "name": "Feature Delivery",
                    "target_date": project.start_date + timedelta(days=45),
                    "status": "pending",
                    "deliverables": ["Production feature", "User training", "Support documentation"]
                }
            ]
        
        return milestones
    
    async def update_project_status(self, project_id: str, 
                                   new_status: ProjectStatus,
                                   progress_data: Dict[str, Any]) -> ServiceProject:
        """Update project status and progress"""
        
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        project.status = new_status
        project.updated_at = datetime.utcnow()
        
        # Update progress
        if "progress_percentage" in progress_data:
            project.progress_percentage = progress_data["progress_percentage"]
        
        if "actual_cost" in progress_data:
            project.actual_cost = progress_data["actual_cost"]
        
        if "client_satisfaction" in progress_data:
            project.client_satisfaction = progress_data["client_satisfaction"]
        
        # Update milestones if provided
        if "milestones" in progress_data:
            project.milestones = progress_data["milestones"]
        
        # Update database
        await self.db.execute(text("""
            UPDATE service_projects 
            SET status = :status, progress_percentage = :progress, actual_cost = :actual_cost,
                client_satisfaction = :satisfaction, milestones = :milestones, updated_at = :updated_at
            WHERE id = :project_id
        """), {
            "project_id": project_id,
            "status": new_status.value,
            "progress": project.progress_percentage,
            "actual_cost": project.actual_cost,
            "satisfaction": project.client_satisfaction,
            "milestones": json.dumps(project.milestones),
            "updated_at": project.updated_at
        })
        
        await self.db.commit()
        
        return project
    
    async def generate_service_quote(self, client_id: str, 
                                   service_id: str,
                                   requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed service quote"""
        
        if service_id not in self.services:
            raise ValueError(f"Service {service_id} not found")
        
        service = self.services[service_id]
        
        # Calculate base pricing
        base_price = service.base_price
        
        # Adjust for complexity
        complexity_multiplier = self._calculate_complexity_multiplier(requirements)
        adjusted_price = base_price * complexity_multiplier
        
        # Add optional addons
        selected_addons = requirements.get("addons", [])
        addon_cost = sum(addon["price"] for addon in service.optional_addons 
                         if addon["name"] in selected_addons)
        
        # Calculate total
        total_price = adjusted_price + addon_cost
        
        # Generate quote
        quote = {
            "quote_id": str(uuid.uuid4()),
            "client_id": client_id,
            "service_id": service_id,
            "service_name": service.name,
            "quote_date": datetime.utcnow().isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "pricing": {
                "base_price": base_price,
                "complexity_multiplier": complexity_multiplier,
                "adjusted_price": adjusted_price,
                "addon_cost": addon_cost,
                "total_price": total_price
            },
            "scope": {
                "deliverables": service.deliverables,
                "success_criteria": service.success_criteria,
                "estimated_duration": service.estimated_duration_days,
                "required_resources": service.required_resources
            },
            "addons": [
                addon for addon in service.optional_addons
                if addon["name"] in selected_addons
            ],
            "terms": {
                "payment_schedule": "50% upfront, 50% on completion",
                "payment_terms": "Net 30",
                "cancellation_policy": "30 days notice",
                "warranty": "90 days post-delivery"
            }
        }
        
        return quote
    
    def _calculate_complexity_multiplier(self, requirements: Dict[str, Any]) -> float:
        """Calculate complexity multiplier based on requirements"""
        base_multiplier = 1.0
        
        # Adjust for data volume
        data_volume = requirements.get("data_volume", "medium")
        if data_volume == "large":
            base_multiplier += 0.3
        elif data_volume == "enterprise":
            base_multiplier += 0.5
        
        # Adjust for integration complexity
        integration_complexity = requirements.get("integration_complexity", "medium")
        if integration_complexity == "high":
            base_multiplier += 0.2
        elif integration_complexity == "enterprise":
            base_multiplier += 0.4
        
        # Adjust for customization level
        customization = requirements.get("customization", "standard")
        if customization == "extensive":
            base_multiplier += 0.3
        elif customization == "complete":
            base_multiplier += 0.5
        
        # Adjust for geographic scope
        geographic_scope = requirements.get("geographic_scope", "single")
        if geographic_scope == "multi_site":
            base_multiplier += 0.2
        elif geographic_scope == "global":
            base_multiplier += 0.4
        
        return min(base_multiplier, 2.5)  # Cap at 2.5x base price
    
    async def get_team_utilization(self) -> Dict[str, Any]:
        """Get team utilization metrics"""
        
        utilization_report = {
            "overall_utilization": 0.0,
            "team_utilization": {},
            "skill_utilization": {},
            "capacity_analysis": {},
            "recommendations": []
        }
        
        total_utilization = 0
        team_count = len(self.teams)
        
        for team_id, team in self.teams.items():
            team_utilization = {
                "team_name": team.name,
                "specialization": team.specialization,
                "utilization_rate": team.utilization_rate,
                "current_projects": len(team.current_projects),
                "available_capacity": (1 - team.utilization_rate) * 100,
                "hourly_rate": team.hourly_rate,
                "members": len(team.members)
            }
            
            utilization_report["team_utilization"][team_id] = team_utilization
            total_utilization += team.utilization_rate
        
        utilization_report["overall_utilization"] = total_utilization / team_count if team_count > 0 else 0
        
        # Generate recommendations
        if utilization_report["overall_utilization"] > 0.85:
            utilization_report["recommendations"].append("Consider expanding team capacity")
        elif utilization_report["overall_utilization"] < 0.6:
            utilization_report["recommendations"].append("Focus on sales to increase utilization")
        
        return utilization_report
    
    async def get_business_metrics(self) -> Dict[str, Any]:
        """Get professional services business metrics"""
        
        # Calculate total revenue
        total_revenue = 0
        active_projects = 0
        completed_projects = 0
        
        for project in self.projects.values():
            if project.status in [ProjectStatus.IN_PROGRESS, ProjectStatus.TESTING, ProjectStatus.DEPLOYED]:
                active_projects += 1
                total_revenue += project.actual_cost
            elif project.status == ProjectStatus.COMPLETED:
                completed_projects += 1
                total_revenue += project.actual_cost
        
        # Calculate service breakdown
        service_revenue = {}
        for project in self.projects.values():
            service_name = self.services[project.service_id].name
            service_revenue[service_name] = service_revenue.get(service_name, 0) + project.actual_cost
        
        return {
            "total_revenue": total_revenue,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "services_offered": len(self.services),
            "team_count": len(self.teams),
            "total_team_members": sum(len(team.members) for team in self.teams.values()),
            "average_project_value": total_revenue / max(len(self.projects), 1),
            "service_revenue_breakdown": service_revenue,
            "team_utilization": await self.get_team_utilization(),
            "top_performing_services": sorted(
                service_revenue.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }

# Singleton instance
professional_services_manager = ProfessionalServicesManager

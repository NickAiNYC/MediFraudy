"""
Data & Analytics Business Unit
Fraud trend reports, benchmarking, risk assessments, market intelligence
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import uuid
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class ReportType(Enum):
    FRAUD_TRENDS = "fraud_trends"
    BENCHMARKING = "benchmarking"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_INTELLIGENCE = "market_intelligence"
    INDUSTRY_ANALYSIS = "industry_analysis"
    COMPETITIVE_INTELLIGENCE = "competitive_intelligence"

class ReportFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_DEMAND = "on_demand"

@dataclass
class AnalyticsReport:
    id: str
    title: str
    report_type: ReportType
    frequency: ReportFrequency
    client_id: Optional[str]
    data_sources: List[str]
    methodology: str
    key_findings: List[str]
    recommendations: List[str]
    charts: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class DataProduct:
    id: str
    name: str
    description: str
    product_type: str
    pricing_model: str
    price: float
    features: List[str]
    target_market: List[str]
    revenue_generated: float
    customers_count: int
    created_at: datetime

class FraudTrendsAnalyzer:
    """Analyze fraud trends across industries and regions"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.trend_models = self._load_trend_models()
        
    def _load_trend_models(self) -> Dict[str, Any]:
        """Load fraud trend analysis models"""
        return {
            "seasonal_patterns": {
                "holiday_fraud_spike": 0.3,
                "end_of_year_increase": 0.25,
                "summer_vacation_fraud": 0.15
            },
            "industry_trends": {
                "healthcare": {
                    "telemedicine_fraud": 0.4,
                    "pharmacy_fraud": 0.3,
                    "durable_medical_equipment": 0.2
                },
                "insurance": {
                    "auto_insurance_fraud": 0.35,
                    "property_insurance_fraud": 0.25,
                    "workers_compensation_fraud": 0.2
                }
            },
            "geographic_hotspots": {
                "high_fraud_states": ["Florida", "California", "New York", "Texas"],
                "emerging_hotspots": ["Arizona", "Nevada", "Georgia"]
            }
        }
    
    async def analyze_fraud_trends(self, time_period: str, industry: Optional[str] = None) -> Dict[str, Any]:
        """Analyze fraud trends for specified time period"""
        
        # Get fraud data from database
        fraud_data = await self._get_fraud_data(time_period, industry)
        
        # Analyze trends
        trend_analysis = {
            "overall_trend": self._analyze_overall_trend(fraud_data),
            "seasonal_patterns": self._analyze_seasonal_patterns(fraud_data),
            "industry_breakdown": self._analyze_industry_breakdown(fraud_data),
            "geographic_analysis": self._analyze_geographic_patterns(fraud_data),
            "emerging_schemes": self._identify_emerging_schemes(fraud_data),
            "financial_impact": self._calculate_financial_impact(fraud_data),
            "predictions": self._generate_trend_predictions(fraud_data)
        }
        
        return trend_analysis
    
    async def _get_fraud_data(self, time_period: str, industry: Optional[str]) -> List[Dict]:
        """Get fraud data from database"""
        # Mock implementation - would query actual database
        return [
            {
                "date": "2026-01-01",
                "amount": 50000,
                "type": "healthcare",
                "scheme": "phantom_billing",
                "location": "Florida",
                "detected_by": "ai_system"
            },
            {
                "date": "2026-01-02",
                "amount": 75000,
                "type": "insurance",
                "scheme": "staged_accident",
                "location": "California",
                "detected_by": "human_investigator"
            }
        ]
    
    def _analyze_overall_trend(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Analyze overall fraud trend"""
        # Mock trend analysis
        return {
            "direction": "increasing",
            "growth_rate": 0.15,
            "confidence": 0.85,
            "key_drivers": ["economic_pressure", "sophisticated_schemes", "digital_transformation"]
        }
    
    def _analyze_seasonal_patterns(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Analyze seasonal patterns in fraud"""
        return {
            "holiday_season_spike": {
                "period": "Nov-Dec",
                "increase_percentage": 35,
                "primary_schemes": ["gift_card_fraud", "charity_scams"]
            },
            "summer_increase": {
                "period": "Jun-Aug",
                "increase_percentage": 20,
                "primary_schemes": ["vacation_rental_fraud", "travel_scams"]
            }
        }
    
    def _analyze_industry_breakdown(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Analyze fraud by industry"""
        return {
            "healthcare": {
                "total_amount": 45000000,
                "case_count": 1250,
                "average_case_value": 36000,
                "top_schemes": ["phantom_billing", "upcoding", "kickbacks"]
            },
            "insurance": {
                "total_amount": 32000000,
                "case_count": 890,
                "average_case_value": 35955,
                "top_schemes": ["staged_accidents", "false_claims", "inflated_losses"]
            }
        }
    
    def _analyze_geographic_patterns(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Analyze geographic patterns"""
        return {
            "hotspot_states": {
                "Florida": {
                    "total_amount": 15000000,
                    "case_count": 420,
                    "primary_schemes": ["medicaid_fraud", "auto_insurance"]
                },
                "California": {
                    "total_amount": 12000000,
                    "case_count": 380,
                    "primary_schemes": ["workers_comp", "property_insurance"]
                }
            },
            "emerging_hotspots": {
                "Arizona": {
                    "growth_rate": 0.45,
                    "primary_schemes": ["telemedicine_fraud"]
                }
            }
        }
    
    def _identify_emerging_schemes(self, fraud_data: List[Dict]) -> List[Dict[str, Any]]:
        """Identify emerging fraud schemes"""
        return [
            {
                "scheme": "AI-generated_fraud",
                "description": "Using AI to generate fake documents and claims",
                "growth_rate": 0.65,
                "risk_level": "high",
                "affected_industries": ["healthcare", "insurance"]
            },
            {
                "scheme": "cryptocurrency_laundering",
                "description": "Using crypto to launder fraud proceeds",
                "growth_rate": 0.55,
                "risk_level": "medium",
                "affected_industries": ["banking", "insurance"]
            }
        ]
    
    def _calculate_financial_impact(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Calculate financial impact of fraud"""
        return {
            "total_fraud_amount": 77000000,
            "recovered_amount": 23000000,
            "recovery_rate": 0.30,
            "prevented_amount": 45000000,
            "roi_on_detection": 3.5
        }
    
    def _generate_trend_predictions(self, fraud_data: List[Dict]) -> Dict[str, Any]:
        """Generate predictions for future trends"""
        return {
            "next_quarter_prediction": {
                "expected_increase": 0.18,
                "confidence": 0.75,
                "key_factors": ["economic_conditions", "regulatory_changes"]
            },
            "next_year_prediction": {
                "expected_increase": 0.22,
                "confidence": 0.65,
                "emerging_risks": ["deepfake_fraud", "supply_chain_fraud"]
            }
        }

class BenchmarkingService:
    """Benchmarking service for performance comparison"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.benchmark_data = self._load_benchmark_data()
        
    def _load_benchmark_data(self) -> Dict[str, Any]:
        """Load industry benchmark data"""
        return {
            "healthcare_fraud_detection": {
                "industry_average_detection_rate": 0.15,
                "top_quartile_detection_rate": 0.35,
                "median_processing_time": 45,  # days
                "top_quartile_processing_time": 7,
                "industry_average_cost_per_case": 250,
                "top_quartile_cost_per_case": 85
            },
            "insurance_claims_processing": {
                "industry_average_processing_time": 5,  # days
                "top_quartile_processing_time": 0.5,
                "industry_average_fraud_detection": 0.12,
                "top_quartile_fraud_detection": 0.28,
                "industry_average_cost_per_claim": 180,
                "top_quartile_cost_per_claim": 45
            }
        }
    
    async def generate_benchmark_report(self, client_id: str, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Generate benchmark comparison report"""
        
        # Determine industry
        industry = self._determine_industry(client_id)
        benchmarks = self.benchmark_data.get(industry, {})
        
        # Calculate percentiles
        percentiles = self._calculate_percentiles(metrics, benchmarks)
        
        # Generate recommendations
        recommendations = self._generate_benchmark_recommendations(percentiles)
        
        return {
            "client_id": client_id,
            "industry": industry,
            "performance_metrics": metrics,
            "benchmark_comparison": percentiles,
            "competitive_position": self._determine_competitive_position(percentiles),
            "improvement_opportunities": recommendations,
            "industry_leaders": self._get_industry_leaders(industry),
            "report_date": datetime.utcnow().isoformat()
        }
    
    def _determine_industry(self, client_id: str) -> str:
        """Determine client industry"""
        # Mock implementation - would query client data
        return "healthcare_fraud_detection"
    
    def _calculate_percentiles(self, metrics: Dict[str, float], benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance percentiles"""
        percentiles = {}
        
        for metric, value in metrics.items():
            if metric in benchmarks:
                industry_avg = benchmarks[metric]
                if metric.endswith("_rate") or metric.endswith("_score"):
                    # Higher is better
                    percentile = min(95, (value / industry_avg - 1) * 100)
                else:
                    # Lower is better (time, cost)
                    percentile = min(95, (1 - value / industry_avg) * 100)
                
                percentiles[metric] = {
                    "value": value,
                    "industry_average": industry_avg,
                    "percentile": max(5, percentile),
                    "performance": "above_average" if percentile > 50 else "below_average"
                }
        
        return percentiles
    
    def _generate_benchmark_recommendations(self, percentiles: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        for metric, data in percentiles.items():
            if data["percentile"] < 25:
                if "detection_rate" in metric:
                    recommendations.append(f"Improve {metric} by implementing advanced AI algorithms")
                elif "processing_time" in metric:
                    recommendations.append(f"Reduce {metric} through automation and process optimization")
                elif "cost" in metric:
                    recommendations.append(f"Lower {metric} by leveraging economies of scale")
        
        return recommendations
    
    def _determine_competitive_position(self, percentiles: Dict[str, Any]) -> str:
        """Determine overall competitive position"""
        avg_percentile = sum(data["percentile"] for data in percentiles.values()) / len(percentiles)
        
        if avg_percentile >= 75:
            return "leader"
        elif avg_percentile >= 50:
            return "competitive"
        elif avg_percentile >= 25:
            return "lagging"
        else:
            return "significant_improvement_needed"
    
    def _get_industry_leaders(self, industry: str) -> List[str]:
        """Get list of industry leaders"""
        if industry == "healthcare_fraud_detection":
            return ["Mayo Clinic", "Cleveland Clinic", "Kaiser Permanente"]
        elif industry == "insurance_claims_processing":
            return ["State Farm", "Allstate", "Progressive"]
        return []

class RiskAssessmentService:
    """Risk assessment and underwriting support"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_models = self._load_risk_models()
        
    def _load_risk_models(self) -> Dict[str, Any]:
        """Load risk assessment models"""
        return {
            "healthcare_provider_risk": {
                "factors": ["billing_patterns", "referral_networks", "compliance_history"],
                "weights": [0.4, 0.3, 0.3]
            },
            "insurance_claim_risk": {
                "factors": ["claim_history", "geographic_location", "provider_network"],
                "weights": [0.5, 0.2, 0.3]
            }
        }
    
    async def assess_risk(self, entity_data: Dict[str, Any], risk_type: str) -> Dict[str, Any]:
        """Assess risk for entity"""
        
        # Get risk model
        model = self.risk_models.get(risk_type, {})
        factors = model.get("factors", [])
        weights = model.get("weights", [])
        
        # Calculate risk scores
        risk_scores = {}
        for factor in factors:
            score = self._calculate_factor_score(entity_data, factor)
            risk_scores[factor] = score
        
        # Calculate overall risk score
        overall_score = sum(score * weight for score, weight in zip(risk_scores.values(), weights))
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_risk_recommendations(risk_level, risk_scores)
        
        return {
            "entity_id": entity_data.get("entity_id"),
            "risk_type": risk_type,
            "overall_score": overall_score,
            "risk_level": risk_level,
            "factor_scores": risk_scores,
            "recommendations": recommendations,
            "assessment_date": datetime.utcnow().isoformat()
        }
    
    def _calculate_factor_score(self, entity_data: Dict[str, Any], factor: str) -> float:
        """Calculate risk score for specific factor"""
        # Mock implementation - would use actual risk models
        if factor == "billing_patterns":
            return 0.65
        elif factor == "referral_networks":
            return 0.45
        elif factor == "compliance_history":
            return 0.25
        else:
            return 0.5
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "minimal"
    
    def _generate_risk_recommendations(self, risk_level: str, factor_scores: Dict[str, float]) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("Implement enhanced monitoring procedures")
            recommendations.append("Conduct comprehensive audit")
            recommendations.append("Consider additional verification requirements")
        
        # Factor-specific recommendations
        for factor, score in factor_scores.items():
            if score > 0.7:
                if factor == "billing_patterns":
                    recommendations.append("Review and validate billing practices")
                elif factor == "referral_networks":
                    recommendations.append("Analyze referral patterns for anomalies")
        
        return recommendations

class MarketIntelligenceService:
    """Market intelligence and competitive analysis"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = self._load_market_data()
        
    def _load_market_data(self) -> Dict[str, Any]:
        """Load market intelligence data"""
        return {
            "market_size": {
                "healthcare_fraud_detection": 10000000000,
                "insurance_fraud_detection": 8000000000,
                "total_addressable_market": 18000000000
            },
            "growth_rates": {
                "healthcare_fraud_detection": 0.15,
                "insurance_fraud_detection": 0.18,
                "overall_market": 0.16
            },
            "competitors": {
                "healthcare": ["Optum", "Change Healthcare", "IBM Watson Health"],
                "insurance": ["Guidewire", "Sapiens", "Duck Creek"]
            },
            "market_trends": [
                "AI adoption accelerating",
                "Regulatory compliance driving demand",
                "Consolidation in fraud detection market"
            ]
        }
    
    async def generate_market_intelligence(self, focus_area: str) -> Dict[str, Any]:
        """Generate market intelligence report"""
        
        market_data = self.market_data
        
        intelligence = {
            "focus_area": focus_area,
            "market_size": market_data["market_size"],
            "growth_projections": self._calculate_growth_projections(market_data),
            "competitive_landscape": self._analyze_competition(focus_area),
            "market_opportunities": self._identify_opportunities(focus_area),
            "threat_analysis": self._analyze_threats(focus_area),
            "strategic_recommendations": self._generate_strategic_recommendations(focus_area),
            "report_date": datetime.utcnow().isoformat()
        }
        
        return intelligence
    
    def _calculate_growth_projections(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate market growth projections"""
        projections = {}
        
        for segment, growth_rate in market_data["growth_rates"].items():
            current_size = market_data["market_size"].get(segment, 0)
            projections[segment] = {
                "current_size": current_size,
                "growth_rate": growth_rate,
                "projected_size_2027": current_size * (1 + growth_rate) ** 2,
                "projected_size_2030": current_size * (1 + growth_rate) ** 5
            }
        
        return projections
    
    def _analyze_competition(self, focus_area: str) -> Dict[str, Any]:
        """Analyze competitive landscape"""
        competitors = self.market_data["competitors"].get(focus_area, [])
        
        return {
            "major_players": competitors,
            "market_share_estimates": {
                "leader": competitors[0] if competitors else "Unknown",
                "market_leader_share": 0.25,
                "top_3_share": 0.60
            },
            "competitive_advantages": [
                "AI technology superiority",
                "Cross-industry expertise",
                "Regulatory compliance focus"
            ]
        }
    
    def _identify_opportunities(self, focus_area: str) -> List[str]:
        """Identify market opportunities"""
        return [
            "Untapped mid-market segment",
            "International expansion potential",
            "Partnership opportunities with incumbents",
            "Regulatory-driven demand growth"
        ]
    
    def _analyze_threats(self, focus_area: str) -> List[str]:
        """Analyze market threats"""
        return [
            "New entrants with deep pockets",
            "Regulatory changes affecting business model",
            "Technology disruption from AI advances",
            "Customer consolidation reducing addressable market"
        ]
    
    def _generate_strategic_recommendations(self, focus_area: str) -> List[str]:
        """Generate strategic recommendations"""
        return [
            "Focus on differentiation through AI superiority",
            "Develop strategic partnerships for market access",
            "Invest in international compliance capabilities",
            "Build ecosystem of complementary solutions"
        ]

class DataAnalyticsBusiness:
    """Main data analytics business unit"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fraud_analyzer = FraudTrendsAnalyzer(db)
        self.benchmarking_service = BenchmarkingService(db)
        self.risk_assessment_service = RiskAssessmentService(db)
        self.market_intelligence_service = MarketIntelligenceService(db)
        self.reports = {}
        self.data_products = self._initialize_data_products()
        
    def _initialize_data_products(self) -> Dict[str, DataProduct]:
        """Initialize data products catalog"""
        return {
            "fraud_trends_report": DataProduct(
                id="fraud_trends_report",
                name="Fraud Trends Quarterly Report",
                description="Comprehensive analysis of fraud trends across industries",
                product_type="report",
                pricing_model="subscription",
                price=25000,
                features=["Trend analysis", "Predictive insights", "Industry benchmarks"],
                target_market=["insurance_carriers", "healthcare_systems", "government_agencies"],
                revenue_generated=125000,
                customers_count=5,
                created_at=datetime.utcnow()
            ),
            "benchmarking_service": DataProduct(
                id="benchmarking_service",
                name="Performance Benchmarking",
                description="Compare your fraud detection performance against industry leaders",
                product_type="service",
                pricing_model="per_report",
                price=15000,
                features=["Performance comparison", "Improvement recommendations", "Industry insights"],
                target_market=["insurance_carriers", "healthcare_systems"],
                revenue_generated=90000,
                customers_count=6,
                created_at=datetime.utcnow()
            ),
            "risk_assessment_tool": DataProduct(
                id="risk_assessment_tool",
                name="Risk Assessment Platform",
                description="AI-powered risk assessment for underwriting and compliance",
                product_type="platform",
                pricing_model="subscription",
                price=35000,
                features=["Risk scoring", "Predictive analytics", "Compliance monitoring"],
                target_market=["insurance_carriers", "reinsurance_companies"],
                revenue_generated=175000,
                customers_count=5,
                created_at=datetime.utcnow()
            ),
            "market_intelligence": DataProduct(
                id="market_intelligence",
                name="Market Intelligence Service",
                description="Strategic market analysis and competitive intelligence",
                product_type="service",
                pricing_model="retainer",
                price=50000,
                features=["Market analysis", "Competitive intelligence", "Strategic insights"],
                target_market=["enterprise_clients", "investors", "strategic_partners"],
                revenue_generated=100000,
                customers_count=2,
                created_at=datetime.utcnow()
            )
        }
    
    async def generate_report(self, report_type: ReportType, 
                            parameters: Dict[str, Any],
                            client_id: Optional[str] = None) -> AnalyticsReport:
        """Generate analytics report"""
        
        report_id = str(uuid.uuid4())
        
        # Generate report content based on type
        if report_type == ReportType.FRAUD_TRENDS:
            content = await self.fraud_analyzer.analyze_fraud_trends(
                parameters.get("time_period", "quarterly"),
                parameters.get("industry")
            )
        elif report_type == ReportType.BENCHMARKING:
            content = await self.benchmarking_service.generate_benchmark_report(
                client_id, parameters.get("metrics", {})
            )
        elif report_type == ReportType.RISK_ASSESSMENT:
            content = await self.risk_assessment_service.assess_risk(
                parameters.get("entity_data", {}),
                parameters.get("risk_type", "healthcare_provider")
            )
        elif report_type == ReportType.MARKET_INTELLIGENCE:
            content = await self.market_intelligence_service.generate_market_intelligence(
                parameters.get("focus_area", "overall")
            )
        else:
            content = {"error": "Report type not supported"}
        
        # Create report object
        report = AnalyticsReport(
            id=report_id,
            title=self._generate_report_title(report_type, parameters),
            report_type=report_type,
            frequency=ReportFrequency(parameters.get("frequency", "on_demand")),
            client_id=client_id,
            data_sources=parameters.get("data_sources", ["internal_database", "industry_data"]),
            methodology="AI-powered analytics with human validation",
            key_findings=content.get("key_findings", []),
            recommendations=content.get("recommendations", []),
            charts=content.get("charts", []),
            tables=content.get("tables", []),
            metadata=content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store report
        self.reports[report_id] = report
        
        # Store in database
        await self.db.execute(text("""
            INSERT INTO analytics_reports (
                id, title, report_type, frequency, client_id, data_sources,
                methodology, key_findings, recommendations, charts, tables,
                metadata, created_at, updated_at
            ) VALUES (
                :id, :title, :report_type, :frequency, :client_id, :data_sources,
                :methodology, :key_findings, :recommendations, :charts, :tables,
                :metadata, :created_at, :updated_at
            )
        """), {
            "id": report.id,
            "title": report.title,
            "report_type": report.report_type.value,
            "frequency": report.frequency.value,
            "client_id": report.client_id,
            "data_sources": json.dumps(report.data_sources),
            "methodology": report.methodology,
            "key_findings": json.dumps(report.key_findings),
            "recommendations": json.dumps(report.recommendations),
            "charts": json.dumps(report.charts),
            "tables": json.dumps(report.tables),
            "metadata": json.dumps(report.metadata),
            "created_at": report.created_at,
            "updated_at": report.updated_at
        })
        
        await self.db.commit()
        
        return report
    
    def _generate_report_title(self, report_type: ReportType, parameters: Dict[str, Any]) -> str:
        """Generate report title"""
        titles = {
            ReportType.FRAUD_TRENDS: "Fraud Trends Analysis Report",
            ReportType.BENCHMARKING: "Performance Benchmarking Report",
            ReportType.RISK_ASSESSMENT: "Risk Assessment Report",
            ReportType.MARKET_INTELLIGENCE: "Market Intelligence Report"
        }
        
        base_title = titles.get(report_type, "Analytics Report")
        
        # Add time period if specified
        if "time_period" in parameters:
            base_title += f" - {parameters['time_period'].title()}"
        
        return base_title
    
    async def get_business_metrics(self) -> Dict[str, Any]:
        """Get data analytics business metrics"""
        total_revenue = sum(product.revenue_generated for product in self.data_products.values())
        total_customers = sum(product.customers_count for product in self.data_products.values())
        
        return {
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "products_count": len(self.data_products),
            "reports_generated": len(self.reports),
            "top_products": sorted(
                self.data_products.values(),
                key=lambda x: x.revenue_generated,
                reverse=True
            )[:3],
            "revenue_by_product": {
                product_id: product.revenue_generated
                for product_id, product in self.data_products.items()
            },
            "customer_breakdown": {
                product_id: product.customers_count
                for product_id, product in self.data_products.items()
            }
        }

# Singleton instance
data_analytics_business = DataAnalyticsBusiness

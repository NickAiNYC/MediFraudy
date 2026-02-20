"""
ClaimSwarm Engine - Autonomous Claims Processing and Fraud Detection
Integrates with MediFraudy for comprehensive fraud protection
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import numpy as np
from dataclasses import dataclass
from enum import Enum
import networkx as nx

logger = logging.getLogger(__name__)

class ClaimComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"

class ClaimStatus(Enum):
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    ESTIMATING = "estimating"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

@dataclass
class ClaimData:
    """Structured claim data"""
    claim_id: str
    policy_number: str
    claimant_name: str
    claim_type: str
    incident_date: datetime
    incident_location: str
    description: str
    photos: List[str]
    documents: List[str]
    estimated_amount: float
    police_report: Optional[str] = None
    witnesses: List[str] = None
    repair_shops: List[str] = None
    medical_providers: List[str] = None

@dataclass
class ClaimResult:
    """Claim processing result"""
    claim_id: str
    complexity: ClaimComplexity
    status: ClaimStatus
    fraud_score: float
    estimated_cost: float
    confidence: float
    suspicious_patterns: List[str]
    evidence_links: List[str]
    recommendation: str
    processing_time: float
    blockchain_hash: Optional[str] = None

class TriageAgent:
    """Intelligent claim triage and categorization"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.complexity_thresholds = {
            'amount': 10000,
            'injuries': 3,
            'vehicles': 2,
            'locations': 1
        }
    
    async def categorize_claim(self, claim: ClaimData) -> ClaimComplexity:
        """Categorize claim complexity"""
        complexity_score = 0
        
        # Amount-based complexity
        if claim.estimated_amount > self.complexity_thresholds['amount']:
            complexity_score += 2
        
        # Injury-based complexity
        if claim.medical_providers and len(claim.medical_providers) > self.complexity_thresholds['injuries']:
            complexity_score += 2
        
        # Multi-vehicle complexity
        if claim.claim_type == 'auto' and claim.claimant_name.count('&') > 0:
            complexity_score += 1
        
        # Location complexity
        if 'highway' in claim.incident_location.lower() or 'interstate' in claim.incident_location.lower():
            complexity_score += 1
        
        # Time-based complexity
        days_since_incident = (datetime.utcnow() - claim.incident_date).days
        if days_since_incident > 30:
            complexity_score += 1
        
        # Determine complexity
        if complexity_score >= 4:
            return ClaimComplexity.CRITICAL
        elif complexity_score >= 3:
            return ClaimComplexity.COMPLEX
        elif complexity_score >= 1:
            return ClaimComplexity.MODERATE
        else:
            return ClaimComplexity.SIMPLE

class InvestigatorSwarm:
    """Swarm of agents that investigate claims for fraud"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fraud_graph = nx.Graph()
        self.investigation_agents = [
            PoliceReportAgent(),
            SocialMediaAgent(),
            WeatherAgent(),
            RepairShopAgent(),
            MedicalProviderAgent(),
            LocationAgent()
        ]
    
    async def investigate_claim(self, claim: ClaimData) -> Dict[str, Any]:
        """Conduct comprehensive fraud investigation"""
        
        investigation_results = {
            'fraud_indicators': [],
            'suspicious_patterns': [],
            'evidence_links': [],
            'entity_connections': [],
            'risk_score': 0.0
        }
        
        # Run all investigation agents in parallel
        tasks = []
        for agent in self.investigation_agents:
            tasks.append(agent.investigate(claim))
        
        agent_results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for result in agent_results:
            investigation_results['fraud_indicators'].extend(result.get('indicators', []))
            investigation_results['suspicious_patterns'].extend(result.get('patterns', []))
            investigation_results['evidence_links'].extend(result.get('evidence', []))
        
        # Update fraud graph
        await self._update_fraud_graph(claim, investigation_results)
        
        # Calculate overall risk score
        investigation_results['risk_score'] = self._calculate_risk_score(investigation_results)
        
        return investigation_results
    
    async def _update_fraud_graph(self, claim: ClaimData, results: Dict[str, Any]):
        """Update the fraud graph with new claim data"""
        
        # Add entities to graph
        entities = {
            'claimant': claim.claimant_name,
            'location': claim.incident_location,
            'policy': claim.policy_number
        }
        
        # Add medical providers if present
        if claim.medical_providers:
            for provider in claim.medical_providers:
                entities[f'medical_{provider}'] = provider
        
        # Add repair shops if present
        if claim.repair_shops:
            for shop in claim.repair_shops:
                entities[f'repair_{shop}'] = shop
        
        # Create connections
        entity_list = list(entities.values())
        for i, entity1 in enumerate(entity_list):
            for entity2 in entity_list[i+1:]:
                if self.fraud_graph.has_edge(entity1, entity2):
                    self.fraud_graph[entity1][entity2]['weight'] += 1
                else:
                    self.fraud_graph.add_edge(entity1, entity2, weight=1)
        
        # Check for suspicious patterns in graph
        suspicious_connections = self._find_suspicious_connections(claim.claimant_name)
        results['entity_connections'] = suspicious_connections
    
    def _find_suspicious_connections(self, claimant: str) -> List[Dict]:
        """Find suspicious connections in fraud graph"""
        suspicious = []
        
        if claimant in self.fraud_graph:
            # Check for high-degree nodes (potential fraud rings)
            neighbors = list(self.fraud_graph.neighbors(claimant))
            for neighbor in neighbors:
                edge_weight = self.fraud_graph[claimant][neighbor]['weight']
                if edge_weight > 3:  # Appeared together in >3 claims
                    suspicious.append({
                        'entity': neighbor,
                        'connection_count': edge_weight,
                        'suspicion_level': 'high' if edge_weight > 5 else 'medium'
                    })
        
        return suspicious
    
    def _calculate_risk_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall fraud risk score"""
        score = 0.0
        
        # Fraud indicators
        score += len(results['fraud_indicators']) * 0.1
        
        # Suspicious patterns
        score += len(results['suspicious_patterns']) * 0.2
        
        # Entity connections
        high_risk_connections = len([c for c in results['entity_connections'] if c['suspicion_level'] == 'high'])
        score += high_risk_connections * 0.3
        
        return min(1.0, score)

class EstimatorAgent:
    """Computer vision-based damage assessment and cost estimation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.damage_models = self._load_damage_models()
        self.cost_database = self._load_cost_database()
    
    async def estimate_from_photos(self, claim: ClaimData) -> Dict[str, Any]:
        """Estimate repair costs from photos"""
        
        estimation_results = {
            'damage_assessment': {},
            'cost_breakdown': {},
            'confidence_score': 0.0,
            'estimated_total': 0.0,
            'recommended_settlement': 0.0
        }
        
        # Analyze each photo
        total_damage = 0.0
        confidence_scores = []
        
        for photo_url in claim.photos:
            damage_result = await self._analyze_photo(photo_url, claim.claim_type)
            estimation_results['damage_assessment'][photo_url] = damage_result
            
            total_damage += damage_result['estimated_cost']
            confidence_scores.append(damage_result['confidence'])
        
        # Calculate overall confidence
        estimation_results['confidence_score'] = np.mean(confidence_scores) if confidence_scores else 0.5
        
        # Generate cost breakdown
        estimation_results['cost_breakdown'] = await self._generate_cost_breakdown(claim.claim_type, total_damage)
        
        # Calculate total and recommended settlement
        estimation_results['estimated_total'] = total_damage
        estimation_results['recommended_settlement'] = total_damage * 0.9  # 10% negotiation buffer
        
        return estimation_results
    
    async def _analyze_photo(self, photo_url: str, claim_type: str) -> Dict[str, Any]:
        """Analyze individual photo for damage"""
        
        # Mock computer vision analysis
        # In production, would use actual CV models
        
        damage_types = {
            'auto': ['bumper', 'door', 'window', 'roof', 'frame'],
            'property': ['roof', 'wall', 'window', 'foundation', 'structural'],
            'liability': ['injury', 'property_damage', 'medical', 'therapy']
        }
        
        detected_damage = []
        for damage_type in damage_types.get(claim_type, []):
            # Simulate damage detection
            if np.random.random() < 0.3:  # 30% chance of each damage type
                severity = np.random.uniform(0.1, 1.0)
                cost = severity * np.random.uniform(500, 5000)
                
                detected_damage.append({
                    'type': damage_type,
                    'severity': severity,
                    'estimated_cost': cost,
                    'confidence': np.random.uniform(0.7, 0.95)
                })
        
        total_cost = sum(d['estimated_cost'] for d in detected_damage)
        avg_confidence = np.mean([d['confidence'] for d in detected_damage]) if detected_damage else 0.5
        
        return {
            'detected_damage': detected_damage,
            'estimated_cost': total_cost,
            'confidence': avg_confidence
        }
    
    async def _generate_cost_breakdown(self, claim_type: str, total_damage: float) -> Dict[str, float]:
        """Generate detailed cost breakdown"""
        
        breakdown_templates = {
            'auto': {
                'parts': 0.4,
                'labor': 0.35,
                'paint': 0.15,
                'miscellaneous': 0.1
            },
            'property': {
                'materials': 0.5,
                'labor': 0.3,
                'permits': 0.1,
                'miscellaneous': 0.1
            },
            'liability': {
                'medical': 0.6,
                'therapy': 0.2,
                'lost_wages': 0.15,
                'miscellaneous': 0.05
            }
        }
        
        template = breakdown_templates.get(claim_type, breakdown_templates['auto'])
        
        return {category: total_damage * ratio for category, ratio in template.items()}
    
    def _load_damage_models(self):
        """Load computer vision models for damage detection"""
        # In production, would load actual ML models
        return {
            'auto_damage_model': 'auto_damage_v2.pt',
            'property_damage_model': 'property_damage_v1.pt',
            'injury_detection_model': 'injury_detection_v1.pt'
        }
    
    def _load_cost_database(self):
        """Load cost database for estimation"""
        # In production, would load actual cost data
        return {
            'auto_parts': {'bumper': 500, 'door': 800, 'window': 300},
            'labor_rates': {'auto': 75, 'property': 65, 'general': 55}
        }

class SettlerAgent:
    """Intelligent claim settlement and approval"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.approval_thresholds = {
            ClaimComplexity.SIMPLE: 0.3,
            ClaimComplexity.MODERATE: 0.2,
            ClaimComplexity.COMPLEX: 0.1,
            ClaimComplexity.CRITICAL: 0.05
        }
    
    async def process_claim_settlement(self, claim: ClaimData, investigation: Dict, estimation: Dict, complexity: ClaimComplexity) -> Dict[str, Any]:
        """Process claim settlement decision"""
        
        settlement_results = {
            'decision': 'pending',
            'settlement_amount': 0.0,
            'confidence': 0.0,
            'reasoning': [],
            'escalation_required': False,
            'suspicion_dossier': {}
        }
        
        # Calculate fraud risk
        fraud_score = investigation.get('risk_score', 0.0)
        
        # Get approval threshold for complexity
        approval_threshold = self.approval_thresholds[complexity]
        
        # Make decision
        if fraud_score < approval_threshold:
            settlement_results['decision'] = 'auto_approve'
            settlement_results['settlement_amount'] = estimation.get('recommended_settlement', claim.estimated_amount)
            settlement_results['confidence'] = 0.9
            settlement_results['reasoning'].append('Low fraud risk detected')
            settlement_results['reasoning'].append(f'Risk score {fraud_score:.2f} below threshold {approval_threshold:.2f}')
        else:
            settlement_results['decision'] = 'escalate'
            settlement_results['escalation_required'] = True
            settlement_results['confidence'] = 0.6
            settlement_results['reasoning'].append('High fraud risk detected')
            settlement_results['reasoning'].append(f'Risk score {fraud_score:.2f} above threshold {approval_threshold:.2f}')
            
            # Create suspicion dossier
            settlement_results['suspicion_dossier'] = {
                'fraud_indicators': investigation.get('fraud_indicators', []),
                'suspicious_patterns': investigation.get('suspicious_patterns', []),
                'entity_connections': investigation.get('entity_connections', []),
                'recommended_investigation': self._generate_investigation_recommendations(investigation)
            }
        
        return settlement_results
    
    def _generate_investigation_recommendations(self, investigation: Dict) -> List[str]:
        """Generate recommendations for human investigators"""
        recommendations = []
        
        if investigation.get('fraud_indicators'):
            recommendations.append('Verify all claimant statements with external sources')
        
        if investigation.get('entity_connections'):
            recommendations.append('Investigate connections to known fraud networks')
        
        if investigation.get('suspicious_patterns'):
            recommendations.append('Review historical claims for similar patterns')
        
        recommendations.append('Conduct in-person interview with claimant')
        recommendations.append('Verify all documentation authenticity')
        
        return recommendations

# Individual Investigation Agents
class PoliceReportAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate police report consistency"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        if claim.police_report:
            # Mock police report analysis
            if np.random.random() < 0.1:  # 10% chance of inconsistency
                results['indicators'].append('Police report inconsistencies detected')
                results['patterns'].append('Timeline discrepancies')
                results['evidence'].append('police_report_analysis')
        
        return results

class SocialMediaAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate social media for evidence"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        # Mock social media analysis
        if np.random.random() < 0.15:  # 15% chance of suspicious activity
            results['indicators'].append('Suspicious social media activity')
            results['patterns'].append('Posts inconsistent with claim')
            results['evidence'].append('social_media_analysis')
        
        return results

class WeatherAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate weather conditions consistency"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        # Mock weather analysis
        if np.random.random() < 0.05:  # 5% chance of weather inconsistency
            results['indicators'].append('Weather conditions inconsistent with claim')
            results['patterns'].append('Impossible weather scenario')
            results['evidence'].append('weather_data_analysis')
        
        return results

class RepairShopAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate repair shop reputation and patterns"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        if claim.repair_shops:
            for shop in claim.repair_shops:
                # Mock repair shop analysis
                if np.random.random() < 0.2:  # 20% chance of suspicious shop
                    results['indicators'].append(f'Suspicious repair shop: {shop}')
                    results['patterns'].append('Repeated claims with same shop')
                    results['evidence'].append(f'repair_shop_analysis_{shop}')
        
        return results

class MedicalProviderAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate medical provider patterns"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        if claim.medical_providers:
            for provider in claim.medical_providers:
                # Mock medical provider analysis
                if np.random.random() < 0.15:  # 15% chance of suspicious provider
                    results['indicators'].append(f'Suspicious medical provider: {provider}')
                    results['patterns'].append('Unusual billing patterns')
                    results['evidence'].append(f'medical_provider_analysis_{provider}')
        
        return results

class LocationAgent:
    async def investigate(self, claim: ClaimData) -> Dict[str, Any]:
        """Investigate location-based patterns"""
        results = {'indicators': [], 'patterns': [], 'evidence': []}
        
        # Mock location analysis
        if np.random.random() < 0.1:  # 10% chance of suspicious location
            results['indicators'].append('High fraud area detected')
            results['patterns'].append('Multiple claims from same location')
            results['evidence'].append('location_pattern_analysis')
        
        return results

class ClaimSwarmEngine:
    """Main ClaimSwarm orchestration engine"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.triage_agent = TriageAgent(db)
        self.investigator_swarm = InvestigatorSwarm(db)
        self.estimator_agent = EstimatorAgent(db)
        self.settler_agent = SettlerAgent(db)
        
        # Integration with MediFraudy
        self.fraud_graph = self.investigator_swarm.fraud_graph
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> ClaimResult:
        """Process a complete claim through the swarm"""
        
        start_time = datetime.utcnow()
        
        # Parse claim data
        claim = ClaimData(
            claim_id=claim_data['claim_id'],
            policy_number=claim_data['policy_number'],
            claimant_name=claim_data['claimant_name'],
            claim_type=claim_data['claim_type'],
            incident_date=datetime.fromisoformat(claim_data['incident_date']),
            incident_location=claim_data['incident_location'],
            description=claim_data['description'],
            photos=claim_data.get('photos', []),
            documents=claim_data.get('documents', []),
            estimated_amount=claim_data.get('estimated_amount', 0.0),
            police_report=claim_data.get('police_report'),
            witnesses=claim_data.get('witnesses', []),
            repair_shops=claim_data.get('repair_shops', []),
            medical_providers=claim_data.get('medical_providers', [])
        )
        
        # Step 1: Triage
        complexity = await self.triage_agent.categorize_claim(claim)
        
        # Step 2: Investigation (parallel with estimation for simple claims)
        investigation_task = self.investigator_swarm.investigate_claim(claim)
        estimation_task = self.estimator_agent.estimate_from_photos(claim)
        
        if complexity == ClaimComplexity.SIMPLE:
            # Run in parallel for simple claims
            investigation, estimation = await asyncio.gather(investigation_task, estimation_task)
        else:
            # Sequential for complex claims
            investigation = await investigation_task
            estimation = await estimation_task
        
        # Step 3: Settlement
        settlement = await self.settler_agent.process_claim_settlement(
            claim, investigation, estimation, complexity
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create result
        result = ClaimResult(
            claim_id=claim.claim_id,
            complexity=complexity,
            status=ClaimStatus.APPROVED if settlement['decision'] == 'auto_approve' else ClaimStatus.ESCALATED,
            fraud_score=investigation.get('risk_score', 0.0),
            estimated_cost=estimation.get('estimated_total', claim.estimated_amount),
            confidence=settlement.get('confidence', 0.0),
            suspicious_patterns=investigation.get('suspicious_patterns', []),
            evidence_links=investigation.get('evidence_links', []),
            recommendation=settlement['decision'],
            processing_time=processing_time
        )
        
        # Add to blockchain evidence (integration with MediFraudy)
        from services.blockchain_evidence import blockchain_evidence
        
        evidence_data = {
            'claim_id': claim.claim_id,
            'processing_result': {
                'complexity': complexity.value,
                'fraud_score': result.fraud_score,
                'decision': settlement['decision'],
                'processing_time': processing_time
            },
            'investigation_summary': investigation,
            'estimation_summary': estimation
        }
        
        try:
            await blockchain_evidence.initialize_blockchain()
            result.blockchain_hash = await blockchain_evidence.add_evidence(
                'claim_processing', evidence_data, 0, claim.claim_id, 'claimswarm_ai'
            )
        except Exception as e:
            logger.warning(f"Failed to add claim evidence to blockchain: {e}")
        
        return result
    
    async def get_fraud_graph_metrics(self) -> Dict[str, Any]:
        """Get fraud graph analytics"""
        
        return {
            'total_entities': self.fraud_graph.number_of_nodes(),
            'total_connections': self.fraud_graph.number_of_edges(),
            'high_risk_entities': len([n for n in self.fraud_graph.nodes() if self.fraud_graph.degree(n) > 5]),
            'connected_components': nx.number_connected_components(self.fraud_graph),
            'average_clustering': nx.average_clustering(self.fraud_graph)
        }
    
    async def find_fraud_rings(self, min_size: int = 3) -> List[List[str]]:
        """Find potential fraud rings in the graph"""
        
        fraud_rings = []
        
        # Find cliques (complete subgraphs) that might indicate fraud rings
        for clique in nx.find_cliques(self.fraud_graph):
            if len(clique) >= min_size:
                # Check if this clique has high connectivity
                subgraph = self.fraud_graph.subgraph(clique)
                if nx.is_connected(subgraph):
                    fraud_rings.append(list(clique))
        
        return fraud_rings

# Singleton instance
claimswarm_engine = ClaimSwarmEngine

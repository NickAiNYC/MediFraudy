"""
Graph-based fraud detection using NetworkX and Neo4j-style analytics.
Detects:
- Fraud rings (dense subgraphs)
- Kickback patterns (bidirectional referral flows)
- Unusual beneficiary sharing
- Provider collusion networks
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging

try:
    import community as community_louvain
except ImportError:
    community_louvain = None
    logging.warning("python-louvain not installed. Community detection will be limited.")

logger = logging.getLogger(__name__)


class FraudRingDetector:
    """
    Advanced graph analytics for fraud ring detection.
    Uses community detection, centrality analysis, and pattern matching.
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.graph = nx.Graph()
        self.directed_graph = nx.DiGraph()
        self.provider_metadata = {}
        self.beneficiary_graph = nx.Graph()  # Bipartite graph
        
    def build_provider_network(self, 
                               min_shared_patients: int = 5,
                               lookback_days: int = 730) -> nx.Graph:
        """
        Build graph where:
        - Nodes: Providers (with metadata: type, risk_score, capacity)
        - Edges: Shared beneficiaries, referral relationships
        - Edge weight: Number of shared patients / referral volume
        
        Returns NetworkX graph for analysis.
        """
        logger.info(f"Building provider network with {min_shared_patients} min shared patients, {lookback_days} day lookback")
        
        # Query shared beneficiaries between providers
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Mock data structure - in production, this would query actual database
        # For demonstration, we'll create sample data
        providers = self._get_providers()
        shared_data = self._get_shared_beneficiaries(cutoff_date, min_shared_patients)
        
        # Add nodes with metadata
        for p in providers:
            self.graph.add_node(
                p['id'], 
                name=p['name'],
                type=p.get('facility_type', 'Unknown'),
                risk_score=p.get('risk_score', 0),
                capacity=p.get('licensed_capacity', 0),
                npi=p.get('npi', 'N/A'),
                address=p.get('address', ''),
                total_claims=p.get('total_claims', 0)
            )
            self.provider_metadata[p['id']] = p
        
        # Add weighted edges
        for row in shared_data:
            self.graph.add_edge(
                row['provider_a'], 
                row['provider_b'],
                weight=row['shared_patients'],
                claims=row['total_claims'],
                connection_type='shared_beneficiaries'
            )
        
        logger.info(f"Built network with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        return self.graph
    
    def build_referral_network(self, lookback_days: int = 730) -> nx.DiGraph:
        """Build directed graph of referral relationships for kickback detection."""
        logger.info("Building referral network")
        
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        referrals = self._get_referrals(cutoff_date)
        
        for ref in referrals:
            if not self.directed_graph.has_node(ref['referring_provider']):
                self.directed_graph.add_node(
                    ref['referring_provider'],
                    **self.provider_metadata.get(ref['referring_provider'], {})
                )
            if not self.directed_graph.has_node(ref['receiving_provider']):
                self.directed_graph.add_node(
                    ref['receiving_provider'],
                    **self.provider_metadata.get(ref['receiving_provider'], {})
                )
            
            self.directed_graph.add_edge(
                ref['referring_provider'],
                ref['receiving_provider'],
                weight=ref['volume'],
                referral_type=ref.get('type', 'general')
            )
        
        return self.directed_graph
    
    def detect_fraud_rings(self, min_size: int = 3) -> List[Dict[str, Any]]:
        """
        Detect fraud rings using:
        1. Louvain community detection
        2. Density-based analysis
        3. Risk score aggregation
        
        Returns ranked list of suspicious communities.
        """
        logger.info("Detecting fraud rings...")
        
        if self.graph.number_of_nodes() == 0:
            logger.warning("Empty graph - no fraud rings to detect")
            return []
        
        # Community detection
        if community_louvain:
            communities = community_louvain.best_partition(self.graph)
        else:
            # Fallback: use connected components
            communities = {}
            for idx, component in enumerate(nx.connected_components(self.graph)):
                for node in component:
                    communities[node] = idx
        
        # Analyze each community
        fraud_rings = []
        community_groups = defaultdict(list)
        
        for node, community_id in communities.items():
            community_groups[community_id].append(node)
        
        for community_id, nodes in community_groups.items():
            if len(nodes) < min_size:  # Skip small groups
                continue
            
            subgraph = self.graph.subgraph(nodes)
            
            # Calculate fraud indicators
            density = nx.density(subgraph)
            
            # Risk scores
            risk_scores = [
                self.graph.nodes[n].get('risk_score', 0) 
                for n in nodes
            ]
            avg_risk = np.mean(risk_scores) if risk_scores else 0
            max_risk = np.max(risk_scores) if risk_scores else 0
            
            # Reciprocity (for directed subgraph)
            reciprocity = self._calculate_reciprocity(subgraph)
            
            # Triangle count
            triangle_count = sum(nx.triangles(subgraph).values()) // 3
            
            # Total claims volume
            total_claims = sum(
                self.graph.nodes[n].get('total_claims', 0) 
                for n in nodes
            )
            
            fraud_score = self._calculate_ring_fraud_score(
                density, avg_risk, reciprocity, triangle_count, len(nodes), total_claims
            )
            
            if fraud_score > 50:  # Threshold for inclusion
                providers_data = [
                    {
                        'id': n,
                        'name': self.graph.nodes[n].get('name', f'Provider {n}'),
                        'type': self.graph.nodes[n].get('type', 'Unknown'),
                        'risk_score': self.graph.nodes[n].get('risk_score', 0),
                        'npi': self.graph.nodes[n].get('npi', 'N/A')
                    }
                    for n in nodes
                ]
                
                fraud_rings.append({
                    'community_id': int(community_id),
                    'size': int(len(nodes)),
                    'density': float(round(density, 4)),
                    'avg_risk_score': float(round(avg_risk, 2)),
                    'max_risk_score': float(round(max_risk, 2)),
                    'reciprocity': float(round(reciprocity, 4)),
                    'triangles': int(triangle_count),
                    'total_claims': int(total_claims),
                    'fraud_score': float(round(fraud_score, 2)),
                    'suspicion_level': 'CRITICAL' if fraud_score > 90 else 'HIGH' if fraud_score > 75 else 'MEDIUM',
                    'providers': providers_data,
                    'detection_patterns': self._identify_patterns(subgraph, nodes)
                })
        
        sorted_rings = sorted(fraud_rings, key=lambda x: x['fraud_score'], reverse=True)
        logger.info(f"Detected {len(sorted_rings)} fraud rings")
        return sorted_rings
    
    def detect_kickback_cycles(self, min_volume: int = 10) -> List[Dict[str, Any]]:
        """
        Detect directed cycles that indicate kickback schemes.
        Brooklyn $68M case pattern: A refers to B, B refers to C, C refers to A.
        """
        logger.info("Detecting kickback cycles...")
        
        if self.directed_graph.number_of_nodes() == 0:
            self.build_referral_network()
        
        # Find all simple cycles
        try:
            cycles = list(nx.simple_cycles(self.directed_graph))
        except:
            cycles = []
            logger.warning("Cycle detection failed")
        
        suspicious_cycles = []
        
        for cycle in cycles:
            if len(cycle) < 3:  # Minimum cycle length for meaningful kickbacks
                continue
            
            # Calculate total referral volume in cycle
            cycle_edges = [(cycle[i], cycle[(i+1) % len(cycle)]) for i in range(len(cycle))]
            
            total_volume = 0
            for u, v in cycle_edges:
                if self.directed_graph.has_edge(u, v):
                    total_volume += self.directed_graph[u][v].get('weight', 0)
            
            if total_volume < min_volume:
                continue
            
            avg_volume = total_volume / len(cycle)
            
            # Calculate cycle risk score
            provider_risks = [
                self.directed_graph.nodes[n].get('risk_score', 0)
                for n in cycle
            ]
            avg_risk = np.mean(provider_risks) if provider_risks else 0
            
            suspicion_score = min(100, (total_volume / 50) + avg_risk)
            
            suspicious_cycles.append({
                'providers': [
                    {'id': int(u), 'name': self.provider_metadata.get(u, {}).get('name', f'Provider {u}')}
                    for u in cycle
                ],
                'length': int(len(cycle)),
                'total_volume': int(total_volume),
                'avg_volume': float(round(avg_volume, 2)),
                'avg_risk_score': float(round(avg_risk, 2)),
                'suspicion_score': float(round(suspicion_score, 2)),
                'cycle_type': 'direct_kickback' if len(cycle) == 2 else 'circular_referral'
            })
        
        sorted_cycles = sorted(suspicious_cycles, key=lambda x: x['suspicion_score'], reverse=True)
        logger.info(f"Detected {len(sorted_cycles)} kickback cycles")
        return sorted_cycles[:50]  # Limit to top 50
    
    def find_beneficiary_concentration_rings(self, 
                                            min_overlap: int = 5,
                                            overlap_threshold: float = 0.7) -> List[Dict]:
        """
        Detect groups of providers sharing the same small set of beneficiaries.
        Key indicator of patient brokering/kickbacks.
        """
        logger.info("Finding beneficiary concentration rings...")
        
        # Build provider-beneficiary bipartite graph
        provider_beneficiaries = self._get_provider_beneficiary_relationships()
        
        suspicious_sets = []
        provider_list = list(provider_beneficiaries.keys())
        
        for i, p1 in enumerate(provider_list):
            p1_beneficiaries = set(provider_beneficiaries[p1])
            
            if len(p1_beneficiaries) < min_overlap:
                continue
            
            for p2 in provider_list[i+1:]:
                p2_beneficiaries = set(provider_beneficiaries[p2])
                
                overlap = p1_beneficiaries & p2_beneficiaries
                if len(overlap) < min_overlap:
                    continue
                
                overlap_ratio = len(overlap) / min(len(p1_beneficiaries), len(p2_beneficiaries))
                
                if overlap_ratio >= overlap_threshold:
                    suspicious_sets.append({
                        'providers': [
                        {
                            'id': int(p1),
                            'name': self.provider_metadata.get(p1, {}).get('name', f'Provider {p1}')
                        },
                        {
                            'id': int(p2),
                            'name': self.provider_metadata.get(p2, {}).get('name', f'Provider {p2}')
                        }
                    ],
                    'provider_ids': [int(p1), int(p2)],
                    'overlap_count': int(len(overlap)),
                    'overlap_ratio': float(round(overlap_ratio, 4)),
                    'suspicion_score': float(round(overlap_ratio * 100, 2)),
                    'pattern_type': 'beneficiary_concentration',
                    'beneficiary_ids': [int(b) for b in list(overlap)[:10]]  # Sample
                })
        
        sorted_sets = sorted(suspicious_sets, key=lambda x: x['suspicion_score'], reverse=True)
        logger.info(f"Found {len(sorted_sets)} beneficiary concentration patterns")
        return sorted_sets[:100]  # Limit results
    
    def _calculate_ring_fraud_score(self, density, avg_risk, reciprocity, 
                                    triangles, size, total_claims):
        """Calculate fraud likelihood for a provider community."""
        score = 0
        
        # Dense networks are suspicious (max 25 points)
        score += min(25, density * 100)
        
        # High individual risk scores (max 30 points)
        score += min(30, avg_risk * 0.5)
        
        # Mutual referrals indicate collusion (max 20 points)
        score += min(20, reciprocity * 50)
        
        # Triangle density shows tight collaboration (max 15 points)
        max_triangles = size * (size - 1) * (size - 2) / 6
        triangle_density = triangles / max_triangles if max_triangles > 0 else 0
        score += min(15, triangle_density * 100)
        
        # Large claim volumes (max 10 points)
        if total_claims > 10000:
            score += 10
        elif total_claims > 5000:
            score += 5
        
        return min(100, score)
    
    def _calculate_reciprocity(self, graph) -> float:
        """Calculate reciprocity score for undirected graph (mutual connections)."""
        if graph.number_of_edges() == 0:
            return 0.0
        
        # For undirected graph, check if edges would be reciprocal in directed context
        # This is a simplified measure
        reciprocal_count = 0
        total_edges = 0
        
        for u, v in graph.edges():
            total_edges += 1
            # In undirected graph, edges are inherently reciprocal
            reciprocal_count += 1
        
        return reciprocal_count / total_edges if total_edges > 0 else 0.0
    
    def _identify_patterns(self, subgraph, nodes) -> List[str]:
        """Identify specific fraud patterns in a community."""
        patterns = []
        
        # High density
        if nx.density(subgraph) > 0.7:
            patterns.append("extremely_dense_network")
        
        # Star pattern (one central provider)
        degrees = dict(subgraph.degree())
        max_degree = max(degrees.values()) if degrees else 0
        if max_degree > len(nodes) * 0.7:
            patterns.append("star_topology_hub")
        
        # Clique detection
        cliques = list(nx.find_cliques(subgraph))
        if any(len(c) >= len(nodes) * 0.8 for c in cliques):
            patterns.append("near_complete_graph")
        
        # High average clustering
        if nx.average_clustering(subgraph) > 0.8:
            patterns.append("high_clustering")
        
        return patterns
    
    def get_ego_network(self, provider_id: int, depth: int = 2) -> Dict[str, Any]:
        """Extract ego network for a specific provider."""
        if provider_id not in self.graph:
            return {'nodes': [], 'edges': [], 'error': 'Provider not found'}
        
        # Get nodes within depth
        nodes = set([provider_id])
        for _ in range(depth):
            neighbors = set()
            for node in nodes:
                if node in self.graph:
                    neighbors.update(self.graph.neighbors(node))
            nodes.update(neighbors)
        
        subgraph = self.graph.subgraph(nodes)
        
        return {
            'nodes': [
                {
                    'id': n,
                    **self.graph.nodes[n]
                }
                for n in subgraph.nodes()
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    **subgraph.edges[u, v]
                }
                for u, v in subgraph.edges()
            ],
            'center_node': provider_id,
            'depth': depth,
            'total_nodes': len(subgraph.nodes()),
            'total_edges': len(subgraph.edges())
        }
    
    def generate_network_insights(self) -> Dict[str, Any]:
        """Generate comprehensive network analysis report.

        Includes degree centrality, betweenness centrality, community detection,
        shared address clusters, and cross-borough mapping.
        """
        logger.info("Generating network insights...")
        
        if self.graph.number_of_nodes() == 0:
            self.build_provider_network()
        
        # Degree centrality
        degree_centrality = nx.degree_centrality(self.graph)
        top_degree = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]

        # Betweenness centrality — identifies brokers between clusters
        betweenness = nx.betweenness_centrality(self.graph)
        top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Community summary
        if community_louvain:
            communities = community_louvain.best_partition(self.graph)
            num_communities = len(set(communities.values()))
        else:
            num_communities = nx.number_connected_components(self.graph)

        # Shared address clusters
        shared_address_clusters = self._detect_shared_address_clusters()

        # Cross-borough cluster mapping
        cross_borough_clusters = self._detect_cross_borough_clusters(communities if community_louvain else {})
        
        insights = {
            'total_providers': int(self.graph.number_of_nodes()),
            'total_connections': int(self.graph.number_of_edges()),
            'network_density': float(round(nx.density(self.graph), 6)),
            'num_communities': int(num_communities),
            'avg_clustering': float(round(nx.average_clustering(self.graph), 4)),
            'fraud_rings': self.detect_fraud_rings(),
            'kickback_cycles': self.detect_kickback_cycles(),
            'beneficiary_concentration': self.find_beneficiary_concentration_rings(),
            'shared_address_clusters': shared_address_clusters,
            'cross_borough_clusters': cross_borough_clusters,
            'most_central_providers': [
                {
                    'id': int(node_id),
                    'name': self.graph.nodes[node_id].get('name', f'Provider {node_id}'),
                    'degree_centrality': float(round(score, 4)),
                    'betweenness_centrality': float(round(betweenness.get(node_id, 0), 4)),
                    'risk_score': float(self.graph.nodes[node_id].get('risk_score', 0))
                }
                for node_id, score in top_degree
            ],
            'top_betweenness_brokers': [
                {
                    'id': int(node_id),
                    'name': self.graph.nodes[node_id].get('name', f'Provider {node_id}'),
                    'betweenness_centrality': float(round(score, 4)),
                    'risk_score': float(self.graph.nodes[node_id].get('risk_score', 0))
                }
                for node_id, score in top_betweenness
                if score > 0
            ],
        }
        
        logger.info("Network insights generated successfully")
        return insights

    def _detect_shared_address_clusters(self) -> List[Dict[str, Any]]:
        """Detect providers sharing the same address (potential shell entities).

        Shared addresses are a strong indicator of coordinated fraud schemes
        where multiple provider entities operate from one location.
        """
        address_groups: Dict[str, List[int]] = defaultdict(list)
        for node_id in self.graph.nodes():
            addr = self.graph.nodes[node_id].get('address', '').strip().lower()
            if addr and addr not in ('', 'unknown', 'n/a'):
                address_groups[addr].append(node_id)

        clusters = []
        for addr, provider_ids in address_groups.items():
            if len(provider_ids) < 2:
                continue
            providers_data = [
                {
                    'id': int(pid),
                    'name': self.graph.nodes[pid].get('name', f'Provider {pid}'),
                    'type': self.graph.nodes[pid].get('type', 'Unknown'),
                }
                for pid in provider_ids
            ]
            clusters.append({
                'address': addr,
                'provider_count': len(provider_ids),
                'providers': providers_data,
                'suspicion_level': 'HIGH' if len(provider_ids) >= 4 else 'MEDIUM',
            })

        clusters.sort(key=lambda x: x['provider_count'], reverse=True)
        return clusters[:50]

    def _detect_cross_borough_clusters(self, communities: Dict) -> List[Dict[str, Any]]:
        """Map fraud communities that span multiple NYC boroughs.

        Cross-borough clusters suggest organized fraud rings operating
        across geographic boundaries to evade local oversight.
        """
        nyc_boroughs = {"manhattan", "brooklyn", "queens", "bronx", "staten island"}
        if not communities:
            return []

        community_groups: Dict[int, List[int]] = defaultdict(list)
        for node_id, comm_id in communities.items():
            community_groups[comm_id].append(node_id)

        cross_borough = []
        for comm_id, nodes in community_groups.items():
            if len(nodes) < 3:
                continue
            boroughs_found = set()
            for n in nodes:
                addr = self.graph.nodes[n].get('address', '').lower()
                node_type = self.graph.nodes[n].get('type', '').lower()
                for borough in nyc_boroughs:
                    if borough in addr or borough in node_type:
                        boroughs_found.add(borough.title())
            if len(boroughs_found) >= 2:
                cross_borough.append({
                    'community_id': int(comm_id),
                    'size': len(nodes),
                    'boroughs': sorted(boroughs_found),
                    'borough_count': len(boroughs_found),
                    'providers': [
                        {
                            'id': int(n),
                            'name': self.graph.nodes[n].get('name', f'Provider {n}'),
                        }
                        for n in nodes[:20]
                    ],
                })

        cross_borough.sort(key=lambda x: x['borough_count'], reverse=True)
        return cross_borough[:20]
    
    def _get_providers(self) -> List[Dict]:
        """Get providers from database with aggregate stats."""
        from sqlalchemy import func
        from models import Provider, Claim

        # Get top providers by claim count to keep graph manageable
        results = self.db.query(
            Provider.id,
            Provider.name,
            Provider.facility_type,
            Provider.npi,
            Provider.address,
            Provider.licensed_capacity,
            func.count(Claim.id).label('total_claims')
        ).join(Claim, Provider.id == Claim.provider_id, isouter=True) \
        .group_by(Provider.id) \
        .order_by(func.count(Claim.id).desc()) \
        .limit(200) \
        .all()

        return [
            {
                'id': r.id,
                'name': r.name,
                'facility_type': r.facility_type or 'Unknown',
                'npi': r.npi,
                'address': r.address or '',
                'licensed_capacity': r.licensed_capacity or 0,
                'total_claims': r.total_claims,
                'risk_score': 0  # To be calculated by risk engine if available
            }
            for r in results
        ]

    def _get_shared_beneficiaries(self, cutoff_date, min_shared) -> List[Dict]:
        """Get shared beneficiary data from actual claims."""
        from sqlalchemy import text
        
        sql = text("""
            SELECT 
                c1.provider_id as provider_a, 
                c2.provider_id as provider_b, 
                COUNT(DISTINCT c1.beneficiary_id) as shared_patients,
                COUNT(c1.id) + COUNT(c2.id) as total_claims
            FROM claims c1
            JOIN claims c2 ON c1.beneficiary_id = c2.beneficiary_id
            WHERE c1.provider_id < c2.provider_id
            AND c1.claim_date >= :cutoff
            AND c2.claim_date >= :cutoff
            GROUP BY c1.provider_id, c2.provider_id
            HAVING COUNT(DISTINCT c1.beneficiary_id) >= :min_shared
            ORDER BY shared_patients DESC
            LIMIT 500;
        """)
        
        results = self.db.execute(sql, {
            "cutoff": cutoff_date,
            "min_shared": min_shared
        }).fetchall()
        
        return [dict(row._mapping) for row in results]

    def _get_referrals(self, cutoff_date) -> List[Dict]:
        """Get referral relationships from database (if available)."""
        # Since we don't have a dedicated referral table, we can infer referrals
        # from shared patients where one provider is a 'Prescriber' and another is a 'Pharmacy/Facility'
        # Or look for patterns in the claims data.
        # For now, returning empty to avoid mock data.
        return []

    def _get_provider_beneficiary_relationships(self) -> Dict[int, List[int]]:
        """Get mapping of providers to their beneficiaries."""
        from sqlalchemy import text
        
        sql = text("""
            SELECT provider_id, beneficiary_id
            FROM claims
            WHERE beneficiary_id IS NOT NULL
            LIMIT 10000;
        """)
        
        results = self.db.execute(sql).fetchall()
        mapping = {}
        for row in results:
            pid = row.provider_id
            bid = row.beneficiary_id
            if pid not in mapping:
                mapping[pid] = []
            mapping[pid].append(bid)
        return mapping

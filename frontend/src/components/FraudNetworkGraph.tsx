import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import './FraudNetworkGraph.css';

import { graphApi } from '../services/api';

interface Node extends d3.SimulationNodeDatum {
  id: number | string;
  name: string;
  type: string;
  risk_score?: number;
  capacity?: number;
  npi?: string;
  x?: number;
  y?: number;
}

interface Edge {
  source: number | string | Node;
  target: number | string | Node;
  weight: number;
  claims?: number;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

interface FraudNetworkGraphProps {
  providerId?: number;
  data?: GraphData;
  onNodeClick?: (node: Node) => void;
}

export const FraudNetworkGraph: React.FC<FraudNetworkGraphProps> = ({ 
  providerId, 
  data: externalData,
  onNodeClick 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(false);
  const [depth, setDepth] = useState(2);
  const [showRiskColors, setShowRiskColors] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const simulationRef = useRef<d3.Simulation<Node, Edge> | null>(null);

  const fetchNetwork = useCallback(async () => {
    if (!providerId) return;
    setLoading(true);
    try {
      const data = await graphApi.getProviderNetwork(providerId, depth);
      setGraphData(data);
    } catch (error) {
      console.error('Failed to fetch network:', error);
    } finally {
      setLoading(false);
    }
  }, [providerId, depth]);

  const fetchFullNetwork = useCallback(async () => {
    setLoading(true);
    try {
      const rings = await graphApi.getFraudRings(50);
      
      // Transform rings into graph data
      const nodes = new Map<number, Node>();
      const edges: Edge[] = [];
      
      if (Array.isArray(rings)) {
        rings.forEach((ring: any) => {
          if (ring.providers && Array.isArray(ring.providers)) {
            ring.providers.forEach((p: any) => {
              if (!nodes.has(p.id)) {
                nodes.set(p.id, {
                  id: p.id,
                  name: p.name,
                  type: p.type,
                  risk_score: p.risk_score
                });
              }
            });
            
            // Add edges between all providers in ring (complete graph)
            for (let i = 0; i < ring.providers.length; i++) {
              for (let j = i + 1; j < ring.providers.length; j++) {
                edges.push({
                  source: ring.providers[i].id,
                  target: ring.providers[j].id,
                  weight: ring.density * 10
                });
              }
            }
          }
        });
      }
      
      setGraphData({
        nodes: Array.from(nodes.values()),
        edges: edges
      });
    } catch (error) {
      console.error('Failed to fetch fraud rings:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch network data
  useEffect(() => {
    if (externalData) {
      setGraphData(externalData);
    } else if (providerId) {
      fetchNetwork();
    } else {
      fetchFullNetwork();
    }
  }, [providerId, depth, externalData, fetchNetwork, fetchFullNetwork]);

  // D3 visualization
  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    // Ensure nodes and edges are arrays
    const nodes = Array.isArray(graphData.nodes) ? graphData.nodes : [];
    const edges = Array.isArray(graphData.edges) ? graphData.edges : [];

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = Math.max(600, containerRef.current.clientHeight || 600);
    const width = Math.max(300, containerWidth);
    const height = containerHeight;

    svg.attr('width', width).attr('height', height);

    // Create zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString());
      });

    svg.call(zoom);

    const g = svg.append('g');

    // Create force simulation
    const simulation = d3.forceSimulation<Node>(nodes)
      .force('link', d3.forceLink<Node, Edge>(edges)
        .id(d => d.id)
        .distance(d => 100 + (1 / (d.weight + 0.1)) * 50))
      .force('charge', d3.forceManyBody<Node>().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<Node>().radius(d => 20 + ((d.risk_score || 0) / 10)));

    simulationRef.current = simulation;

    // Define color scales
    const getRiskColor = (risk: number | undefined) => {
      if (!showRiskColors) return '#4A90E2';
      const score = risk || 0;
      if (score >= 85) return '#E74C3C';
      if (score >= 70) return '#E67E22';
      if (score >= 50) return '#F39C12';
      if (score >= 30) return '#52B788';
      return '#27AE60';
    };

    // Draw edges with gradient
    const defs = svg.append('defs');
    
    edges.forEach((_, i) => {
      const gradient = defs.append('linearGradient')
        .attr('id', `edge-gradient-${i}`)
        .attr('gradientUnits', 'userSpaceOnUse');
      
      gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#95A5A6')
        .attr('stop-opacity', 0.6);
      
      gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#BDC3C7')
        .attr('stop-opacity', 0.3);
    });

    // Draw edges
    const link = g.append('g')
      .selectAll<SVGLineElement, Edge>('line')
      .data(edges)
      .enter()
      .append('line')
      .attr('stroke', (d: any, i) => `url(#edge-gradient-${i})`)
      .attr('stroke-width', d => Math.sqrt(d.weight) * 1.5)
      .attr('stroke-linecap', 'round')
      .style('transition', 'all 0.3s ease');

    // Node groups
    const nodeGroup = g.append('g')
      .selectAll<SVGGElement, Node>('g')
      .data(graphData.nodes)
      .enter()
      .append('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer')
      .call(d3.drag<SVGGElement, Node>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    // Node outer glow
    nodeGroup.append('circle')
      .attr('class', 'node-glow')
      .attr('r', d => 15 + ((d.risk_score || 0) / 8))
      .attr('fill', d => getRiskColor(d.risk_score))
      .attr('opacity', 0.2)
      .style('filter', 'blur(8px)');

    // Node circle
    nodeGroup.append('circle')
      .attr('class', 'node')
      .attr('r', d => 12 + ((d.risk_score || 0) / 10))
      .attr('fill', d => getRiskColor(d.risk_score))
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2.5)
      .style('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))');

    // Risk indicator ring
    nodeGroup.each(function(d) {
      if ((d.risk_score || 0) >= 70) {
        d3.select(this).append('circle')
          .attr('class', 'risk-ring')
          .attr('r', 12 + ((d.risk_score || 0) / 10) + 4)
          .attr('fill', 'none')
          .attr('stroke', '#E74C3C')
          .attr('stroke-width', 2)
          .attr('stroke-dasharray', '4,4')
          .style('animation', 'pulse 2s ease-in-out infinite');
      }
    });

    // Node labels
    nodeGroup.append('text')
      .attr('class', 'node-label')
      .attr('dy', d => 20 + ((d.risk_score || 0) / 10))
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('font-weight', '600')
      .attr('fill', '#2C3E50')
      .attr('paint-order', 'stroke')
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 3)
      .attr('stroke-linejoin', 'round')
      .text(d => {
        const name = String(d.name || 'Node');
        return name.substring(0, 20) + (name.length > 20 ? '...' : '');
      })
      .style('pointer-events', 'none')
      .style('opacity', 0.9);

    // Hover effects
    nodeGroup
      .on('mouseenter', (event, d) => {
        setHoveredNode(d);
        
        d3.select(event.currentTarget).select('.node')
          .transition()
          .duration(200)
          .attr('r', (d: any) => 16 + ((d.risk_score || 0) / 10))
          .attr('stroke-width', 3.5);
        
        d3.select(event.currentTarget).select('.node-glow')
          .transition()
          .duration(200)
          .attr('opacity', 0.4);
        
        // Highlight connected edges
        link
          .transition()
          .duration(200)
          .attr('stroke-opacity', (l: any) => {
            const source = typeof l.source === 'object' ? l.source.id : l.source;
            const target = typeof l.target === 'object' ? l.target.id : l.target;
            return (source === d.id || target === d.id) ? 1 : 0.15;
          })
          .attr('stroke-width', (l: any) => {
            const source = typeof l.source === 'object' ? l.source.id : l.source;
            const target = typeof l.target === 'object' ? l.target.id : l.target;
            return (source === d.id || target === d.id) ? Math.sqrt(l.weight) * 2.5 : Math.sqrt(l.weight) * 1.5;
          });
      })
      .on('mouseleave', function() {
        setHoveredNode(null);
        
        d3.select(this).select('.node')
          .transition()
          .duration(200)
          .attr('r', (d: any) => 12 + (d.risk_score / 10))
          .attr('stroke-width', 2.5);
        
        d3.select(this).select('.node-glow')
          .transition()
          .duration(200)
          .attr('opacity', 0.2);
        
        link
          .transition()
          .duration(200)
          .attr('stroke-opacity', 1)
          .attr('stroke-width', (d: any) => Math.sqrt(d.weight) * 1.5);
      })
      .on('click', (event, d) => {
        event.stopPropagation();
        setSelectedNode(d);
        setDrawerOpen(true);
        if (onNodeClick) onNodeClick(d);
      });

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);

      nodeGroup.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [graphData, showRiskColors, onNodeClick]);

  const handleZoomIn = () => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 1.3);
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 0.7);
    }
  };

  const handleReset = () => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      svg.transition().call(
        d3.zoom<SVGSVGElement, unknown>().transform as any, 
        d3.zoomIdentity
      );
    }
    if (simulationRef.current) {
      simulationRef.current.alpha(1).restart();
    }
  };

  return (
    <div className="fraud-network-container">
      <div className="graph-header">
        <div className="header-left">
          <h2 className="graph-title">
            <span className="title-icon">🕸️</span>
            Fraud Network Analysis
          </h2>
          {providerId && <span className="provider-badge">Provider {providerId}</span>}
        </div>
        
        <div className="header-controls">
          <button className="control-btn" onClick={handleZoomIn} title="Zoom In">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>
          <button className="control-btn" onClick={handleZoomOut} title="Zoom Out">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>
          <button className="control-btn" onClick={handleReset} title="Reset View">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
          </button>
          <button 
            className="control-btn" 
            onClick={providerId ? fetchNetwork : fetchFullNetwork}
            disabled={loading}
            title="Refresh"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
            </svg>
          </button>
        </div>
      </div>

      <div className="graph-controls">
        {providerId && (
          <div className="control-group">
            <label className="control-label">
              Network Depth: <span className="control-value">{depth}</span>
            </label>
            <input
              type="range"
              min="1"
              max="4"
              value={depth}
              onChange={(e) => setDepth(parseInt(e.target.value))}
              className="depth-slider"
            />
          </div>
        )}
        
        <div className="control-group">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showRiskColors}
              onChange={(e) => setShowRiskColors(e.target.checked)}
              className="toggle-input"
            />
            <span className="toggle-slider"></span>
            <span className="toggle-text">Color by Risk Score</span>
          </label>
        </div>
      </div>

      <div className="graph-wrapper" ref={containerRef}>
        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Analyzing network...</p>
          </div>
        )}
        <svg ref={svgRef} className="network-svg"></svg>
        
        {hoveredNode && (
          <div className="node-tooltip">
            <div className="tooltip-header">{hoveredNode.name}</div>
            <div className="tooltip-content">
              <div className="tooltip-row">
                <span className="tooltip-label">Type:</span>
                <span className="tooltip-value">{hoveredNode.type}</span>
              </div>
              <div className="tooltip-row">
                <span className="tooltip-label">Risk Score:</span>
                <span className={`tooltip-value risk-${(hoveredNode.risk_score || 0) >= 70 ? 'high' : (hoveredNode.risk_score || 0) >= 40 ? 'medium' : 'low'}`}>
                  {hoveredNode.risk_score ?? 'N/A'}
                </span>
              </div>
              {hoveredNode.npi && (
                <div className="tooltip-row">
                  <span className="tooltip-label">NPI:</span>
                  <span className="tooltip-value">{hoveredNode.npi}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Side Drawer */}
      {drawerOpen && selectedNode && (
        <>
          <div className="drawer-overlay" onClick={() => setDrawerOpen(false)}></div>
          <div className="drawer">
            <div className="drawer-header">
              <h3>Provider Details</h3>
              <button className="drawer-close" onClick={() => setDrawerOpen(false)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="drawer-content">
              <div className="detail-section">
                <h4>Basic Information</h4>
                <div className="detail-item">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{selectedNode.name}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Type</span>
                  <span className="detail-value">{selectedNode.type}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">NPI</span>
                  <span className="detail-value">{selectedNode.npi || 'N/A'}</span>
                </div>
                {selectedNode.capacity && (
                  <div className="detail-item">
                    <span className="detail-label">Licensed Capacity</span>
                    <span className="detail-value">{selectedNode.capacity}</span>
                  </div>
                )}
              </div>
              
              <div className="detail-section">
                <h4>Risk Assessment</h4>
                <div className="risk-meter">
                  <div className="risk-bar">
                    <div 
                      className="risk-fill" 
                      style={{
                        width: `${selectedNode.risk_score || 0}%`,
                        backgroundColor: (selectedNode.risk_score || 0) >= 70 ? '#E74C3C' : 
                                       (selectedNode.risk_score || 0) >= 40 ? '#F39C12' : '#27AE60'
                      }}
                    ></div>
                  </div>
                  <span className="risk-score-label">{selectedNode.risk_score ?? 'N/A'}/100</span>
                </div>
                <div className="risk-level">
                  Status: <span className={`risk-badge risk-${(selectedNode.risk_score || 0) >= 70 ? 'high' : (selectedNode.risk_score || 0) >= 40 ? 'medium' : 'low'}`}>
                    {(selectedNode.risk_score || 0) >= 70 ? 'High Risk' : (selectedNode.risk_score || 0) >= 40 ? 'Medium Risk' : 'Low Risk'}
                  </span>
                </div>
                <div className="detail-item" style={{ marginTop: '12px' }}>
                  <span className="detail-label">Connections</span>
                  <span className="detail-value">{graphData?.edges.filter(e => {
                    const s = typeof e.source === 'object' ? (e.source as Node).id : e.source;
                    const t = typeof e.target === 'object' ? (e.target as Node).id : e.target;
                    return s === selectedNode.id || t === selectedNode.id;
                  }).length}</span>
                </div>
              </div>
              
              <button 
                className="view-full-btn"
                onClick={() => window.open(`/providers/${selectedNode.id}`, '_blank')}
              >
                View Full Analysis →
              </button>
            </div>
          </div>
        </>
      )}

      <div className="legend">
        <div className="legend-title">Risk Levels</div>
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#27AE60'}}></div>
            <span>Low (0-30)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#52B788'}}></div>
            <span>Low-Med (30-50)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#F39C12'}}></div>
            <span>Medium (50-70)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#E67E22'}}></div>
            <span>High (70-85)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{backgroundColor: '#E74C3C'}}></div>
            <span>Critical (85+)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FraudNetworkGraph;

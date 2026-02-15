import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node extends d3.SimulationNodeDatum {
  id: number;
  name: string;
  type: string;
  risk_score: number;
  x?: number;
  y?: number;
}

interface Edge {
  source: number | Node;
  target: number | Node;
  weight: number;
}

interface CanvasGraphProps {
  data: {
    nodes: any[];
    edges: any[];
  };
}

export const CanvasGraph: React.FC<CanvasGraphProps> = ({ data }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;
    
    // Set canvas dimensions to match container
    const width = canvas.parentElement?.clientWidth || 800;
    const height = 600;
    canvas.width = width;
    canvas.height = height;

    // Create a copy of nodes and edges to avoid mutating props
    const nodes = data.nodes.map(d => ({ ...d }));
    const edges = data.edges.map(d => ({ ...d }));

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(20));

    simulation.on('tick', () => {
      context.clearRect(0, 0, width, height);
      
      // Draw Edges
      context.lineWidth = 1;
      edges.forEach((edge: any) => {
        const source = edge.source;
        const target = edge.target;
        if (source.x && source.y && target.x && target.y) {
            context.beginPath();
            context.moveTo(source.x, source.y);
            context.lineTo(target.x, target.y);
            context.strokeStyle = `rgba(189, 195, 199, ${0.3 + (edge.weight * 0.1)})`;
            context.stroke();
        }
      });

      // Draw Nodes
      nodes.forEach((node: any) => {
        if (!node.x || !node.y) return;
        
        context.beginPath();
        const radius = 5 + (node.risk_score / 15);
        context.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        
        // Color based on risk
        if (node.type === 'Transportation' || node.type === 'Ambulette') {
            context.fillStyle = '#F1C40F';
        } else if (node.risk_score >= 85) {
            context.fillStyle = '#E74C3C';
        } else if (node.risk_score >= 70) {
            context.fillStyle = '#E67E22';
        } else if (node.risk_score >= 50) {
            context.fillStyle = '#F39C12';
        } else {
            context.fillStyle = '#27AE60';
        }
        
        context.fill();
        context.strokeStyle = '#fff';
        context.lineWidth = 1.5;
        context.stroke();
        
        // Draw Label if high risk
        if (node.risk_score > 80) {
            context.fillStyle = '#333';
            context.font = '10px Arial';
            context.fillText(node.name, node.x + 10, node.y + 3);
        }
      });
    });

    return () => {
      simulation.stop();
    };
  }, [data]);

  return (
    <div style={{ width: '100%', height: '600px', position: 'relative' }}>
      <canvas 
        ref={canvasRef} 
        style={{ width: '100%', height: '100%' }}
      />
      <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(0,0,0,0.7)', color: 'white', padding: '5px 10px', borderRadius: '4px', fontSize: '12px' }}>
        Canvas Mode ({data.nodes.length} Nodes)
      </div>
    </div>
  );
};

import React, { useEffect, useState, useCallback } from 'react';
import { FraudNetworkGraph } from '../components/FraudNetworkGraph';
import { graphApi } from '../services/api';
import './FraudRings.css';

interface FraudRing {
  community_id: number;
  size: number;
  density: number;
  avg_risk_score: number;
  max_risk_score: number;
  reciprocity: number;
  triangles: number;
  total_claims: number;
  fraud_score: number;
  suspicion_level: string;
  providers: Array<{
    id: number;
    name: string;
    type: string;
    risk_score: number;
    npi: string;
  }>;
  detection_patterns: string[];
}

interface NetworkStats {
  total_providers: number;
  total_connections: number;
  network_density: number;
  num_communities: number;
  fraud_rings: FraudRing[];
  kickback_cycles: any[];
  beneficiary_concentration: any[];
}

export const FraudRingsPage: React.FC = () => {
  const [rings, setRings] = useState<FraudRing[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRing, setSelectedRing] = useState<FraudRing | null>(null);
  const [stats, setStats] = useState<NetworkStats | null>(null);
  const [minScore, setMinScore] = useState(50);
  const [sortBy, setSortBy] = useState<'fraud_score' | 'size' | 'density'>('fraud_score');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ringsData, statsData] = await Promise.all([
        graphApi.getFraudRings(minScore),
        graphApi.getNetworkStats()
      ]);

      setRings(ringsData || []);
      setStats(statsData || null);
    } catch (error) {
      console.error('Failed to fetch fraud rings:', error);
    } finally {
      setLoading(false);
    }
  }, [minScore]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const sortedRings = [...rings].sort((a, b) => {
    if (sortBy === 'fraud_score') return b.fraud_score - a.fraud_score;
    if (sortBy === 'size') return b.size - a.size;
    if (sortBy === 'density') return b.density - a.density;
    return 0;
  });

  const getSuspicionColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return '#C0392B';
      case 'HIGH': return '#E67E22';
      case 'MEDIUM': return '#F39C12';
      default: return '#27AE60';
    }
  };

  if (loading && !rings.length) {
    return (
      <div className="fraud-rings-page">
        <div className="loading-container">
          <div className="loading-spinner-large"></div>
          <h3>Analyzing Provider Networks...</h3>
          <p>Running graph algorithms to detect fraud patterns</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fraud-rings-page">
      {/* Header */}
      <div className="page-header">
        <div className="header-content">
          <h1 className="page-title">
            <span className="title-icon">🔍</span>
            Fraud Ring Detection
          </h1>
          <p className="page-subtitle">
            Advanced graph analytics powered by community detection and network analysis
          </p>
        </div>
        
        <button className="refresh-btn" onClick={fetchData} disabled={loading}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
          </svg>
          {loading ? 'Analyzing...' : 'Refresh Analysis'}
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon" style={{background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <div className="stat-content">
              <div className="stat-value">{stats.total_providers.toLocaleString()}</div>
              <div className="stat-label">Providers Analyzed</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
            <div className="stat-content">
              <div className="stat-value">{stats.total_connections.toLocaleString()}</div>
              <div className="stat-label">Network Connections</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'}}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
              </svg>
            </div>
            <div className="stat-content">
              <div className="stat-value">{rings.length}</div>
              <div className="stat-label">Fraud Rings Detected</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'}}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <div className="stat-content">
              <div className="stat-value">{(stats.network_density * 100).toFixed(2)}%</div>
              <div className="stat-label">Network Density</div>
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="controls-panel">
        <div className="control-item">
          <label className="control-label">
            Minimum Fraud Score: <strong>{minScore}</strong>
          </label>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={minScore}
            onChange={(e) => setMinScore(parseInt(e.target.value))}
            className="score-slider"
          />
        </div>

        <div className="control-item">
          <label className="control-label">Sort By:</label>
          <div className="sort-buttons">
            <button
              className={`sort-btn ${sortBy === 'fraud_score' ? 'active' : ''}`}
              onClick={() => setSortBy('fraud_score')}
            >
              Fraud Score
            </button>
            <button
              className={`sort-btn ${sortBy === 'size' ? 'active' : ''}`}
              onClick={() => setSortBy('size')}
            >
              Ring Size
            </button>
            <button
              className={`sort-btn ${sortBy === 'density' ? 'active' : ''}`}
              onClick={() => setSortBy('density')}
            >
              Density
            </button>
          </div>
        </div>
      </div>

      {/* Rings Table */}
      <div className="rings-section">
        <div className="section-header">
          <h2>Detected Fraud Rings</h2>
          <span className="ring-count">{sortedRings.length} rings found</span>
        </div>

        {sortedRings.length === 0 ? (
          <div className="empty-state">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4"/>
              <path d="M12 8h.01"/>
            </svg>
            <h3>No Fraud Rings Detected</h3>
            <p>Try adjusting the minimum score threshold to see more results</p>
          </div>
        ) : (
          <div className="rings-grid">
            {sortedRings.map((ring) => (
              <div
                key={ring.community_id}
                className="ring-card"
                onClick={() => setSelectedRing(ring)}
                style={{borderLeftColor: getSuspicionColor(ring.suspicion_level)}}
              >
                <div className="ring-card-header">
                  <div className="ring-id">Ring #{ring.community_id}</div>
                  <span 
                    className="suspicion-badge"
                    style={{
                      background: `${getSuspicionColor(ring.suspicion_level)}20`,
                      color: getSuspicionColor(ring.suspicion_level)
                    }}
                  >
                    {ring.suspicion_level}
                  </span>
                </div>

                <div className="ring-card-body">
                  <div className="fraud-score-display">
                    <div className="score-circle">
                      <svg width="80" height="80" viewBox="0 0 80 80">
                        <circle
                          cx="40"
                          cy="40"
                          r="34"
                          fill="none"
                          stroke="#E9ECEF"
                          strokeWidth="6"
                        />
                        <circle
                          cx="40"
                          cy="40"
                          r="34"
                          fill="none"
                          stroke={getSuspicionColor(ring.suspicion_level)}
                          strokeWidth="6"
                          strokeDasharray={`${(ring.fraud_score / 100) * 214} 214`}
                          strokeLinecap="round"
                          transform="rotate(-90 40 40)"
                        />
                        <text
                          x="40"
                          y="40"
                          textAnchor="middle"
                          dy="7"
                          fontSize="20"
                          fontWeight="700"
                          fill={getSuspicionColor(ring.suspicion_level)}
                        >
                          {Math.round(ring.fraud_score)}
                        </text>
                      </svg>
                    </div>
                    <div className="score-details">
                      <div className="metric">
                        <span className="metric-value">{ring.size}</span>
                        <span className="metric-label">Providers</span>
                      </div>
                      <div className="metric">
                        <span className="metric-value">{ring.triangles}</span>
                        <span className="metric-label">Triangles</span>
                      </div>
                    </div>
                  </div>

                  <div className="ring-metrics">
                    <div className="metric-row">
                      <span className="metric-name">Network Density</span>
                      <span className="metric-number">{(ring.density * 100).toFixed(1)}%</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-name">Avg Risk Score</span>
                      <span className="metric-number">{ring.avg_risk_score.toFixed(1)}</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-name">Reciprocity</span>
                      <span className="metric-number">{(ring.reciprocity * 100).toFixed(1)}%</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-name">Total Claims</span>
                      <span className="metric-number">{ring.total_claims.toLocaleString()}</span>
                    </div>
                  </div>

                  {ring.detection_patterns && ring.detection_patterns.length > 0 && (
                    <div className="patterns">
                      <div className="patterns-label">Detection Patterns:</div>
                      <div className="pattern-tags">
                        {ring.detection_patterns.map((pattern, idx) => (
                          <span key={idx} className="pattern-tag">
                            {pattern.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="providers-list">
                    <div className="providers-header">Providers in Ring:</div>
                    <div className="providers-preview">
                      {ring.providers.slice(0, 3).map((provider) => (
                        <div key={provider.id} className="provider-chip">
                          {provider.name}
                          <span className="provider-risk">{provider.risk_score}</span>
                        </div>
                      ))}
                      {ring.providers.length > 3 && (
                        <div className="provider-chip more">
                          +{ring.providers.length - 3} more
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="ring-card-footer">
                  <button className="view-detail-btn">
                    View Details
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M5 12h14"/>
                      <path d="m12 5 7 7-7 7"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Network Visualization */}
      <div className="visualization-section">
        <h2>Network Visualization</h2>
        <FraudNetworkGraph />
      </div>

      {/* Ring Detail Modal */}
      {selectedRing && (
        <>
          <div className="modal-overlay" onClick={() => setSelectedRing(null)}></div>
          <div className="ring-detail-modal">
            <div className="modal-header">
              <h2>Fraud Ring #{selectedRing.community_id} Details</h2>
              <button className="modal-close" onClick={() => setSelectedRing(null)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-content">
              <div className="modal-section">
                <h3>Ring Statistics</h3>
                <div className="stats-list">
                  <div className="stat-item">
                    <span>Fraud Score</span>
                    <strong style={{color: getSuspicionColor(selectedRing.suspicion_level)}}>
                      {selectedRing.fraud_score.toFixed(2)}
                    </strong>
                  </div>
                  <div className="stat-item">
                    <span>Providers</span>
                    <strong>{selectedRing.size}</strong>
                  </div>
                  <div className="stat-item">
                    <span>Network Density</span>
                    <strong>{(selectedRing.density * 100).toFixed(2)}%</strong>
                  </div>
                  <div className="stat-item">
                    <span>Avg Risk Score</span>
                    <strong>{selectedRing.avg_risk_score.toFixed(1)}</strong>
                  </div>
                  <div className="stat-item">
                    <span>Max Risk Score</span>
                    <strong>{selectedRing.max_risk_score.toFixed(1)}</strong>
                  </div>
                  <div className="stat-item">
                    <span>Triangle Count</span>
                    <strong>{selectedRing.triangles}</strong>
                  </div>
                  <div className="stat-item">
                    <span>Total Claims</span>
                    <strong>{selectedRing.total_claims.toLocaleString()}</strong>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3>Providers in Ring</h3>
                <div className="providers-table">
                  {selectedRing.providers.map((provider) => (
                    <div key={provider.id} className="provider-row">
                      <div className="provider-info">
                        <div className="provider-name">{provider.name}</div>
                        <div className="provider-meta">
                          {provider.type} • NPI: {provider.npi}
                        </div>
                      </div>
                      <div className="provider-risk-badge" style={{
                        background: provider.risk_score >= 70 ? '#FEE' : 
                                  provider.risk_score >= 40 ? '#FFE' : '#EFE',
                        color: provider.risk_score >= 70 ? '#C00' : 
                              provider.risk_score >= 40 ? '#D80' : '#0A0'
                      }}>
                        Risk: {provider.risk_score}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="modal-actions">
                <button className="action-btn primary">
                  Generate Report
                </button>
                <button className="action-btn secondary">
                  Export Data
                </button>
                <button className="action-btn secondary" onClick={() => setSelectedRing(null)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default FraudRingsPage;

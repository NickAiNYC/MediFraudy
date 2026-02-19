import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, ZoomControl } from 'react-leaflet';
import { Box, Typography, Button, Chip, CircularProgress } from '@mui/material';
import { OpenInNew as ExternalLinkIcon, Warning as WarningIcon } from '@mui/icons-material';
import 'leaflet/dist/leaflet.css';

interface Provider {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  riskScore: number;
  exposure: number;
  borough: string;
  violations: number;
}

interface NYCFraudMapProps {
  providers: Provider[];
  onProviderClick?: (providerId: string) => void;
  height?: number;
}

export const NYCFraudMap: React.FC<NYCFraudMapProps> = ({ 
  providers, 
  onProviderClick,
  height = 500 
}) => {
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    // Ensure Leaflet is loaded
    const timer = setTimeout(() => setMapReady(true), 100);
    return () => clearTimeout(timer);
  }, []);

  if (!mapReady || providers.length === 0) {
    return (
      <Box sx={{ 
        height, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: '#1e293b',
        borderRadius: 3
      }}>
        <CircularProgress sx={{ color: '#10b981' }} />
      </Box>
    );
  }

  // Calculate bounds for auto-zoom
  const validProviders = providers.filter(p => p.latitude && p.longitude);
  if (validProviders.length === 0) {
    return (
      <Box sx={{ 
        height, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: '#1e293b',
        borderRadius: 3
      }}>
        <Typography sx={{ color: '#64748b' }}>No provider locations available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative', height, borderRadius: 3, overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
      <MapContainer
        center={[40.7128, -74.0060]}
        zoom={11}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />
        <ZoomControl position="topright" />
        
        {validProviders.map(provider => {
          const color = provider.riskScore >= 85 ? '#ef4444' :
                       provider.riskScore >= 70 ? '#f97316' : 
                       provider.riskScore >= 50 ? '#eab308' : '#10b981';
          
          return (
            <CircleMarker
              key={provider.id}
              center={[provider.latitude, provider.longitude]}
              radius={Math.sqrt(provider.riskScore) * 1.2}
              fillColor={color}
              fillOpacity={0.6}
              stroke={true}
              color="#fff"
              weight={2}
              eventHandlers={{
                mouseover: (e) => {
                  e.target.setStyle({ fillOpacity: 0.9, weight: 3 });
                },
                mouseout: (e) => {
                  e.target.setStyle({ fillOpacity: 0.6, weight: 2 });
                }
              }}
            >
              <Popup maxWidth={280} className="custom-popup">
                <Box sx={{ minWidth: 250, p: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography 
                      variant="subtitle2" 
                      sx={{ 
                        fontWeight: 700, 
                        color: '#0f172a',
                        flex: 1,
                        mr: 1
                      }}
                    >
                      {provider.name}
                    </Typography>
                    <Chip
                      label={provider.riskScore}
                      size="small"
                      sx={{
                        bgcolor: color,
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: '0.7rem',
                        fontFamily: '"JetBrains Mono", monospace',
                        minWidth: 40
                      }}
                    />
                  </Box>
                  
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      display: 'block', 
                      color: '#64748b',
                      mb: 1.5
                    }}
                  >
                    {provider.borough || 'NYC'}
                  </Typography>
                  
                  <Box sx={{ bgcolor: '#f8fafc', borderRadius: 1, p: 1, mb: 1.5 }}>
                    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1 }}>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#64748b', display: 'block', fontSize: '0.65rem' }}>
                          Exposure
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#0f172a', fontWeight: 700, fontSize: '0.85rem' }}>
                          ${(provider.exposure / 1000000).toFixed(1)}M
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#64748b', display: 'block', fontSize: '0.65rem' }}>
                          Violations
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#ef4444', fontWeight: 700, fontSize: '0.85rem' }}>
                          {provider.violations || 0}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  
                  {onProviderClick && (
                    <Button
                      size="small"
                      variant="contained"
                      fullWidth
                      onClick={() => onProviderClick(provider.id)}
                      sx={{
                        bgcolor: '#10b981',
                        fontSize: '0.75rem',
                        py: 0.75,
                        fontWeight: 600,
                        textTransform: 'none',
                        '&:hover': { bgcolor: '#059669' }
                      }}
                    >
                      View Full Analysis
                    </Button>
                  )}
                </Box>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      {/* Enhanced Legend */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          bgcolor: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(12px)',
          p: 2,
          borderRadius: 2,
          border: '1px solid #334155',
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5 }}>
          <WarningIcon sx={{ fontSize: '0.9rem', color: '#10b981' }} />
          <Typography variant="caption" sx={{ color: '#f1f5f9', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Risk Level
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 16, height: 16, borderRadius: '50%', bgcolor: '#ef4444', border: '2px solid #fff' }} />
            <Typography variant="caption" sx={{ color: '#f1f5f9', fontSize: '0.7rem', fontFamily: '"JetBrains Mono", monospace' }}>
              Critical (85-100)
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 16, height: 16, borderRadius: '50%', bgcolor: '#f97316', border: '2px solid #fff' }} />
            <Typography variant="caption" sx={{ color: '#f1f5f9', fontSize: '0.7rem', fontFamily: '"JetBrains Mono", monospace' }}>
              High (70-84)
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 16, height: 16, borderRadius: '50%', bgcolor: '#eab308', border: '2px solid #fff' }} />
            <Typography variant="caption" sx={{ color: '#f1f5f9', fontSize: '0.7rem', fontFamily: '"JetBrains Mono", monospace' }}>
              Medium (50-69)
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 16, height: 16, borderRadius: '50%', bgcolor: '#10b981', border: '2px solid #fff' }} />
            <Typography variant="caption" sx={{ color: '#f1f5f9', fontSize: '0.7rem', fontFamily: '"JetBrains Mono", monospace' }}>
              Low (&lt;50)
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Stats Overlay */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          bgcolor: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(12px)',
          px: 2.5,
          py: 1.5,
          borderRadius: 2,
          border: '1px solid #334155',
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mb: 0.5 }}>
          Providers Mapped
        </Typography>
        <Typography variant="h5" sx={{ color: '#f1f5f9', fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
          {validProviders.length}
        </Typography>
      </Box>
    </Box>
  );
};

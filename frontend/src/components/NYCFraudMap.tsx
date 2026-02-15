import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { Box, Typography, Button } from '@mui/material';
import 'leaflet/dist/leaflet.css';

interface MapProvider {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  riskScore: number;
  exposure: number;
  borough: string;
}

interface NYCFraudMapProps {
  providers: MapProvider[];
  onProviderClick?: (providerId: string) => void;
}

const getRiskColor = (score: number): string => {
  if (score >= 85) return '#ef4444';
  if (score >= 70) return '#f97316';
  if (score >= 50) return '#eab308';
  return '#10b981';
};

export const NYCFraudMap: React.FC<NYCFraudMapProps> = ({ providers, onProviderClick }) => {
  return (
    <MapContainer
      center={[40.7128, -74.006]}
      zoom={11}
      style={{ height: '500px', width: '100%', borderRadius: '12px' }}
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
      />

      {providers.map((provider) => {
        const color = getRiskColor(provider.riskScore);
        return (
          <CircleMarker
            key={provider.id}
            center={[provider.latitude, provider.longitude]}
            radius={Math.max(6, Math.sqrt(provider.riskScore) * 1.5)}
            fillColor={color}
            fillOpacity={0.7}
            stroke={true}
            color="#fff"
            weight={2}
          >
            <Popup>
              <Box sx={{ minWidth: 200, p: 0.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5, color: '#0f172a' }}>
                  {provider.name}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', color: '#64748b', mb: 1 }}>
                  {provider.borough}
                </Typography>
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    Risk Score: <strong style={{ color }}>{provider.riskScore}/100</strong>
                  </Typography>
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    Exposure: <strong>${(provider.exposure / 1000000).toFixed(1)}M</strong>
                  </Typography>
                </Box>
                {onProviderClick && (
                  <Button
                    size="small"
                    variant="contained"
                    fullWidth
                    onClick={() => onProviderClick(provider.id)}
                    sx={{
                      bgcolor: '#10b981',
                      fontSize: '0.7rem',
                      py: 0.5,
                      textTransform: 'none',
                      '&:hover': { bgcolor: '#059669' },
                    }}
                  >
                    View Evidence
                  </Button>
                )}
              </Box>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
};

export default NYCFraudMap;

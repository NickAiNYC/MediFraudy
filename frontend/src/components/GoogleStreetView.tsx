import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import {
  OpenInNew as ExternalLinkIcon,
  LocationOn as MapPinIcon,
} from '@mui/icons-material';

interface GoogleStreetViewProps {
  latitude: number;
  longitude: number;
  address: string;
  capacity?: number;
}

declare global {
  interface Window {
    google: any;
    initGoogleMaps: () => void;
  }
}

const GoogleStreetView: React.FC<GoogleStreetViewProps> = ({
  latitude,
  longitude,
  address,
  capacity,
}) => {
  const panoramaRef = useRef<HTMLDivElement>(null);
  const [panoramaAvailable, setPanoramaAvailable] = useState(true);
  const [loading, setLoading] = useState(true);

  const initPanorama = useCallback(() => {
    if (!panoramaRef.current || !window.google) return;

    const streetViewService = new window.google.maps.StreetViewService();
    const position = { lat: latitude, lng: longitude };

    streetViewService.getPanorama(
      { location: position, radius: 50 },
      (data: any, status: string) => {
        if (status === 'OK' && panoramaRef.current) {
          new window.google.maps.StreetViewPanorama(panoramaRef.current, {
            position: position,
            pov: { heading: 34, pitch: 10 },
            zoom: 1,
            addressControl: false,
            linksControl: true,
            panControl: true,
            enableCloseButton: false,
            fullscreenControl: false,
            motionTracking: false,
            motionTrackingControl: false,
          });
          setPanoramaAvailable(true);
        } else {
          setPanoramaAvailable(false);
        }
        setLoading(false);
      }
    );
  }, [latitude, longitude]);

  useEffect(() => {
    const apiKey = process.env.REACT_APP_GOOGLE_MAPS_KEY;

    if (!apiKey) {
      // No API key - show fallback
      setPanoramaAvailable(false);
      setLoading(false);
      return;
    }

    if (!window.google) {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}`;
      script.async = true;
      script.onload = () => initPanorama();
      script.onerror = () => {
        setPanoramaAvailable(false);
        setLoading(false);
      };
      document.head.appendChild(script);
    } else {
      initPanorama();
    }
  }, [initPanorama]);

  if (loading) {
    return (
      <Box
        sx={{
          height: 256,
          bgcolor: '#1e293b',
          borderRadius: 3,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress size={32} sx={{ color: '#10b981' }} />
      </Box>
    );
  }

  if (!panoramaAvailable) {
    return (
      <Box
        sx={{
          height: 256,
          bgcolor: '#1e293b',
          borderRadius: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 3,
        }}
      >
        <MapPinIcon sx={{ fontSize: 48, color: '#475569', mb: 1.5 }} />
        <Typography variant="body2" sx={{ color: '#94a3b8', textAlign: 'center', mb: 2, fontSize: '0.85rem' }}>
          Street View not available at this location
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<ExternalLinkIcon sx={{ fontSize: '0.9rem' }} />}
          onClick={() =>
            window.open(
              `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`,
              '_blank',
              'noopener,noreferrer'
            )
          }
          sx={{
            borderColor: '#334155',
            color: '#94a3b8',
            fontSize: '0.75rem',
            '&:hover': { borderColor: '#10b981', color: '#10b981' },
          }}
        >
          Open in Google Maps
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative' }}>
      <Box
        ref={panoramaRef}
        sx={{
          height: 256,
          borderRadius: 3,
          overflow: 'hidden',
          boxShadow: '0 10px 15px rgba(0,0,0,0.15)',
        }}
      />
      {/* Address overlay */}
      <Box
        sx={{
          position: 'absolute',
          top: 12,
          left: 12,
          bgcolor: 'rgba(0,0,0,0.8)',
          backdropFilter: 'blur(8px)',
          px: 1.5,
          py: 1,
          borderRadius: 2,
          border: '1px solid #334155',
        }}
      >
        <Typography variant="body2" sx={{ color: '#fff', fontSize: '0.75rem', fontWeight: 500 }}>
          {address}
        </Typography>
        <Typography variant="caption" sx={{ color: '#34d399', fontSize: '0.65rem' }}>
          {latitude.toFixed(6)}, {longitude.toFixed(6)}
          {capacity != null && ` • Capacity: ${capacity}`}
        </Typography>
      </Box>
      {/* Full screen button */}
      <Button
        size="small"
        startIcon={<ExternalLinkIcon sx={{ fontSize: '0.8rem' }} />}
        onClick={() =>
          window.open(
            `https://www.google.com/maps/@${latitude},${longitude},3a,75y,90h,90t/data=!3m6!1e1`,
            '_blank',
            'noopener,noreferrer'
          )
        }
        sx={{
          position: 'absolute',
          bottom: 12,
          right: 12,
          bgcolor: 'rgba(15,23,42,0.9)',
          color: '#f1f5f9',
          fontSize: '0.7rem',
          border: '1px solid #334155',
          '&:hover': { bgcolor: 'rgba(15,23,42,1)', borderColor: '#10b981' },
        }}
      >
        Full Screen
      </Button>
    </Box>
  );
};

export default GoogleStreetView;

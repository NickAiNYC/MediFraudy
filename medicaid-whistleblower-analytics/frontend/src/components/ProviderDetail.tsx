import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Divider,
  CircularProgress,
} from '@mui/material';
import { getProvider, compareProvider } from '../services/api';

const ProviderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [provider, setProvider] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const pid = Number(id);
    Promise.all([getProvider(pid), compareProvider(pid)])
      .then(([pRes, cRes]) => {
        setProvider(pRes.data);
        setComparison(cRes.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <CircularProgress />;
  if (!provider) return <Typography>Provider not found</Typography>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {provider.name}
      </Typography>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2">NPI: {provider.npi}</Typography>
          <Typography variant="body2">
            {provider.address}, {provider.city}, {provider.state} {provider.zip_code}
          </Typography>
          <Chip label={provider.facility_type} sx={{ mt: 1 }} />
          {provider.licensed_capacity && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Licensed Capacity: {provider.licensed_capacity}
            </Typography>
          )}
        </CardContent>
      </Card>

      {comparison && (
        <Card>
          <CardContent>
            <Typography variant="h6">Peer Comparison</Typography>
            <Divider sx={{ my: 1 }} />
            <Typography>
              Average billing: ${comparison.provider?.avg_amount?.toFixed(2) ?? 'N/A'}
            </Typography>
            <Typography>
              Peer average: ${comparison.peer_group?.avg_amount?.toFixed(2) ?? 'N/A'}
            </Typography>
            <Typography>
              Z-Score:{' '}
              <strong style={{ color: Math.abs(comparison.z_score ?? 0) > 3 ? 'red' : 'inherit' }}>
                {comparison.z_score?.toFixed(2) ?? 'N/A'}
              </strong>
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default ProviderDetail;

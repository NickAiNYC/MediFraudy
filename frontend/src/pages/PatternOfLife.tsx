import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Box, Paper, TextField, Button, List, ListItem, ListItemText, Chip, Divider, ListItemButton } from '@mui/material';
import PatternOfLifeView from '../components/PatternOfLifeView';
import { polApi } from '../services/api';

const PatternOfLife: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inputProviderId, setInputProviderId] = useState('');
  const [highRiskProviders, setHighRiskProviders] = useState<any[]>([]);

  useEffect(() => {
    if (!id) {
        const fetchHighRisk = async () => {
        try {
            const res = await polApi.getNYCElderlySweep(5);
            if (res.results) {
                setHighRiskProviders(res.results);
            }
        } catch (e) {
            console.error("Failed to load suggestions", e);
        }
        };
        fetchHighRisk();
    }
  }, [id]);

  const handleSearch = () => {
    if (inputProviderId) {
      navigate(`/pattern-of-life/${inputProviderId}`);
    }
  };

  if (id) {
    return (
      <Box sx={{ p: 3 }}>
        <Button onClick={() => navigate('/pattern-of-life')} sx={{ mb: 2 }}>
            Back to Search
        </Button>
        <PatternOfLifeView providerId={parseInt(id)} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, margin: '0 auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
        Pattern-of-Life Forensic Analysis
      </Typography>
      <Paper sx={{ p: 4, mt: 2 }}>
        <Typography variant="h6" gutterBottom>
          Behavioral Anomaly Detection
        </Typography>
        <Typography paragraph color="text.secondary">
          This tool uses the comprehensive pattern analysis engine to detect:
        </Typography>
        <ul>
            <li><strong>Robotic Billing:</strong> Perfect periodicity in claim submission times.</li>
            <li><strong>Capacity Violations:</strong> Billing for more patients than licensed beds or 24-hour days.</li>
            <li><strong>Weekend Spikes:</strong> Abnormal revenue patterns on non-business days.</li>
        </ul>
        
        <Box sx={{ mt: 4, mb: 4, maxWidth: 600 }}>
            <Typography variant="subtitle2" gutterBottom>Analyze Specific Provider</Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                fullWidth
                label="Provider ID (NPI or Internal ID)"
                value={inputProviderId}
                onChange={(e) => setInputProviderId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                size="small"
                />
                <Button 
                variant="contained" 
                onClick={handleSearch}
                disabled={!inputProviderId}
                sx={{ minWidth: 150 }}
                >
                Run Forensics
                </Button>
            </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h6" gutterBottom>
            Detected High-Risk Targets (NYC Sweep)
        </Typography>
        <List>
            {highRiskProviders.map((p: any) => (
                <ListItem 
                    key={p.provider_id} 
                    disablePadding
                    sx={{ border: '1px solid #eee', mb: 1, borderRadius: 1 }}
                >
                    <ListItemButton onClick={() => navigate(`/pattern-of-life/${p.provider_id}`)}>
                        <ListItemText 
                            primary={`Provider #${p.provider_id} - Risk Score: ${p.risk_score}`}
                            secondary={`Violations: ${p.anomalies?.length || 0} detected`}
                        />
                        <Chip label="High Risk" color="error" size="small" />
                    </ListItemButton>
                </ListItem>
            ))}
             {highRiskProviders.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                    No high-risk targets currently flagged in the sweep.
                </Typography>
            )}
        </List>
      </Paper>
    </Box>
  );
};

export default PatternOfLife;

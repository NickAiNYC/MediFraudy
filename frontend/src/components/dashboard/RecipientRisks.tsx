import React from 'react';
import { Card, CardContent, Typography, List, ListItem, ListItemText, Box, Chip } from '@mui/material';
import { Person as PersonIcon, Loop as LoopIcon, Map as MapIcon } from '@mui/icons-material';

interface CardSharer {
    beneficiary_id: string;
    city_count: number;
    cities: string;
    providers: string;
}

interface MedReseller {
    beneficiary_id: string;
    provider_count: number;
    claim_count: number;
    total_cost: number;
}

interface RecipientRisksProps {
    cardSharers: CardSharer[];
    medResellers: MedReseller[];
}

export const RecipientRisks: React.FC<RecipientRisksProps> = ({ cardSharers = [], medResellers = [] }) => {
    const safeCardSharers = Array.isArray(cardSharers) ? cardSharers : [];
    const safeMedResellers = Array.isArray(medResellers) ? medResellers : [];

    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <PersonIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Recipient Fraud Indicators</Typography>
                </Box>
                
                <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
                    <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="error" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                            <MapIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Card Sharing (Impossible Travel)
                        </Typography>
                        <List dense>
                            {safeCardSharers.length === 0 ? (
                                <ListItem><ListItemText primary="No card sharing detected" /></ListItem>
                            ) : (
                                safeCardSharers.slice(0, 5).map((sharer, idx) => (
                                    <ListItem key={idx} alignItems="flex-start">
                                        <ListItemText 
                                            primary={`ID: ${sharer.beneficiary_id}`}
                                            secondary={
                                                <React.Fragment>
                                                    <Typography sx={{ display: 'inline' }} component="span" variant="body2" color="text.primary">
                                                        {sharer.city_count} Cities
                                                    </Typography>
                                                    {` — ${sharer.cities}`}
                                                </React.Fragment>
                                            }
                                        />
                                    </ListItem>
                                ))
                            )}
                        </List>
                    </Box>
                    
                    <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="warning" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                            <LoopIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Medication Reselling (Doctor Shopping)
                        </Typography>
                        <List dense>
                            {safeMedResellers.length === 0 ? (
                                <ListItem><ListItemText primary="No reselling detected" /></ListItem>
                            ) : (
                                safeMedResellers.slice(0, 5).map((reseller, idx) => (
                                    <ListItem key={idx}>
                                        <ListItemText 
                                            primary={`ID: ${reseller.beneficiary_id}`}
                                            secondary={`${reseller.provider_count} Pharmacies | $${reseller.total_cost.toLocaleString()}`}
                                        />
                                    </ListItem>
                                ))
                            )}
                        </List>
                    </Box>
                </Box>
            </CardContent>
        </Card>
    );
};

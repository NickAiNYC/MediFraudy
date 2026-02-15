import React from 'react';
import { Card, CardContent, Typography, List, ListItem, ListItemText, Divider, Box } from '@mui/material';
import { DirectionsCar as CarIcon, ReportProblem as AlertIcon } from '@mui/icons-material';

interface GhostRide {
    provider_id: number;
    provider_name: string;
    suspicious_claim_count: number;
    total_suspicious_amount: number;
}

interface ImpossibleTrip {
    provider_id: number;
    provider_name: string;
    inflated_trips: number;
    avg_inflation: number;
}

interface NEMTRisksProps {
    ghostRides: GhostRide[];
    impossibleTrips: ImpossibleTrip[];
}

export const NEMTRisks: React.FC<NEMTRisksProps> = ({ ghostRides = [], impossibleTrips = [] }) => {
    const safeGhostRides = Array.isArray(ghostRides) ? ghostRides : [];
    const safeImpossibleTrips = Array.isArray(impossibleTrips) ? impossibleTrips : [];

    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CarIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">NEMT Fraud Indicators</Typography>
                </Box>
                
                <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
                    <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="error" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                            <AlertIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Ghost Rides (No Medical Service)
                        </Typography>
                        <List dense>
                            {safeGhostRides.length === 0 ? (
                                <ListItem><ListItemText primary="No ghost rides detected" /></ListItem>
                            ) : (
                                safeGhostRides.slice(0, 5).map((ride, idx) => (
                                    <React.Fragment key={idx}>
                                        <ListItem>
                                            <ListItemText 
                                                primary={ride.provider_name}
                                                secondary={`${ride.suspicious_claim_count} claims | $${ride.total_suspicious_amount.toLocaleString()}`}
                                            />
                                        </ListItem>
                                        <Divider component="li" />
                                    </React.Fragment>
                                ))
                            )}
                        </List>
                    </Box>
                    
                    <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="warning" gutterBottom>
                            Mileage Inflation (Impossible Trips)
                        </Typography>
                        <List dense>
                            {safeImpossibleTrips.length === 0 ? (
                                <ListItem><ListItemText primary="No impossible trips detected" /></ListItem>
                            ) : (
                                safeImpossibleTrips.slice(0, 5).map((trip, idx) => (
                                    <React.Fragment key={idx}>
                                        <ListItem>
                                            <ListItemText 
                                                primary={trip.provider_name}
                                                secondary={`${trip.inflated_trips} trips | +${Math.round(trip.avg_inflation)} miles avg`}
                                            />
                                        </ListItem>
                                        <Divider component="li" />
                                    </React.Fragment>
                                ))
                            )}
                        </List>
                    </Box>
                </Box>
            </CardContent>
        </Card>
    );
};

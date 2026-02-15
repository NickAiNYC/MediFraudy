import React from 'react';
import { 
    Card, 
    CardContent, 
    Typography, 
    Table, 
    TableBody, 
    TableCell, 
    TableContainer, 
    TableHead, 
    TableRow, 
    Chip,
    Box
} from '@mui/material';
import { Business as BusinessIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface FacilityResult {
    provider_id: number;
    npi: string;
    name: string;
    city: string;
    facility_type: string;
    risk_score: number;
    severity: string;
    findings_count: number;
}

interface HighRiskFacilitiesProps {
    facilities: FacilityResult[];
}

export const HighRiskFacilities: React.FC<HighRiskFacilitiesProps> = ({ facilities }) => {
    const navigate = useNavigate();
    const safeFacilities = Array.isArray(facilities) ? facilities : [];

    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <BusinessIcon color="error" sx={{ mr: 1 }} />
                    <Typography variant="h6">High-Risk Facility Alert (NYC Sweep)</Typography>
                </Box>
                
                <TableContainer>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Facility</TableCell>
                                <TableCell>Type</TableCell>
                                <TableCell>City</TableCell>
                                <TableCell align="right">Risk Score</TableCell>
                                <TableCell align="right">Findings</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {safeFacilities.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} align="center">No high-risk facilities detected</TableCell>
                                </TableRow>
                            ) : (
                                safeFacilities.slice(0, 5).map((facility) => (
                                    <TableRow 
                                        key={facility.provider_id} 
                                        hover 
                                        onClick={() => navigate(`/providers/${facility.provider_id}`)}
                                        sx={{ cursor: 'pointer' }}
                                    >
                                        <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                                            {facility.name}
                                        </TableCell>
                                        <TableCell>{facility.facility_type}</TableCell>
                                        <TableCell>{facility.city}</TableCell>
                                        <TableCell align="right">
                                            <Chip 
                                                label={facility.risk_score} 
                                                color={facility.risk_score > 80 ? "error" : "warning"} 
                                                size="small" 
                                            />
                                        </TableCell>
                                        <TableCell align="right">{facility.findings_count}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </CardContent>
        </Card>
    );
};

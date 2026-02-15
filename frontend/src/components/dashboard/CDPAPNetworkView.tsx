import React, { useEffect, useState } from 'react';
import { Card, CardContent, Typography, Box, CircularProgress } from '@mui/material';
import { FraudNetworkGraph } from '../FraudNetworkGraph';
import { cdpapApi } from '../../services/api';

export const CDPAPNetworkView: React.FC = () => {
    const [graphData, setGraphData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await cdpapApi.getNetwork(200);
                
                if (!data || !data.nodes || !Array.isArray(data.nodes)) {
                    console.warn("Invalid CDPAP network data format:", data);
                    setGraphData({ nodes: [], edges: [] });
                    setLoading(false);
                    return;
                }

                // Transform to the format FraudNetworkGraph expects (nodes/edges)
                const nodes = (data.nodes || []).map((n: any) => ({
                    id: n.id,
                    label: n.label,
                    type: n.type,
                    val: n.val || 5
                }));

                const edges = Array.isArray(data.links) 
                    ? data.links.map((l: any) => ({
                        source: l.source,
                        target: l.target,
                        value: l.value || 1
                    }))
                    : [];

                setGraphData({ nodes, edges });
            } catch (error) {
                console.error("Error loading CDPAP network:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) return <CircularProgress />;

    return (
        <Card sx={{ height: 600 }}>
            <CardContent sx={{ height: '100%', p: 0 }}>
                <Box sx={{ p: 2, borderBottom: '1px solid #eee' }}>
                    <Typography variant="h6">CDPAP "Relative Racket" Network</Typography>
                    <Typography variant="body2" color="textSecondary">
                        Visualizing caregivers with exclusive, high-hour relationships.
                    </Typography>
                </Box>
                {graphData && (
                    <Box sx={{ height: 'calc(100% - 80px)' }}>
                        <FraudNetworkGraph 
                            data={graphData} 
                            onNodeClick={(node: any) => console.log(node)} 
                        />
                    </Box>
                )}
            </CardContent>
        </Card>
    );
};

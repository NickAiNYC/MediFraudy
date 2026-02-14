import React, { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { getTrends } from '../services/api';

const TrendChart: React.FC = () => {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getTrends('NY')
      .then(({ data: trends }) => setData(trends))
      .catch(console.error);
  }, []);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Year-over-Year Billing Trends (NY)
      </Typography>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="total" stroke="#1976d2" name="Total Billing" />
          <Line type="monotone" dataKey="claim_count" stroke="#d32f2f" name="Claim Count" />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default TrendChart;

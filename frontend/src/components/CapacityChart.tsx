import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import { motion } from 'framer-motion';

interface CapacityChartProps {
  data: Array<{
    date: string;
    actualCapacity: number;
    violations?: number;
  }>;
  licensedCapacity: number;
}

const CapacityChart: React.FC<CapacityChartProps> = ({ data, licensedCapacity }) => {
  const chartData = useMemo(() => {
    return data.map((d) => {
      const dateObj = new Date(d.date);
      return {
        ...d,
        dateLabel: dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        licensedCapacity: licensedCapacity,
        overCapacity: Math.max(0, d.actualCapacity - licensedCapacity),
      };
    });
  }, [data, licensedCapacity]);

  const violationDays = data.filter((d) => d.actualCapacity > licensedCapacity).length;
  const totalDays = data.length;
  const violationPercent = totalDays > 0 ? ((violationDays / totalDays) * 100).toFixed(1) : '0';

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload[0]) return null;

    const item = payload[0].payload;
    const isViolation = item.actualCapacity > licensedCapacity;

    return (
      <Box
        sx={{
          bgcolor: '#0f172a',
          border: '1px solid #334155',
          p: 1.5,
          borderRadius: 2,
          boxShadow: '0 20px 25px rgba(0,0,0,0.2)',
        }}
      >
        <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600, mb: 1, fontSize: '0.8rem' }}>
          {item.dateLabel}
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 3, mb: 0.5 }}>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>Actual Census:</Typography>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 700,
              fontFamily: '"JetBrains Mono", monospace',
              color: isViolation ? '#f87171' : '#34d399',
            }}
          >
            {item.actualCapacity}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 3, mb: 0.5 }}>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>Licensed:</Typography>
          <Typography
            variant="caption"
            sx={{ fontWeight: 700, fontFamily: '"JetBrains Mono", monospace', color: '#60a5fa' }}
          >
            {item.licensedCapacity}
          </Typography>
        </Box>
        {isViolation && (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 3,
              pt: 0.5,
              mt: 0.5,
              borderTop: '1px solid #334155',
            }}
          >
            <Typography variant="caption" sx={{ color: '#94a3b8' }}>Over Capacity:</Typography>
            <Typography
              variant="caption"
              sx={{ fontWeight: 700, fontFamily: '"JetBrains Mono", monospace', color: '#f87171' }}
            >
              +{item.actualCapacity - licensedCapacity}
            </Typography>
          </Box>
        )}
      </Box>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <Box>
        {/* Stats Banner */}
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 2 }}>
          <Box
            sx={{
              bgcolor: '#1e293b',
              borderRadius: 2,
              p: 2,
            }}
          >
            <Typography variant="caption" sx={{ color: '#94a3b8', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Days
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace' }}>
              {totalDays}
            </Typography>
          </Box>
          <Box
            sx={{
              bgcolor: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.25)',
              borderRadius: 2,
              p: 2,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fca5a5', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Violation Days
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#f87171', fontFamily: '"JetBrains Mono", monospace' }}>
              {violationDays}
            </Typography>
          </Box>
          <Box
            sx={{
              bgcolor: 'rgba(249,115,22,0.08)',
              border: '1px solid rgba(249,115,22,0.25)',
              borderRadius: 2,
              p: 2,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fdba74', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Violation Rate
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#fb923c', fontFamily: '"JetBrains Mono", monospace' }}>
              {violationPercent}%
            </Typography>
          </Box>
        </Box>

        {/* Chart */}
        <Box sx={{ bgcolor: '#1e293b', borderRadius: 3, p: 2 }}>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="gradActualCapacity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="gradOverCapacity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#dc2626" stopOpacity={0.9} />
                  <stop offset="95%" stopColor="#dc2626" stopOpacity={0.2} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

              <XAxis
                dataKey="dateLabel"
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={{ stroke: '#334155' }}
              />

              <YAxis
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={{ stroke: '#334155' }}
                label={{
                  value: 'Patient Census',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fill: '#94a3b8', fontSize: 11 },
                }}
              />

              <Tooltip content={<CustomTooltip />} />

              <Legend
                wrapperStyle={{ paddingTop: '10px', fontSize: '0.75rem', color: '#94a3b8' }}
                iconType="rect"
              />

              {/* Licensed capacity reference line */}
              <ReferenceLine
                y={licensedCapacity}
                stroke="#3b82f6"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: `Licensed: ${licensedCapacity}`,
                  position: 'insideTopRight',
                  fill: '#3b82f6',
                  fontSize: 11,
                  fontWeight: 'bold' as const,
                }}
              />

              {/* Actual capacity area */}
              <Area
                type="monotone"
                dataKey="actualCapacity"
                stroke="#ef4444"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradActualCapacity)"
                name="Actual Census"
              />

              {/* Over capacity highlight */}
              <Area
                type="monotone"
                dataKey="overCapacity"
                stroke="#dc2626"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#gradOverCapacity)"
                name="Over Capacity"
                stackId="over"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </Box>
    </motion.div>
  );
};

export default CapacityChart;

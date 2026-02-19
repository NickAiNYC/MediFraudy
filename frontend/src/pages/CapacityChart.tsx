import React, { useMemo } from 'react';
import { Box, Typography, Card, CardContent, Chip, Alert } from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend
} from 'recharts';
import { format } from 'date-fns';
import { Warning as WarningIcon, TrendingUp as TrendingUpIcon } from '@mui/icons-material';

interface CapacityDataPoint {
  date: string;
  actualCapacity: number;
  violations: number;
}

interface CapacityChartProps {
  data: CapacityDataPoint[];
  licensedCapacity: number;
  providerName?: string;
}

export const CapacityChart: React.FC<CapacityChartProps> = ({ 
  data, 
  licensedCapacity,
  providerName 
}) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    return data.map(d => ({
      ...d,
      date: format(new Date(d.date), 'MMM dd'),
      licensedCapacity,
      overCapacity: Math.max(0, d.actualCapacity - licensedCapacity),
      violationFlag: d.actualCapacity > licensedCapacity ? 1 : 0
    }));
  }, [data, licensedCapacity]);

  const stats = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        totalDays: 0,
        violationDays: 0,
        violationPercent: '0.0',
        maxOverCapacity: 0,
        avgOverCapacity: 0,
        totalExposure: 0
      };
    }

    const violationDays = data.filter(d => d.actualCapacity > licensedCapacity).length;
    const totalDays = data.length;
    const violationPercent = ((violationDays / totalDays) * 100).toFixed(1);
    
    const overCapacityDays = data
      .filter(d => d.actualCapacity > licensedCapacity)
      .map(d => d.actualCapacity - licensedCapacity);
    
    const maxOverCapacity = overCapacityDays.length > 0 ? Math.max(...overCapacityDays) : 0;
    const avgOverCapacity = overCapacityDays.length > 0 
      ? (overCapacityDays.reduce((a, b) => a + b, 0) / overCapacityDays.length).toFixed(1) 
      : 0;
    
    // Estimate exposure: $150 per patient per day over capacity
    const totalExposure = overCapacityDays.reduce((sum, over) => sum + (over * 150), 0);

    return {
      totalDays,
      violationDays,
      violationPercent,
      maxOverCapacity,
      avgOverCapacity,
      totalExposure
    };
  }, [data, licensedCapacity]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.[0]) return null;
    const data = payload[0].payload;
    const isViolation = data.actualCapacity > licensedCapacity;

    return (
      <Box sx={{ 
        bgcolor: '#1e293b', 
        p: 2, 
        borderRadius: 2, 
        border: '1px solid #334155',
        boxShadow: '0 8px 16px rgba(0,0,0,0.4)',
        minWidth: 200
      }}>
        <Typography variant="body2" sx={{ color: '#f1f5f9', fontWeight: 700, mb: 1 }}>
          {data.date}
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
            <Typography variant="caption" sx={{ color: '#94a3b8' }}>Actual:</Typography>
            <Typography variant="caption" sx={{ color: isViolation ? '#ef4444' : '#10b981', fontWeight: 700 }}>
              {data.actualCapacity}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
            <Typography variant="caption" sx={{ color: '#94a3b8' }}>Licensed:</Typography>
            <Typography variant="caption" sx={{ color: '#3b82f6', fontWeight: 700 }}>
              {data.licensedCapacity}
            </Typography>
          </Box>
          {isViolation && (
            <>
              <Box sx={{ borderTop: '1px solid #334155', mt: 0.5, pt: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                  <Typography variant="caption" sx={{ color: '#94a3b8' }}>Over Capacity:</Typography>
                  <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 700 }}>
                    +{data.actualCapacity - licensedCapacity}
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem', display: 'block', mt: 0.5 }}>
                  Est. Violation: ${((data.actualCapacity - licensedCapacity) * 150).toLocaleString()}
                </Typography>
              </Box>
            </>
          )}
        </Box>
      </Box>
    );
  };

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent>
          <Alert severity="info" sx={{ bgcolor: 'rgba(59,130,246,0.1)', color: '#60a5fa' }}>
            No capacity data available for analysis period
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 700, mb: 0.5 }}>
              Capacity Violations Timeline
            </Typography>
            {providerName && (
              <Typography variant="caption" sx={{ color: '#64748b' }}>
                {providerName}
              </Typography>
            )}
          </Box>
          <Chip
            icon={<WarningIcon sx={{ fontSize: '0.85rem' }} />}
            label={`${stats.violationPercent}% Violation Rate`}
            sx={{
              bgcolor: parseFloat(stats.violationPercent) >= 30 ? 'rgba(239,68,68,0.2)' : 'rgba(249,115,22,0.2)',
              color: parseFloat(stats.violationPercent) >= 30 ? '#ef4444' : '#f97316',
              fontWeight: 700,
              border: `1px solid ${parseFloat(stats.violationPercent) >= 30 ? 'rgba(239,68,68,0.3)' : 'rgba(249,115,22,0.3)'}`
            }}
          />
        </Box>
        
        {/* Enhanced Stats Grid */}
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 2, mb: 3 }}>
          <Box sx={{ bgcolor: '#1e293b', p: 2, borderRadius: 2, border: '1px solid #334155' }}>
            <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mb: 0.5, textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
              Analysis Period
            </Typography>
            <Typography variant="h6" sx={{ color: '#f1f5f9', fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              {stats.totalDays}
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem' }}>
              days reviewed
            </Typography>
          </Box>
          
          <Box sx={{ 
            bgcolor: 'rgba(239,68,68,0.1)', 
            p: 2, 
            borderRadius: 2, 
            border: '1px solid rgba(239,68,68,0.3)' 
          }}>
            <Typography variant="caption" sx={{ color: '#f87171', display: 'block', mb: 0.5, textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
              Violation Days
            </Typography>
            <Typography variant="h6" sx={{ color: '#ef4444', fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              {stats.violationDays}
            </Typography>
            <Typography variant="caption" sx={{ color: '#f87171', fontSize: '0.65rem' }}>
              days over capacity
            </Typography>
          </Box>
          
          <Box sx={{ 
            bgcolor: 'rgba(249,115,22,0.1)', 
            p: 2, 
            borderRadius: 2, 
            border: '1px solid rgba(249,115,22,0.3)' 
          }}>
            <Typography variant="caption" sx={{ color: '#fb923c', display: 'block', mb: 0.5, textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
              Max Over Capacity
            </Typography>
            <Typography variant="h6" sx={{ color: '#f97316', fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              +{stats.maxOverCapacity}
            </Typography>
            <Typography variant="caption" sx={{ color: '#fb923c', fontSize: '0.65rem' }}>
              peak violation
            </Typography>
          </Box>

          <Box sx={{ 
            bgcolor: 'rgba(234,179,8,0.1)', 
            p: 2, 
            borderRadius: 2, 
            border: '1px solid rgba(234,179,8,0.3)' 
          }}>
            <Typography variant="caption" sx={{ color: '#fbbf24', display: 'block', mb: 0.5, textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
              Est. Exposure
            </Typography>
            <Typography variant="h6" sx={{ color: '#eab308', fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              ${(stats.totalExposure / 1000).toFixed(0)}K
            </Typography>
            <Typography variant="caption" sx={{ color: '#fbbf24', fontSize: '0.65rem' }}>
              @$150/day
            </Typography>
          </Box>
        </Box>

        {/* Chart */}
        <Box sx={{ bgcolor: '#0f172a', p: 2, borderRadius: 2, border: '1px solid #1e293b' }}>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="actualCapacity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="overCapacity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#dc2626" stopOpacity={0.95}/>
                  <stop offset="95%" stopColor="#dc2626" stopOpacity={0.2}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis 
                dataKey="date" 
                stroke="#64748b" 
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={{ stroke: '#334155' }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis 
                stroke="#64748b" 
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={{ stroke: '#334155' }}
                axisLine={{ stroke: '#334155' }}
                label={{ 
                  value: 'Patient Census', 
                  angle: -90, 
                  position: 'insideLeft',
                  style: { fill: '#94a3b8', fontSize: 11, fontWeight: 600 }
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ 
                  color: '#94a3b8', 
                  fontSize: 12, 
                  paddingTop: 16,
                  fontWeight: 600
                }} 
                iconType="rect"
              />
              <ReferenceLine
                y={licensedCapacity}
                stroke="#3b82f6"
                strokeDasharray="8 4"
                strokeWidth={3}
                label={{ 
                  value: `Licensed Capacity: ${licensedCapacity}`, 
                  position: 'insideTopRight',
                  fill: '#3b82f6', 
                  fontSize: 12,
                  fontWeight: 700,
                  offset: 10
                }}
              />
              <Area
                type="monotone"
                dataKey="actualCapacity"
                stroke="#ef4444"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#actualCapacity)"
                name="Actual Census"
              />
              <Area
                type="monotone"
                dataKey="overCapacity"
                stroke="#dc2626"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#overCapacity)"
                name="Over Capacity"
                stackId="1"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>

        {/* Legal Context */}
        {stats.violationDays > 30 && (
          <Alert 
            severity="warning" 
            icon={<WarningIcon />}
            sx={{ 
              mt: 2, 
              bgcolor: 'rgba(249,115,22,0.1)', 
              color: '#f97316',
              border: '1px solid rgba(249,115,22,0.3)',
              '& .MuiAlert-icon': { color: '#f97316' }
            }}
          >
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Capacity violations detected on {stats.violationDays} days ({stats.violationPercent}% of analysis period)
            </Typography>
            <Typography variant="caption" sx={{ display: 'block', color: '#fb923c' }}>
              Consistent over-capacity billing may indicate systematic false claims violations under 31 U.S.C. § 3729
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

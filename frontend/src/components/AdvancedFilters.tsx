import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Button,
  Chip,
  Stack,
  Grid,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  FilterList,
  Clear,
  ExpandMore,
  ExpandLess,
  Search,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

interface FilterState {
  riskScore: [number, number];
  state: string;
  facilityType: string;
  claimAmount: [number, number];
  dateRange: string;
  fraudType: string[];
}

export const AdvancedFilters: React.FC<{ onApply: (filters: FilterState) => void }> = ({ onApply }) => {
  const [expanded, setExpanded] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    riskScore: [0, 100],
    state: 'all',
    facilityType: 'all',
    claimAmount: [0, 10000000],
    dateRange: 'all',
    fraudType: [],
  });

  const handleApply = () => {
    onApply(filters);
  };

  const handleClear = () => {
    const defaultFilters: FilterState = {
      riskScore: [0, 100],
      state: 'all',
      facilityType: 'all',
      claimAmount: [0, 10000000],
      dateRange: 'all',
      fraudType: [],
    };
    setFilters(defaultFilters);
    onApply(defaultFilters);
  };

  const fraudTypes = [
    'Billing Inflation',
    'Ghost Billing',
    'Kickback Schemes',
    'Capacity Violations',
    'Duplicate Claims',
    'Unbundling',
    'Upcoding',
  ];

  return (
    <Card sx={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', border: '1px solid #334155' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterList sx={{ color: '#10b981' }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Advanced Filters
            </Typography>
          </Box>
          <IconButton onClick={() => setExpanded(!expanded)} size="small">
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
                Risk Score Range
              </Typography>
              <Slider
                value={filters.riskScore}
                onChange={(_, value) => setFilters({ ...filters, riskScore: value as [number, number] })}
                valueLabelDisplay="auto"
                min={0}
                max={100}
                sx={{
                  color: '#10b981',
                  '& .MuiSlider-thumb': {
                    bgcolor: '#10b981',
                  },
                  '& .MuiSlider-track': {
                    bgcolor: '#10b981',
                  },
                }}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  {filters.riskScore[0]}
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  {filters.riskScore[1]}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
                Claim Amount Range ($)
              </Typography>
              <Slider
                value={filters.claimAmount}
                onChange={(_, value) => setFilters({ ...filters, claimAmount: value as [number, number] })}
                valueLabelDisplay="auto"
                min={0}
                max={10000000}
                step={100000}
                valueLabelFormat={(value) => `$${(value / 1000000).toFixed(1)}M`}
                sx={{
                  color: '#3b82f6',
                  '& .MuiSlider-thumb': {
                    bgcolor: '#3b82f6',
                  },
                  '& .MuiSlider-track': {
                    bgcolor: '#3b82f6',
                  },
                }}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  ${(filters.claimAmount[0] / 1000000).toFixed(1)}M
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748b' }}>
                  ${(filters.claimAmount[1] / 1000000).toFixed(1)}M
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>State</InputLabel>
                <Select
                  value={filters.state}
                  label="State"
                  onChange={(e) => setFilters({ ...filters, state: e.target.value })}
                >
                  <MenuItem value="all">All States</MenuItem>
                  <MenuItem value="NY">New York</MenuItem>
                  <MenuItem value="CA">California</MenuItem>
                  <MenuItem value="TX">Texas</MenuItem>
                  <MenuItem value="FL">Florida</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Facility Type</InputLabel>
                <Select
                  value={filters.facilityType}
                  label="Facility Type"
                  onChange={(e) => setFilters({ ...filters, facilityType: e.target.value })}
                >
                  <MenuItem value="all">All Types</MenuItem>
                  <MenuItem value="adult_day_care">Adult Day Care</MenuItem>
                  <MenuItem value="home_health">Home Health</MenuItem>
                  <MenuItem value="transport">Medical Transport</MenuItem>
                  <MenuItem value="dme">DME Supplier</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Date Range</InputLabel>
                <Select
                  value={filters.dateRange}
                  label="Date Range"
                  onChange={(e) => setFilters({ ...filters, dateRange: e.target.value })}
                >
                  <MenuItem value="all">All Time</MenuItem>
                  <MenuItem value="30d">Last 30 Days</MenuItem>
                  <MenuItem value="90d">Last 90 Days</MenuItem>
                  <MenuItem value="1y">Last Year</MenuItem>
                  <MenuItem value="2y">Last 2 Years</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
                Fraud Type
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {fraudTypes.map((type) => (
                  <Chip
                    key={type}
                    label={type}
                    onClick={() => {
                      const newTypes = filters.fraudType.includes(type)
                        ? filters.fraudType.filter((t) => t !== type)
                        : [...filters.fraudType, type];
                      setFilters({ ...filters, fraudType: newTypes });
                    }}
                    sx={{
                      bgcolor: filters.fraudType.includes(type) ? '#10b98140' : '#1e293b',
                      color: filters.fraudType.includes(type) ? '#10b981' : '#94a3b8',
                      border: filters.fraudType.includes(type) ? '1px solid #10b981' : '1px solid #334155',
                      '&:hover': {
                        bgcolor: filters.fraudType.includes(type) ? '#10b98160' : '#334155',
                      },
                    }}
                  />
                ))}
              </Stack>
            </Grid>

            <Grid item xs={12}>
              <Stack direction="row" spacing={2} justifyContent="flex-end">
                <Button
                  variant="outlined"
                  startIcon={<Clear />}
                  onClick={handleClear}
                  sx={{
                    borderColor: '#334155',
                    color: '#94a3b8',
                    '&:hover': {
                      borderColor: '#475569',
                      bgcolor: '#1e293b',
                    },
                  }}
                >
                  Clear All
                </Button>
                <Button
                  variant="contained"
                  startIcon={<Search />}
                  onClick={handleApply}
                  sx={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    fontWeight: 700,
                  }}
                >
                  Apply Filters
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default AdvancedFilters;

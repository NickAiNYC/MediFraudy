import React, { useMemo, useRef, useState } from 'react';
import { Box, Typography, TextField, Button, Chip } from '@mui/material';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { motion } from 'framer-motion';

interface ClaimRow {
  claimId?: string;
  claimDate: string;
  beneficiaryId: string;
  billingCode: string;
  amount: number;
  units?: number;
  aideId?: string;
  violationType?: string;
  isViolation: boolean;
}

interface ClaimsTableProps {
  data: ClaimRow[];
  providerId?: string;
  onBeneficiaryClick?: (beneficiaryId: string) => void;
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const columnHelper = createColumnHelper<ClaimRow>();

export const ClaimsTable: React.FC<ClaimsTableProps> = ({ data, providerId, onBeneficiaryClick }) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const parentRef = useRef<HTMLDivElement>(null);

  const violationCount = useMemo(() => data.filter((d) => d.isViolation).length, [data]);
  const totalAmount = useMemo(() => data.reduce((sum, d) => sum + d.amount, 0), [data]);
  const violationAmount = useMemo(
    () => data.filter((d) => d.isViolation).reduce((sum, d) => sum + d.amount, 0),
    [data]
  );

  const columns = useMemo(
    () => [
      columnHelper.accessor('claimDate', {
        header: 'Date',
        cell: (info) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.8rem',
              color: info.row.original.isViolation ? '#f87171' : '#cbd5e1',
              fontWeight: info.row.original.isViolation ? 700 : 400,
            }}
          >
            {formatDate(info.getValue())}
          </Typography>
        ),
      }),
      columnHelper.accessor('claimId', {
        header: 'Claim ID',
        cell: (info) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.7rem',
              color: '#64748b',
            }}
          >
            {info.getValue() || '—'}
          </Typography>
        ),
      }),
      columnHelper.accessor('beneficiaryId', {
        header: 'Beneficiary',
        cell: (info) => (
          <Typography
            component="button"
            variant="body2"
            onClick={() => onBeneficiaryClick?.(info.getValue())}
            sx={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#60a5fa',
              textDecoration: 'underline',
              fontSize: '0.8rem',
              fontFamily: '"JetBrains Mono", monospace',
              '&:hover': { color: '#93c5fd' },
            }}
          >
            {info.getValue()}
          </Typography>
        ),
      }),
      columnHelper.accessor('aideId', {
        header: 'Aide',
        cell: (info) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.7rem',
              color: '#64748b',
            }}
          >
            {info.getValue() || '—'}
          </Typography>
        ),
      }),
      columnHelper.accessor('billingCode', {
        header: 'Code',
        cell: (info) => (
          <Chip
            label={info.getValue()}
            size="small"
            variant="outlined"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.65rem',
              color: '#cbd5e1',
              borderColor: '#334155',
              height: 22,
            }}
          />
        ),
      }),
      columnHelper.accessor('amount', {
        header: 'Amount',
        cell: (info) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontWeight: 700,
              fontSize: '0.8rem',
              color: info.getValue() > 500 ? '#fbbf24' : '#cbd5e1',
            }}
          >
            ${info.getValue().toFixed(2)}
          </Typography>
        ),
      }),
      columnHelper.accessor('violationType', {
        header: 'Violation',
        cell: (info) => {
          const v = info.getValue();
          if (!v) return <Typography variant="body2" sx={{ color: '#475569' }}>—</Typography>;
          const colorMap: Record<string, { bg: string; text: string }> = {
            EVV_MISSING: { bg: 'rgba(239,68,68,0.15)', text: '#f87171' },
            CAPACITY: { bg: 'rgba(249,115,22,0.15)', text: '#fb923c' },
            IMPOSSIBLE_SCHEDULE: { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24' },
            BENEFICIARY_OVERLAP: { bg: 'rgba(168,85,247,0.15)', text: '#c084fc' },
          };
          const chipColor = colorMap[v] || { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24' };
          return (
            <Chip
              label={v.replace(/_/g, ' ')}
              size="small"
              sx={{
                bgcolor: chipColor.bg,
                color: chipColor.text,
                fontWeight: 700,
                fontSize: '0.6rem',
                height: 22,
                border: `1px solid ${chipColor.text}30`,
              }}
            />
          );
        },
      }),
    ],
    [onBeneficiaryClick]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const { rows } = table.getRowModel();
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 10,
  });

  const handleExport = () => {
    const filteredRows = table.getFilteredRowModel().rows;
    const csvContent = [
      ['Date', 'Claim ID', 'Beneficiary', 'Aide', 'Billing Code', 'Amount', 'Violation'].join(','),
      ...filteredRows.map((row) =>
        [
          row.original.claimDate,
          row.original.claimId || '',
          row.original.beneficiaryId,
          row.original.aideId || '',
          row.original.billingCode,
          row.original.amount,
          row.original.violationType || '',
        ].join(',')
      ),
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `claims_evidence${providerId ? `_${providerId}` : ''}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <Box>
        {/* Summary Stats */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 2, mb: 2 }}>
          <Box sx={{ bgcolor: '#1e293b', borderRadius: 2, p: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Claims
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace' }}>
              {data.length.toLocaleString()}
            </Typography>
          </Box>
          <Box sx={{ bgcolor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 2, p: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#fca5a5', fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Violations
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#f87171', fontFamily: '"JetBrains Mono", monospace' }}>
              {violationCount.toLocaleString()}
            </Typography>
          </Box>
          <Box sx={{ bgcolor: '#1e293b', borderRadius: 2, p: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Amount
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#f1f5f9', fontFamily: '"JetBrains Mono", monospace' }}>
              ${totalAmount >= 1000000 ? `${(totalAmount / 1000000).toFixed(2)}M` : totalAmount.toLocaleString()}
            </Typography>
          </Box>
          <Box sx={{ bgcolor: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: 2, p: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#fdba74', fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Violation Amount
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#fb923c', fontFamily: '"JetBrains Mono", monospace' }}>
              ${violationAmount >= 1000000 ? `${(violationAmount / 1000000).toFixed(2)}M` : violationAmount.toLocaleString()}
            </Typography>
          </Box>
        </Box>

        {/* Toolbar */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
          p: 2,
          bgcolor: '#0f172a',
          borderRadius: 2,
          border: '1px solid #1e293b',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              size="small"
              placeholder="Search claims..."
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              sx={{
                width: 300,
                '& .MuiOutlinedInput-root': {
                  bgcolor: '#1e293b',
                  color: '#f1f5f9',
                  borderRadius: 2,
                  fontSize: '0.85rem',
                  '& fieldset': { borderColor: '#334155' },
                  '&:hover fieldset': { borderColor: '#475569' },
                  '&.Mui-focused fieldset': { borderColor: '#10b981' },
                },
                '& .MuiInputBase-input::placeholder': {
                  color: '#64748b',
                },
              }}
            />
            <Chip
              label={`${rows.length.toLocaleString()} results`}
              size="small"
              sx={{
                bgcolor: 'rgba(148,163,184,0.1)',
                color: '#94a3b8',
                fontSize: '0.65rem',
                fontFamily: '"JetBrains Mono", monospace',
              }}
            />
          </Box>
          <Button
            variant="contained"
            size="small"
            onClick={handleExport}
            sx={{
              bgcolor: '#10b981',
              '&:hover': { bgcolor: '#059669' },
              fontWeight: 600,
              borderRadius: 2,
              fontSize: '0.75rem',
            }}
          >
            Export CSV
          </Button>
        </Box>

        {/* Virtualized Table */}
        <Box
          ref={parentRef}
          sx={{
            height: 500,
            overflow: 'auto',
            bgcolor: '#0f172a',
            borderRadius: 3,
            border: '1px solid #1e293b',
          }}
        >
          <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse' }}>
            <Box component="thead" sx={{ position: 'sticky', top: 0, zIndex: 1, bgcolor: '#1e293b' }}>
              {table.getHeaderGroups().map((headerGroup) => (
                <Box component="tr" key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <Box
                      component="th"
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      sx={{
                        px: 2,
                        py: 1.5,
                        textAlign: 'left',
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        color: '#94a3b8',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        cursor: 'pointer',
                        userSelect: 'none',
                        '&:hover': { color: '#f1f5f9' },
                        borderBottom: '1px solid #334155',
                      }}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === 'asc' ? ' ↑' : header.column.getIsSorted() === 'desc' ? ' ↓' : ''}
                    </Box>
                  ))}
                </Box>
              ))}
            </Box>
            <Box component="tbody">
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                  <Box
                    component="tr"
                    key={row.id}
                    sx={{
                      borderBottom: '1px solid #1e293b',
                      bgcolor: row.original.isViolation ? 'rgba(239,68,68,0.04)' : 'transparent',
                      transition: 'background-color 0.15s ease',
                      '&:hover': { bgcolor: 'rgba(30,41,59,0.5)' },
                      height: virtualRow.size,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <Box component="td" key={cell.id} sx={{ px: 2, py: 1.5 }}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </Box>
                    ))}
                  </Box>
                );
              })}
            </Box>
          </Box>
        </Box>
      </Box>
    </motion.div>
  );
};

export default ClaimsTable;

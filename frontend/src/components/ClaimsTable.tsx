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
  claimDate: string;
  beneficiaryId: string;
  billingCode: string;
  amount: number;
  units: number;
  violationType?: string;
  isViolation: boolean;
}

interface ClaimsTableProps {
  data: ClaimRow[];
  onBeneficiaryClick?: (beneficiaryId: string) => void;
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const columnHelper = createColumnHelper<ClaimRow>();

export const ClaimsTable: React.FC<ClaimsTableProps> = ({ data, onBeneficiaryClick }) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const parentRef = useRef<HTMLDivElement>(null);

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
      columnHelper.accessor('billingCode', {
        header: 'Billing Code',
        cell: (info) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.8rem',
              color: '#cbd5e1',
            }}
          >
            {info.getValue()}
          </Typography>
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
          const chipColor =
            v === 'EVV_MISSING'
              ? { bg: 'rgba(239,68,68,0.15)', text: '#f87171' }
              : v === 'CAPACITY'
              ? { bg: 'rgba(249,115,22,0.15)', text: '#fb923c' }
              : { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24' };
          return (
            <Chip
              label={v.replace(/_/g, ' ')}
              size="small"
              sx={{
                bgcolor: chipColor.bg,
                color: chipColor.text,
                fontWeight: 700,
                fontSize: '0.65rem',
                height: 24,
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
      ['Date', 'Beneficiary', 'Billing Code', 'Amount', 'Violation'].join(','),
      ...filteredRows.map((row) =>
        [
          row.original.claimDate,
          row.original.beneficiaryId,
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
    a.download = 'claims_evidence.csv';
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
        {/* Toolbar */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
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
                '& fieldset': { borderColor: '#334155' },
                '&:hover fieldset': { borderColor: '#475569' },
                '&.Mui-focused fieldset': { borderColor: '#10b981' },
              },
              '& .MuiInputBase-input::placeholder': {
                color: '#64748b',
              },
            }}
          />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" sx={{ color: '#64748b', fontFamily: '"JetBrains Mono", monospace' }}>
              {rows.length.toLocaleString()} rows
            </Typography>
            <Button
              variant="contained"
              size="small"
              onClick={handleExport}
              sx={{
                bgcolor: '#10b981',
                '&:hover': { bgcolor: '#059669' },
                fontWeight: 600,
                borderRadius: 2,
              }}
            >
              Export CSV
            </Button>
          </Box>
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
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color: '#94a3b8',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        cursor: 'pointer',
                        userSelect: 'none',
                        '&:hover': { color: '#f1f5f9' },
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
                      bgcolor: row.original.isViolation ? 'rgba(239,68,68,0.05)' : 'transparent',
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

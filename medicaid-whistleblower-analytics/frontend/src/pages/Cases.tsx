import React, { useEffect, useState } from 'react';
import { Box, Typography, Card, CardContent, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip, IconButton, Tooltip } from '@mui/material';
import { Add as AddIcon, Visibility as ViewIcon, Download as DownloadIcon } from '@mui/icons-material';
import { caseApi } from '../services/api';

const Cases: React.FC = () => {
  const [cases, setCases] = useState([]);
  
  useEffect(() => {
    caseApi.list().then(data => setCases(data.cases || []));
  }, []);
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Whistleblower Cases</Typography>
      {/* Table of cases with status, actions */}
    </Box>
  );
};

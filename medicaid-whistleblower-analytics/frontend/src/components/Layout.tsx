import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  CssBaseline,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import WarningIcon from '@mui/icons-material/Warning';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import GavelIcon from '@mui/icons-material/Gavel';
import ElderlyIcon from '@mui/icons-material/Elderly';

const DRAWER_WIDTH = 240;

const navItems = [
  { text: 'Provider Search', icon: <SearchIcon />, path: '/' },
  { text: 'Anomalies', icon: <WarningIcon />, path: '/anomalies' },
  { text: 'Trends', icon: <TrendingUpIcon />, path: '/trends' },
  { text: 'Cases', icon: <GavelIcon />, path: '/cases' },
  { text: 'Elderly Care', icon: <ElderlyIcon />, path: '/elderly-care' },
];

const Layout: React.FC = () => (
  <Box sx={{ display: 'flex' }}>
    <CssBaseline />
    <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
      <Toolbar>
        <Typography variant="h6" noWrap>
          Medicaid Whistleblower Analytics
        </Typography>
      </Toolbar>
    </AppBar>

    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
      }}
    >
      <Toolbar />
      <List>
        {navItems.map((item) => (
          <ListItemButton key={item.text} component={Link} to={item.path}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>

    <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
      <Toolbar />
      <Outlet />
    </Box>
  </Box>
);

export default Layout;

import React, { useState } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  Badge,
  useMediaQuery,
  useTheme,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Analytics as AnalyticsIcon,
  FolderSpecial as CasesIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Warning as WarningIcon,
  MedicalServices as MedicalIcon,
  GroupWork as GraphIcon,
  Shield as ShieldIcon,
  Assessment as AssessmentIcon,
  Storage as StorageIcon,
  Gavel as GavelIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const drawerWidth = 280;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [notificationsAnchor, setNotificationsAnchor] = useState<null | HTMLElement>(null);
  
  const navigate = useNavigate();
  const location = useLocation();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleNotificationsOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationsAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setNotificationsAnchor(null);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
    handleMenuClose();
  };

  const menuItems = [
    { text: 'Intelligence Overview', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Provider Risk Index', icon: <AssessmentIcon />, path: '/providers' },
    { text: 'Network Graph', icon: <GraphIcon />, path: '/fraud-rings' },
    { text: 'Case Builder', icon: <CasesIcon />, path: '/cases' },
    { text: 'Alerts', icon: <WarningIcon />, path: '/alerts' },
    { text: 'Evidence Vault', icon: <StorageIcon />, path: '/evidence' },
    { text: 'Legal Assistant', icon: <GavelIcon />, path: '/agent' },
    { text: 'Pattern of Life', icon: <AnalyticsIcon />, path: '/pattern-of-life' },
    { text: 'Home Care Intel', icon: <MedicalIcon />, path: '/home-care' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#0f172a' }}>
      {/* Logo */}
      <Toolbar sx={{ 
        justifyContent: 'center', 
        py: 2.5,
        borderBottom: '1px solid #1e293b',
      }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography
            variant="h5"
            sx={{
              fontWeight: 800,
              background: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.025em',
            }}
          >
            MediFraudy
          </Typography>
          <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
            FRAUD INTELLIGENCE PLATFORM
          </Typography>
        </Box>
      </Toolbar>

      {/* Risk Alert Banner */}
      <Box sx={{ 
        mx: 2, 
        mt: 2, 
        p: 1.5, 
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        borderRadius: 2,
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        '&:hover': { 
          borderColor: '#ef4444',
          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(239, 68, 68, 0.1) 100%)',
        },
      }}
      onClick={() => handleNavigation('/dashboard')}
      >
        <WarningIcon sx={{ color: '#f87171', fontSize: '1rem' }} />
        <Typography variant="body2" sx={{ color: '#f87171', fontWeight: 600, fontSize: '0.75rem' }}>
          Live Fraud Alerts Active
        </Typography>
      </Box>

      {/* Navigation Menu */}
      <List sx={{ flex: 1, px: 2, mt: 2 }}>
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                sx={{
                  borderRadius: 2,
                  bgcolor: isActive 
                    ? 'rgba(16, 185, 129, 0.1)' 
                    : 'transparent',
                  border: isActive 
                    ? '1px solid rgba(16, 185, 129, 0.3)' 
                    : '1px solid transparent',
                  color: isActive ? '#10b981' : '#94a3b8',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: isActive 
                      ? 'rgba(16, 185, 129, 0.15)' 
                      : 'rgba(148, 163, 184, 0.05)',
                    color: isActive ? '#34d399' : '#f1f5f9',
                  },
                  '& .MuiListItemIcon-root': {
                    color: isActive ? '#10b981' : '#64748b',
                    minWidth: 40,
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.text}
                  primaryTypographyProps={{ 
                    fontSize: '0.875rem',
                    fontWeight: isActive ? 600 : 400,
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: '1px solid #1e293b' }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 1 }}>
          <Chip
            label="77.3M Claims"
            size="small"
            sx={{
              bgcolor: 'rgba(16, 185, 129, 0.1)',
              color: '#10b981',
              fontWeight: 600,
              fontSize: '0.65rem',
              fontFamily: '"JetBrains Mono", monospace',
              border: '1px solid rgba(16, 185, 129, 0.2)',
            }}
          />
        </Box>
        <Typography variant="caption" sx={{ color: '#475569', display: 'block', textAlign: 'center', fontSize: '0.65rem' }}>
          v1.0.0 • DOGE Dataset Feb 2026
        </Typography>
        <Typography variant="caption" sx={{ color: '#475569', display: 'block', textAlign: 'center', fontSize: '0.65rem' }}>
          Queens $120M • Brooklyn $68M
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#020617' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: '#0f172a',
          color: '#f1f5f9',
          borderBottom: '1px solid #1e293b',
          boxShadow: 'none',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 600, fontSize: '1rem' }}>
            {menuItems.find(item => item.path === location.pathname)?.text || 'Medicaid Analytics'}
          </Typography>

          {/* Claims Badge */}
          <Chip
            label="77.3M Claims Analyzed"
            size="small"
            sx={{
              mr: 2,
              bgcolor: 'rgba(16, 185, 129, 0.1)',
              color: '#10b981',
              fontWeight: 600,
              fontSize: '0.7rem',
              fontFamily: '"JetBrains Mono", monospace',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              display: { xs: 'none', sm: 'flex' },
            }}
          />

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton sx={{ color: '#94a3b8' }} onClick={handleNotificationsOpen}>
              <Badge badgeContent={3} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* User Menu */}
          <Tooltip title="Account">
            <IconButton
              onClick={handleProfileMenuOpen}
              size="small"
              sx={{ ml: 1 }}
            >
              <Avatar sx={{ 
                width: 32, 
                height: 32, 
                bgcolor: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                border: '1px solid rgba(16, 185, 129, 0.3)',
              }}>
                <PersonIcon sx={{ fontSize: '1rem' }} />
              </Avatar>
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationsAnchor}
        open={Boolean(notificationsAnchor)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: { 
            width: 320, 
            maxHeight: 400, 
            p: 2,
            bgcolor: '#1e293b',
            border: '1px solid #334155',
          }
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 1, color: '#f1f5f9', fontWeight: 600 }}>Notifications</Typography>
        <MenuItem onClick={handleMenuClose} sx={{ whiteSpace: 'normal', py: 1.5, borderRadius: 1, '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' } }}>
          <Box>
            <Typography variant="body2" fontWeight={600} sx={{ color: '#f1f5f9' }}>New High-Risk Facility</Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              Sunrise Adult Day Care - Risk Score 94
            </Typography>
          </Box>
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ whiteSpace: 'normal', py: 1.5, borderRadius: 1, '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' } }}>
          <Box>
            <Typography variant="body2" fontWeight={600} sx={{ color: '#f1f5f9' }}>POL Analysis Complete</Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              5 facilities analyzed in Brooklyn
            </Typography>
          </Box>
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ whiteSpace: 'normal', py: 1.5, borderRadius: 1, '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' } }}>
          <Box>
            <Typography variant="body2" fontWeight={600} sx={{ color: '#f1f5f9' }}>Dataset Updated</Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              New claims added through Feb 2026
            </Typography>
          </Box>
        </MenuItem>
      </Menu>

      {/* User Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: { 
            width: 200,
            bgcolor: '#1e293b',
            border: '1px solid #334155',
          }
        }}
      >
        <MenuItem onClick={() => handleNavigation('/profile')} sx={{ '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' } }}>
          <ListItemIcon><PersonIcon fontSize="small" sx={{ color: '#94a3b8' }} /></ListItemIcon>
          <ListItemText primaryTypographyProps={{ color: '#f1f5f9' }}>Profile</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleNavigation('/settings')} sx={{ '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.05)' } }}>
          <ListItemIcon><SettingsIcon fontSize="small" sx={{ color: '#94a3b8' }} /></ListItemIcon>
          <ListItemText primaryTypographyProps={{ color: '#f1f5f9' }}>Settings</ListItemText>
        </MenuItem>
        <Divider sx={{ borderColor: '#334155' }} />
        <MenuItem onClick={handleMenuClose} sx={{ '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.05)' } }}>
          <ListItemIcon><LogoutIcon fontSize="small" sx={{ color: '#f87171' }} /></ListItemIcon>
          <ListItemText primaryTypographyProps={{ color: '#f87171' }}>Logout</ListItemText>
        </MenuItem>
      </Menu>

      {/* Sidebar Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth,
              bgcolor: '#0f172a',
              borderRight: '1px solid #1e293b',
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth,
              bgcolor: '#0f172a',
              borderRight: '1px solid #1e293b',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: '64px',
          bgcolor: '#020617',
          minHeight: 'calc(100vh - 64px)',
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default Layout;

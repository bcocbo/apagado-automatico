import React, { useEffect, useState } from 'react';
import {
  Box,
  Chip,
  Tooltip,
  IconButton,
  Typography,
  Popover,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  CheckCircle as HealthyIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../../services/api';
import { ControllerHealth } from '../../types';

interface HealthCheckProps {
  showDetails?: boolean;
  size?: 'small' | 'medium';
}

const HealthCheck: React.FC<HealthCheckProps> = ({ 
  showDetails = false, 
  size = 'medium' 
}) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [lastCheck, setLastCheck] = useState<Date>(new Date());

  const {
    data: health,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['system-health'],
    queryFn: systemApi.getHealth,
    refetchInterval: 30000, // 30 seconds
    retry: 3,
  });

  useEffect(() => {
    if (health) {
      setLastCheck(new Date());
    }
  }, [health]);

  const getHealthStatus = () => {
    if (isLoading) return { status: 'checking', color: 'info', icon: <InfoIcon /> };
    if (error) return { status: 'error', color: 'error', icon: <ErrorIcon /> };
    if (!health) return { status: 'unknown', color: 'warning', icon: <WarningIcon /> };
    
    switch (health.status) {
      case 'healthy':
        return { status: 'healthy', color: 'success', icon: <HealthyIcon /> };
      case 'unhealthy':
        return { status: 'unhealthy', color: 'error', icon: <ErrorIcon /> };
      default:
        return { status: 'degraded', color: 'warning', icon: <WarningIcon /> };
    }
  };

  const { status, color, icon } = getHealthStatus();

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    if (showDetails) {
      setAnchorEl(event.currentTarget);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleRefresh = (event: React.MouseEvent) => {
    event.stopPropagation();
    refetch();
    setLastCheck(new Date());
  };

  const getComponentStatus = (componentName: string, isHealthy: boolean) => {
    return {
      icon: isHealthy ? <HealthyIcon color="success" /> : <ErrorIcon color="error" />,
      color: isHealthy ? 'success' : 'error',
      text: isHealthy ? 'Healthy' : 'Unhealthy'
    };
  };

  const formatComponentName = (name: string) => {
    return name.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <>
      <Box display="flex" alignItems="center" gap={1}>
        <Tooltip title={`System ${status} - Click for details`}>
          <Chip
            icon={icon}
            label={status.toUpperCase()}
            color={color as any}
            size={size}
            variant="outlined"
            onClick={handleClick}
            sx={{ 
              cursor: showDetails ? 'pointer' : 'default',
              '&:hover': showDetails ? { boxShadow: 1 } : {}
            }}
          />
        </Tooltip>
        
        {showDetails && (
          <Tooltip title="Refresh health status">
            <IconButton size="small" onClick={handleRefresh}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {showDetails && (
        <Popover
          open={Boolean(anchorEl)}
          anchorEl={anchorEl}
          onClose={handleClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'left',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'left',
          }}
        >
          <Box sx={{ p: 2, minWidth: 300 }}>
            <Typography variant="h6" gutterBottom>
              System Health Details
            </Typography>
            
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Last checked: {lastCheck.toLocaleTimeString()}
            </Typography>

            <Divider sx={{ my: 1 }} />

            {health?.components && (
              <>
                <Typography variant="subtitle2" gutterBottom>
                  Components:
                </Typography>
                <List dense>
                  {Object.entries(health.components).map(([component, isHealthy]) => {
                    const componentStatus = getComponentStatus(component, isHealthy);
                    return (
                      <ListItem key={component} disablePadding>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          {componentStatus.icon}
                        </ListItemIcon>
                        <ListItemText
                          primary={formatComponentName(component)}
                          secondary={componentStatus.text}
                        />
                      </ListItem>
                    );
                  })}
                </List>
              </>
            )}

            {health?.circuit_breaker && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2" gutterBottom>
                  Circuit Breaker:
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Chip
                    label={health.circuit_breaker.state}
                    color={health.circuit_breaker.state === 'CLOSED' ? 'success' : 'warning'}
                    size="small"
                  />
                  <Typography variant="body2" color="text.secondary">
                    Failures: {health.circuit_breaker.failure_count}
                  </Typography>
                </Box>
              </>
            )}

            {health?.uptime && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Uptime: {Math.floor(health.uptime / 3600)}h {Math.floor((health.uptime % 3600) / 60)}m
                </Typography>
              </>
            )}

            {error && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography variant="body2" color="error">
                  Error: Unable to fetch health status
                </Typography>
              </>
            )}
          </Box>
        </Popover>
      )}
    </>
  );
};

export default HealthCheck;
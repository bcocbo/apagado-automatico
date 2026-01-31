import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  Alert,
  AlertTitle,
  IconButton,
  Tooltip,
  Paper,
  Snackbar,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  Savings as SavingsIcon,
  Speed as SpeedIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
} from '@mui/icons-material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Helmet } from 'react-helmet-async';

// Components
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner';
import { MetricsChart, NamespaceStatusGrid, RecentOperations } from './components';

// Hooks
import { useWebSocket } from '../../hooks/useWebSocket';

// Services
import { systemApi, scheduleApi } from '../../services/api';

// Types
import { SystemMetrics, ControllerHealth, NamespaceSchedule, WebSocketMessage } from '../../types';

const Dashboard: React.FC = () => {
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [wsNotification, setWsNotification] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // WebSocket connection for real-time updates
  const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8080/ws';
  
  const {
    connected: wsConnected,
    connecting: wsConnecting,
    error: wsError,
    sendMessage
  } = useWebSocket({
    url: wsUrl,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    onMessage: (message: WebSocketMessage) => {
      handleWebSocketMessage(message);
    },
    onConnect: () => {
      console.log('WebSocket connected');
      setWsNotification('Real-time updates connected');
      setTimeout(() => setWsNotification(null), 3000);
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
      setWsNotification('Real-time updates disconnected');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      setWsNotification('Connection error - using cached data');
    }
  });

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'system_health_update':
        // Invalidate and refetch health data
        queryClient.invalidateQueries({ queryKey: ['system-health'] });
        break;
      
      case 'metrics_update':
        // Invalidate and refetch metrics data
        queryClient.invalidateQueries({ queryKey: ['system-metrics'] });
        break;
      
      case 'schedule_update':
        // Invalidate and refetch schedules data
        queryClient.invalidateQueries({ queryKey: ['schedules'] });
        break;
      
      case 'operation_complete':
        // Invalidate recent operations and related data
        queryClient.invalidateQueries({ queryKey: ['recent-operations'] });
        queryClient.invalidateQueries({ queryKey: ['system-metrics'] });
        
        // Show notification for important operations
        if (message.data?.operation_type && message.data?.namespace) {
          const operationType = message.data.operation_type;
          const namespace = message.data.namespace;
          const status = message.data.status || 'completed';
          
          setWsNotification(
            `${operationType.charAt(0).toUpperCase() + operationType.slice(1)} ${status} for ${namespace}`
          );
          setTimeout(() => setWsNotification(null), 5000);
        }
        break;
      
      case 'alert':
        // Show alert notifications
        if (message.data?.message) {
          setWsNotification(`Alert: ${message.data.message}`);
          setTimeout(() => setWsNotification(null), 8000);
        }
        break;
      
      default:
        console.log('Unknown WebSocket message type:', message.type);
    }
  };

  // Fetch system health
  const {
    data: health,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['system-health'],
    queryFn: systemApi.getHealth,
    refetchInterval: wsConnected ? 60000 : 30000, // Slower polling when WebSocket is connected
    staleTime: wsConnected ? 30000 : 10000, // Cache longer when real-time updates available
  });

  // Fetch system metrics
  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: systemApi.getMetrics,
    refetchInterval: wsConnected ? 120000 : 60000, // Slower polling when WebSocket is connected
    staleTime: wsConnected ? 60000 : 30000,
  });

  // Fetch schedules for overview
  const {
    data: schedules,
    isLoading: schedulesLoading,
    error: schedulesError,
  } = useQuery({
    queryKey: ['schedules'],
    queryFn: scheduleApi.getAll,
    refetchInterval: wsConnected ? 300000 : 120000, // Much slower polling when WebSocket is connected
    staleTime: wsConnected ? 120000 : 60000,
  });

  const handleRefresh = async () => {
    await Promise.all([
      refetchHealth(),
      refetchMetrics(),
    ]);
    setLastRefresh(new Date());
  };

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'unhealthy':
        return 'error';
      default:
        return 'warning';
    }
  };

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon />;
      case 'unhealthy':
        return <ErrorIcon />;
      default:
        return <WarningIcon />;
    }
  };

  const calculateActiveSchedules = (schedules: NamespaceSchedule[] | undefined) => {
    if (!schedules) return 0;
    return schedules.filter(schedule => schedule.enabled).length;
  };

  const calculateTotalSavings = (schedules: NamespaceSchedule[] | undefined) => {
    if (!schedules) return 0;
    return schedules.reduce((total, schedule) => {
      return total + (schedule.metadata.cost_savings_target || 0);
    }, 0);
  };

  if (healthLoading || metricsLoading || schedulesLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner size={60} message="Loading dashboard..." />
      </Box>
    );
  }

  return (
    <>
      <Helmet>
        <title>Dashboard - Namespace Controller</title>
        <meta name="description" content="Real-time dashboard for namespace auto-shutdown system" />
      </Helmet>

      <Box>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            System Dashboard
          </Typography>
          
          <Box display="flex" alignItems="center" gap={2}>
            {/* WebSocket Connection Status */}
            <Tooltip title={wsConnected ? 'Real-time updates active' : wsConnecting ? 'Connecting...' : 'Real-time updates unavailable'}>
              <Chip
                icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                label={wsConnected ? 'Live' : wsConnecting ? 'Connecting' : 'Offline'}
                color={wsConnected ? 'success' : wsConnecting ? 'warning' : 'default'}
                size="small"
                variant="outlined"
              />
            </Tooltip>
            
            <Typography variant="body2" color="text.secondary">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </Typography>
            <Tooltip title="Refresh data">
              <IconButton onClick={handleRefresh} color="primary">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Health Status Alert */}
        {health && health.status !== 'healthy' && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            <AlertTitle>System Health Warning</AlertTitle>
            The controller is experiencing issues. Some components may not be functioning properly.
          </Alert>
        )}

        {/* Metrics Cards */}
        <Grid container spacing={3} mb={4}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Total Namespaces
                    </Typography>
                    <Typography variant="h4">
                      {metrics?.total_namespaces || 0}
                    </Typography>
                  </Box>
                  <ScheduleIcon color="primary" sx={{ fontSize: 40 }} />
                </Box>
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    {metrics?.active_namespaces || 0} active
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={
                      metrics?.total_namespaces
                        ? (metrics.active_namespaces / metrics.total_namespaces) * 100
                        : 0
                    }
                    sx={{ mt: 1 }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Active Schedules
                    </Typography>
                    <Typography variant="h4">
                      {calculateActiveSchedules(schedules)}
                    </Typography>
                  </Box>
                  <TrendingUpIcon color="success" sx={{ fontSize: 40 }} />
                </Box>
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    {schedules?.length || 0} total configured
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Monthly Savings
                    </Typography>
                    <Typography variant="h4">
                      ${calculateTotalSavings(schedules).toLocaleString()}
                    </Typography>
                  </Box>
                  <SavingsIcon color="success" sx={{ fontSize: 40 }} />
                </Box>
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    Estimated cost reduction
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Operations Today
                    </Typography>
                    <Typography variant="h4">
                      {metrics?.scaling_operations_today || 0}
                    </Typography>
                  </Box>
                  <SpeedIcon color="info" sx={{ fontSize: 40 }} />
                </Box>
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    Scaling operations
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* System Health Status */}
        <Grid container spacing={3} mb={4}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Health
                </Typography>
                
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  {getHealthStatusIcon(health?.status || 'unknown')}
                  <Chip
                    label={health?.status?.toUpperCase() || 'UNKNOWN'}
                    color={getHealthStatusColor(health?.status || 'unknown') as any}
                    variant="outlined"
                  />
                </Box>

                {health?.components && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Components Status:
                    </Typography>
                    <Grid container spacing={1}>
                      {Object.entries(health.components).map(([component, status]) => (
                        <Grid item xs={6} key={component}>
                          <Chip
                            label={component}
                            color={status ? 'success' : 'error'}
                            size="small"
                            variant="outlined"
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}

                {health?.circuit_breaker && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Circuit Breaker:
                    </Typography>
                    <Chip
                      label={health.circuit_breaker.state}
                      color={health.circuit_breaker.state === 'CLOSED' ? 'success' : 'warning'}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Failures: {health.circuit_breaker.failure_count}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Metrics
                </Typography>
                
                {metrics && <MetricsChart metrics={metrics} />}
                
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    Last updated: {metrics?.last_updated ? new Date(metrics.last_updated).toLocaleString() : 'Never'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Namespace Status and Recent Operations */}
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <NamespaceStatusGrid schedules={schedules} />
          </Grid>
          
          <Grid item xs={12} lg={4}>
            <RecentOperations />
          </Grid>
        </Grid>
      </Box>

      {/* WebSocket Notifications */}
      <Snackbar
        open={!!wsNotification}
        autoHideDuration={6000}
        onClose={() => setWsNotification(null)}
        message={wsNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      />
    </>
  );
};

export default Dashboard;
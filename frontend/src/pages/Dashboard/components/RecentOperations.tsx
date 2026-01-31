import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Chip,
  IconButton,
  Tooltip,
  Divider,
  Alert,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  MoreVert as MoreIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { systemApi } from '../../../services/api';
import LoadingSpinner from '../../../components/LoadingSpinner/LoadingSpinner';

interface Operation {
  id: string;
  type: 'startup' | 'shutdown' | 'scale' | 'rollback' | 'error';
  namespace: string;
  cluster?: string;
  status: 'success' | 'failed' | 'in_progress';
  timestamp: string;
  message?: string;
  details?: {
    resources_affected?: number;
    duration_ms?: number;
    error_code?: string;
  };
}

const RecentOperations: React.FC = () => {
  const {
    data: operations,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['recent-operations'],
    queryFn: async (): Promise<Operation[]> => {
      // Mock data for demonstration - replace with actual API call
      const mockOperations: Operation[] = [
        {
          id: '1',
          type: 'shutdown',
          namespace: 'dev-frontend',
          cluster: 'dev-cluster',
          status: 'success',
          timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
          message: 'Scheduled shutdown completed',
          details: { resources_affected: 3, duration_ms: 2500 }
        },
        {
          id: '2',
          type: 'startup',
          namespace: 'staging-api',
          cluster: 'staging-cluster',
          status: 'success',
          timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
          message: 'Scheduled startup completed',
          details: { resources_affected: 5, duration_ms: 8200 }
        },
        {
          id: '3',
          type: 'scale',
          namespace: 'prod-worker',
          cluster: 'prod-cluster',
          status: 'failed',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          message: 'Scale operation failed: insufficient resources',
          details: { error_code: 'RESOURCE_QUOTA_EXCEEDED' }
        },
        {
          id: '4',
          type: 'rollback',
          namespace: 'dev-backend',
          cluster: 'dev-cluster',
          status: 'success',
          timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
          message: 'Automatic rollback triggered',
          details: { resources_affected: 2, duration_ms: 1800 }
        },
        {
          id: '5',
          type: 'shutdown',
          namespace: 'test-env',
          cluster: 'test-cluster',
          status: 'in_progress',
          timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          message: 'Shutdown in progress...',
          details: { resources_affected: 4 }
        }
      ];
      
      return mockOperations;
    },
    refetchInterval: 30000, // 30 seconds
  });

  const getOperationIcon = (type: string, status: string) => {
    if (status === 'failed') {
      return <ErrorIcon color="error" />;
    }
    
    switch (type) {
      case 'startup':
        return <StartIcon color="success" />;
      case 'shutdown':
        return <StopIcon color="warning" />;
      case 'scale':
        return <RefreshIcon color="info" />;
      case 'rollback':
        return <WarningIcon color="warning" />;
      default:
        return <ScheduleIcon color="action" />;
    }
  };

  const getOperationColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'in_progress':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatOperationType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return '';
    
    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(1)}s`;
    } else {
      return `${(durationMs / 60000).toFixed(1)}m`;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Operations
          </Typography>
          <Box display="flex" justifyContent="center" py={4}>
            <LoadingSpinner size={40} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Operations
          </Typography>
          <Alert severity="error">
            Failed to load recent operations. Please try again.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Recent Operations
          </Typography>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={() => refetch()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {!operations || operations.length === 0 ? (
          <Alert severity="info">
            No recent operations found.
          </Alert>
        ) : (
          <List disablePadding>
            {operations.map((operation, index) => (
              <React.Fragment key={operation.id}>
                <ListItem
                  alignItems="flex-start"
                  sx={{
                    px: 0,
                    py: 1.5,
                  }}
                  secondaryAction={
                    <IconButton edge="end" size="small">
                      <MoreIcon />
                    </IconButton>
                  }
                >
                  <ListItemAvatar>
                    <Avatar sx={{ width: 36, height: 36 }}>
                      {getOperationIcon(operation.type, operation.status)}
                    </Avatar>
                  </ListItemAvatar>
                  
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                        <Typography variant="subtitle2">
                          {formatOperationType(operation.type)}
                        </Typography>
                        <Chip
                          label={operation.status.replace('_', ' ').toUpperCase()}
                          size="small"
                          color={getOperationColor(operation.status) as any}
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.primary" gutterBottom>
                          {operation.namespace}
                          {operation.cluster && (
                            <Typography component="span" variant="caption" color="text.secondary">
                              {' '}• {operation.cluster}
                            </Typography>
                          )}
                        </Typography>
                        
                        {operation.message && (
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {operation.message}
                          </Typography>
                        )}
                        
                        <Box display="flex" alignItems="center" gap={2} mt={0.5}>
                          <Typography variant="caption" color="text.secondary">
                            {formatDistanceToNow(parseISO(operation.timestamp), { addSuffix: true })}
                          </Typography>
                          
                          {operation.details?.resources_affected && (
                            <Typography variant="caption" color="text.secondary">
                              {operation.details.resources_affected} resources
                            </Typography>
                          )}
                          
                          {operation.details?.duration_ms && (
                            <Typography variant="caption" color="text.secondary">
                              {formatDuration(operation.details.duration_ms)}
                            </Typography>
                          )}
                          
                          {operation.details?.error_code && (
                            <Chip
                              label={operation.details.error_code}
                              size="small"
                              color="error"
                              variant="outlined"
                              sx={{ height: 16, fontSize: '0.6rem' }}
                            />
                          )}
                        </Box>
                      </Box>
                    }
                  />
                </ListItem>
                
                {index < operations.length - 1 && <Divider component="li" />}
              </React.Fragment>
            ))}
          </List>
        )}

        <Box mt={2} textAlign="center">
          <Typography variant="caption" color="text.secondary">
            Showing last {operations?.length || 0} operations
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default RecentOperations;
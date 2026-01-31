import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  IconButton,
  Tooltip,
  Avatar,
  LinearProgress,
  Collapse,
  Alert,
} from '@mui/material';
import {
  Schedule as ScheduleIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  AccessTime as TimeIcon,
  Savings as SavingsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { format, isAfter, isBefore, parseISO } from 'date-fns';
import { NamespaceSchedule } from '../../../types';

interface NamespaceStatusGridProps {
  schedules?: NamespaceSchedule[];
}

const NamespaceStatusGrid: React.FC<NamespaceStatusGridProps> = ({ schedules = [] }) => {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const toggleExpanded = (scheduleId: string) => {
    const newExpanded = new Set(expandedCards);
    if (newExpanded.has(scheduleId)) {
      newExpanded.delete(scheduleId);
    } else {
      newExpanded.add(scheduleId);
    }
    setExpandedCards(newExpanded);
  };

  const getScheduleStatus = (schedule: NamespaceSchedule) => {
    if (!schedule.enabled) {
      return { status: 'disabled', color: 'default', icon: <PauseIcon /> };
    }

    const now = new Date();
    const currentTime = format(now, 'HH:mm');
    
    // Check if we're in shutdown period
    if (schedule.shutdown_time && schedule.startup_time) {
      const shutdownTime = schedule.shutdown_time;
      const startupTime = schedule.startup_time;
      
      // Handle overnight schedules (shutdown after startup)
      if (shutdownTime > startupTime) {
        if (currentTime >= shutdownTime || currentTime < startupTime) {
          return { status: 'shutdown', color: 'error', icon: <PauseIcon /> };
        }
      } else {
        // Same day schedule
        if (currentTime >= shutdownTime && currentTime < startupTime) {
          return { status: 'shutdown', color: 'error', icon: <PauseIcon /> };
        }
      }
    }

    // Check if there are any recent errors
    if (schedule.metadata.last_error) {
      const lastError = parseISO(schedule.metadata.last_error);
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      if (isAfter(lastError, oneHourAgo)) {
        return { status: 'error', color: 'error', icon: <ErrorIcon /> };
      }
    }

    return { status: 'active', color: 'success', icon: <PlayIcon /> };
  };

  const getNextAction = (schedule: NamespaceSchedule) => {
    if (!schedule.enabled) return 'Disabled';
    
    const now = new Date();
    const currentTime = format(now, 'HH:mm');
    
    if (schedule.shutdown_time && schedule.startup_time) {
      const shutdownTime = schedule.shutdown_time;
      const startupTime = schedule.startup_time;
      
      // Handle overnight schedules
      if (shutdownTime > startupTime) {
        if (currentTime >= shutdownTime || currentTime < startupTime) {
          return `Startup at ${startupTime}`;
        } else {
          return `Shutdown at ${shutdownTime}`;
        }
      } else {
        // Same day schedule
        if (currentTime >= shutdownTime && currentTime < startupTime) {
          return `Startup at ${startupTime}`;
        } else if (currentTime < shutdownTime) {
          return `Shutdown at ${shutdownTime}`;
        } else {
          return `Shutdown at ${shutdownTime} (tomorrow)`;
        }
      }
    }
    
    return 'No schedule';
  };

  const calculateDailySavings = (schedule: NamespaceSchedule) => {
    if (!schedule.shutdown_time || !schedule.startup_time) return 0;
    
    const target = schedule.metadata.cost_savings_target || 0;
    return Math.round(target / 30); // Approximate daily savings from monthly target
  };

  if (schedules.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Namespace Status
          </Typography>
          <Alert severity="info">
            No namespace schedules configured yet. Create your first schedule to get started.
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
            Namespace Status
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {schedules.filter(s => s.enabled).length} of {schedules.length} active
          </Typography>
        </Box>

        <Grid container spacing={2}>
          {schedules.map((schedule) => {
            const { status, color, icon } = getScheduleStatus(schedule);
            const isExpanded = expandedCards.has(schedule.id);
            const dailySavings = calculateDailySavings(schedule);

            return (
              <Grid item xs={12} sm={6} lg={4} key={schedule.id}>
                <Card 
                  variant="outlined" 
                  sx={{ 
                    height: '100%',
                    transition: 'all 0.2s',
                    '&:hover': {
                      boxShadow: 2,
                    }
                  }}
                >
                  <CardContent sx={{ pb: 1 }}>
                    {/* Header */}
                    <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Avatar sx={{ width: 32, height: 32, bgcolor: `${color}.light` }}>
                          {icon}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2" noWrap>
                            {schedule.namespace}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {schedule.cluster || 'default'}
                          </Typography>
                        </Box>
                      </Box>
                      
                      <IconButton 
                        size="small" 
                        onClick={() => toggleExpanded(schedule.id)}
                      >
                        {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </Box>

                    {/* Status */}
                    <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                      <Chip
                        label={status.toUpperCase()}
                        color={color as any}
                        size="small"
                        variant="outlined"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {getNextAction(schedule)}
                      </Typography>
                    </Box>

                    {/* Schedule Times */}
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        <TimeIcon fontSize="small" color="action" />
                        <Typography variant="caption">
                          {schedule.shutdown_time || '--:--'} - {schedule.startup_time || '--:--'}
                        </Typography>
                      </Box>
                      {dailySavings > 0 && (
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <SavingsIcon fontSize="small" color="success" />
                          <Typography variant="caption" color="success.main">
                            ${dailySavings}/day
                          </Typography>
                        </Box>
                      )}
                    </Box>

                    {/* Days of Week */}
                    <Box display="flex" gap={0.5} mb={2}>
                      {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => {
                        const isActive = schedule.days_of_week?.includes(index + 1);
                        return (
                          <Chip
                            key={day}
                            label={day}
                            size="small"
                            variant={isActive ? "filled" : "outlined"}
                            color={isActive ? "primary" : "default"}
                            sx={{ 
                              minWidth: 'auto',
                              height: 20,
                              fontSize: '0.7rem',
                              '& .MuiChip-label': { px: 0.5 }
                            }}
                          />
                        );
                      })}
                    </Box>

                    {/* Expanded Details */}
                    <Collapse in={isExpanded}>
                      <Box pt={1} borderTop={1} borderColor="divider">
                        {/* Last Operation */}
                        {schedule.metadata.last_operation && (
                          <Box mb={1}>
                            <Typography variant="caption" color="text.secondary">
                              Last Operation:
                            </Typography>
                            <Typography variant="body2">
                              {schedule.metadata.last_operation} at{' '}
                              {schedule.metadata.last_operation_time 
                                ? format(parseISO(schedule.metadata.last_operation_time), 'MMM dd, HH:mm')
                                : 'Unknown'
                              }
                            </Typography>
                          </Box>
                        )}

                        {/* Error Information */}
                        {schedule.metadata.last_error && (
                          <Box mb={1}>
                            <Typography variant="caption" color="error">
                              Last Error:
                            </Typography>
                            <Typography variant="body2" color="error">
                              {schedule.metadata.last_error_message || 'Unknown error'}
                            </Typography>
                          </Box>
                        )}

                        {/* Resource Targets */}
                        {(schedule.resource_targets?.deployments || schedule.resource_targets?.statefulsets) && (
                          <Box mb={1}>
                            <Typography variant="caption" color="text.secondary">
                              Targets:
                            </Typography>
                            <Box display="flex" gap={1} flexWrap="wrap">
                              {schedule.resource_targets.deployments?.map((dep, idx) => (
                                <Chip
                                  key={`dep-${idx}`}
                                  label={`Deploy: ${dep}`}
                                  size="small"
                                  variant="outlined"
                                />
                              ))}
                              {schedule.resource_targets.statefulsets?.map((sts, idx) => (
                                <Chip
                                  key={`sts-${idx}`}
                                  label={`STS: ${sts}`}
                                  size="small"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        {/* Success Rate */}
                        {schedule.metadata.success_rate !== undefined && (
                          <Box>
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                              <Typography variant="caption" color="text.secondary">
                                Success Rate
                              </Typography>
                              <Typography variant="caption">
                                {schedule.metadata.success_rate}%
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={schedule.metadata.success_rate}
                              color={schedule.metadata.success_rate > 90 ? 'success' : 'warning'}
                              sx={{ height: 4, borderRadius: 2 }}
                            />
                          </Box>
                        )}
                      </Box>
                    </Collapse>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default NamespaceStatusGrid;
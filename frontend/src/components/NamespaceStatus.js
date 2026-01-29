import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Box,
  LinearProgress,
  Tooltip,
  IconButton,
  Collapse
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

const NamespaceStatus = ({ schedules }) => {
  const [expanded, setExpanded] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [namespaceStates, setNamespaceStates] = useState({});

  // Actualizar tiempo cada minuto
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  // Simular estados de namespaces
  useEffect(() => {
    const mockStates = {};
    schedules.forEach(schedule => {
      const status = getScheduleStatus(schedule);
      mockStates[schedule.namespace] = {
        status: status.color === 'success' ? 'running' : 'stopped',
        replicas: status.color === 'success' ? Math.floor(Math.random() * 5) + 1 : 0,
        lastScaled: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        deployments: Math.floor(Math.random() * 3) + 1
      };
    });
    setNamespaceStates(mockStates);
  }, [schedules, currentTime]);

  const getScheduleStatus = (schedule) => {
    if (!schedule.enabled) return { color: 'default', text: '⏸️ Pausado' };
    
    const now = new Date();
    const currentDay = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
    const currentTime = now.toTimeString().slice(0, 5);
    
    if (!schedule.days_of_week.includes(currentDay)) {
      return { color: 'default', text: '📅 Fuera de horario' };
    }
    
    if (currentTime >= schedule.startup_time && currentTime < schedule.shutdown_time) {
      return { color: 'success', text: '🟢 Activo' };
    } else {
      return { color: 'error', text: '🔴 Inactivo' };
    }
  };

  const getTimeUntilNextAction = (schedule) => {
    const now = new Date();
    const currentTime = now.toTimeString().slice(0, 5);
    const currentDay = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
    
    if (!schedule.enabled || !schedule.days_of_week.includes(currentDay)) {
      return null;
    }

    const [startHour, startMin] = schedule.startup_time.split(':').map(Number);
    const [endHour, endMin] = schedule.shutdown_time.split(':').map(Number);
    const [currentHour, currentMin] = currentTime.split(':').map(Number);
    
    const currentMinutes = currentHour * 60 + currentMin;
    const startMinutes = startHour * 60 + startMin;
    const endMinutes = endHour * 60 + endMin;
    
    if (currentMinutes < startMinutes) {
      const diff = startMinutes - currentMinutes;
      return { action: 'encendido', minutes: diff };
    } else if (currentMinutes < endMinutes) {
      const diff = endMinutes - currentMinutes;
      return { action: 'apagado', minutes: diff };
    }
    
    return null;
  };

  const formatTimeUntil = (minutes) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const activeSchedules = schedules.filter(s => s.enabled);
  const runningNamespaces = schedules.filter(s => getScheduleStatus(s).color === 'success').length;
  const totalReplicas = Object.values(namespaceStates).reduce((sum, state) => sum + state.replicas, 0);

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" component="h2">
            🔄 Estado en Tiempo Real
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {currentTime.toLocaleTimeString('es-CO', { 
                timeZone: 'America/Bogota',
                hour: '2-digit', 
                minute: '2-digit' 
              })} COT
            </Typography>
            <Tooltip title="Actualizar">
              <IconButton size="small" onClick={() => setCurrentTime(new Date())}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton
              size="small"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {runningNamespaces}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Namespaces Activos
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {totalReplicas}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Réplicas Totales
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main">
                {activeSchedules.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Horarios Activos
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Collapse in={expanded}>
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              📊 Detalles por Namespace
            </Typography>
            
            {schedules.map((schedule) => {
              const status = getScheduleStatus(schedule);
              const state = namespaceStates[schedule.namespace] || {};
              const nextAction = getTimeUntilNextAction(schedule);
              
              return (
                <Card key={schedule.id} variant="outlined" sx={{ mb: 2 }}>
                  <CardContent sx={{ py: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} sm={3}>
                        <Typography variant="subtitle1" fontWeight="bold">
                          📦 {schedule.namespace}
                        </Typography>
                        <Chip 
                          label={status.text} 
                          color={status.color} 
                          size="small" 
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Réplicas: {state.replicas || 0}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Deployments: {state.deployments || 0}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={12} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Horario: {schedule.startup_time} - {schedule.shutdown_time}
                        </Typography>
                        {state.lastScaled && (
                          <Typography variant="body2" color="text.secondary">
                            Último cambio: {new Date(state.lastScaled).toLocaleTimeString('es-CO', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </Typography>
                        )}
                      </Grid>
                      
                      <Grid item xs={12} sm={3}>
                        {nextAction && (
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              Próximo {nextAction.action}:
                            </Typography>
                            <Typography variant="body2" fontWeight="bold" color="primary">
                              {formatTimeUntil(nextAction.minutes)}
                            </Typography>
                            <LinearProgress 
                              variant="determinate" 
                              value={Math.max(0, 100 - (nextAction.minutes / 60) * 100)} 
                              sx={{ mt: 1 }}
                            />
                          </Box>
                        )}
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              );
            })}
            
            {schedules.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                No hay namespaces configurados para mostrar
              </Typography>
            )}
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default NamespaceStatus;
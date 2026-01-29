import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  FormControlLabel,
  Switch,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Snackbar
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon,
  PowerSettingsNew as PowerIcon
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import NamespaceStatus from './components/NamespaceStatus';
import { scheduleService, namespaceService, systemService } from './services/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    success: {
      main: '#2e7d32',
    },
    warning: {
      main: '#ed6c02',
    },
  },
});

const DAYS_OF_WEEK = [
  { value: 'monday', label: 'Lunes', short: 'L' },
  { value: 'tuesday', label: 'Martes', short: 'M' },
  { value: 'wednesday', label: 'Miércoles', short: 'X' },
  { value: 'thursday', label: 'Jueves', short: 'J' },
  { value: 'friday', label: 'Viernes', short: 'V' },
  { value: 'saturday', label: 'Sábado', short: 'S' },
  { value: 'sunday', label: 'Domingo', short: 'D' }
];

const TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/Bogota', label: 'Colombia (UTC-5)' },
  { value: 'America/New_York', label: 'New York (UTC-5)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (UTC-8)' },
  { value: 'Europe/Madrid', label: 'Madrid (UTC+1)' }
];

function ScheduleForm({ open, onClose, onSubmit, schedule = null, namespaces = [] }) {
  const [formData, setFormData] = useState({
    namespace: '',
    enabled: true,
    timezone: 'America/Bogota',
    startup_time: '08:00',
    shutdown_time: '17:00',
    days_of_week: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    metadata: {
      business_unit: '',
      cost_savings_target: ''
    }
  });

  useEffect(() => {
    if (schedule) {
      setFormData(schedule);
    } else {
      setFormData({
        namespace: '',
        enabled: true,
        timezone: 'America/Bogota',
        startup_time: '08:00',
        shutdown_time: '17:00',
        days_of_week: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
        metadata: {
          business_unit: '',
          cost_savings_target: ''
        }
      });
    }
  }, [schedule, open]);

  const handleDayToggle = (day) => {
    const newDays = formData.days_of_week.includes(day)
      ? formData.days_of_week.filter(d => d !== day)
      : [...formData.days_of_week, day];
    
    setFormData({ ...formData, days_of_week: newDays });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {schedule ? '✏️ Editar Horario' : '➕ Crear Nuevo Horario'}
      </DialogTitle>
      <DialogContent>
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
          <Grid container spacing={2}>
            {/* Namespace */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Namespace</InputLabel>
                <Select
                  value={formData.namespace}
                  label="Namespace"
                  onChange={(e) => setFormData({ ...formData, namespace: e.target.value })}
                  required
                >
                  {namespaces.map((ns) => (
                    <MenuItem key={ns} value={ns}>{ns}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Timezone */}
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Zona Horaria</InputLabel>
                <Select
                  value={formData.timezone}
                  label="Zona Horaria"
                  onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                >
                  {TIMEZONES.map((tz) => (
                    <MenuItem key={tz.value} value={tz.value}>{tz.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Horarios */}
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="🟢 Hora de Encendido"
                type="time"
                value={formData.startup_time}
                onChange={(e) => setFormData({ ...formData, startup_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="🔴 Hora de Apagado"
                type="time"
                value={formData.shutdown_time}
                onChange={(e) => setFormData({ ...formData, shutdown_time: e.target.value })}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>

            {/* Días de la semana */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                📅 Días de la Semana
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {DAYS_OF_WEEK.map((day) => (
                  <Chip
                    key={day.value}
                    label={`${day.short} - ${day.label}`}
                    onClick={() => handleDayToggle(day.value)}
                    color={formData.days_of_week.includes(day.value) ? 'primary' : 'default'}
                    variant={formData.days_of_week.includes(day.value) ? 'filled' : 'outlined'}
                    clickable
                  />
                ))}
              </Box>
            </Grid>

            {/* Metadata */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" gutterBottom>
                📊 Información Adicional
              </Typography>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Unidad de Negocio"
                value={formData.metadata.business_unit}
                onChange={(e) => setFormData({
                  ...formData,
                  metadata: { ...formData.metadata, business_unit: e.target.value }
                })}
                placeholder="Ej: Engineering, Marketing"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Meta de Ahorro (USD/mes)"
                type="number"
                value={formData.metadata.cost_savings_target}
                onChange={(e) => setFormData({
                  ...formData,
                  metadata: { ...formData.metadata, cost_savings_target: e.target.value }
                })}
                placeholder="1000"
              />
            </Grid>

            {/* Estado */}
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                    color="primary"
                  />
                }
                label={formData.enabled ? "✅ Horario Activo" : "⏸️ Horario Pausado"}
              />
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button onClick={handleSubmit} variant="contained">
          {schedule ? 'Actualizar' : 'Crear'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function App() {
  const [schedules, setSchedules] = useState([]);
  const [namespaces, setNamespaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);

  // Cargar datos iniciales
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setInitialLoading(true);
    try {
      // Cargar datos en paralelo
      const [schedulesData, namespacesData, healthData] = await Promise.all([
        scheduleService.getSchedules(),
        namespaceService.getNamespaces(),
        systemService.getSystemHealth()
      ]);

      setSchedules(schedulesData);
      setNamespaces(namespacesData);
      setSystemHealth(healthData);
    } catch (err) {
      setError('Error cargando datos iniciales: ' + err.message);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleCreateSchedule = async (scheduleData) => {
    setLoading(true);
    setError('');

    try {
      const newSchedule = await scheduleService.createSchedule(scheduleData);
      setSchedules([...schedules, newSchedule]);
      setSuccess('Horario creado exitosamente');
      console.log('Schedule created:', newSchedule);
      
    } catch (err) {
      setError('Error creando horario: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditSchedule = async (scheduleData) => {
    setLoading(true);
    setError('');

    try {
      const updatedSchedule = await scheduleService.updateSchedule(editingSchedule.id, scheduleData);
      const updatedSchedules = schedules.map(s => 
        s.id === editingSchedule.id ? updatedSchedule : s
      );
      
      setSchedules(updatedSchedules);
      setEditingSchedule(null);
      setSuccess('Horario actualizado exitosamente');
      console.log('Schedule updated:', updatedSchedule);
      
    } catch (err) {
      setError('Error actualizando horario: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId) => {
    if (window.confirm('¿Estás seguro de que quieres eliminar este horario?')) {
      try {
        await scheduleService.deleteSchedule(scheduleId);
        setSchedules(schedules.filter(s => s.id !== scheduleId));
        setSuccess('Horario eliminado exitosamente');
      } catch (err) {
        setError('Error eliminando horario: ' + err.message);
      }
    }
  };

  const handleToggleSchedule = async (scheduleId) => {
    const schedule = schedules.find(s => s.id === scheduleId);
    const newEnabled = !schedule.enabled;
    
    try {
      await scheduleService.toggleSchedule(scheduleId, newEnabled);
      const updatedSchedules = schedules.map(s => 
        s.id === scheduleId ? { ...s, enabled: newEnabled } : s
      );
      setSchedules(updatedSchedules);
      setSuccess(`Horario ${newEnabled ? 'activado' : 'desactivado'} exitosamente`);
    } catch (err) {
      setError('Error cambiando estado del horario: ' + err.message);
    }
  };

  const openEditDialog = (schedule) => {
    setEditingSchedule(schedule);
    setDialogOpen(true);
  };

  const openCreateDialog = () => {
    setEditingSchedule(null);
    setDialogOpen(true);
  };

  const formatDays = (days) => {
    const dayMap = DAYS_OF_WEEK.reduce((acc, day) => {
      acc[day.value] = day.short;
      return acc;
    }, {});
    
    return days.map(day => dayMap[day]).join(', ');
  };

  const getScheduleStatus = (schedule) => {
    if (!schedule.enabled) return { color: 'default', text: '⏸️ Pausado' };
    
    const now = new Date();
    const currentDay = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
    const currentTime = now.toTimeString().slice(0, 5);
    
    if (!schedule.days_of_week.includes(currentDay)) {
      return { color: 'default', text: '� Fuera de horario' };
    }
    
    if (currentTime >= schedule.startup_time && currentTime < schedule.shutdown_time) {
      return { color: 'success', text: '🟢 Activo' };
    } else {
      return { color: 'error', text: '🔴 Inactivo' };
    }
  };

  if (initialLoading) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
            <Box sx={{ textAlign: 'center' }}>
              <CircularProgress size={60} sx={{ mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Cargando sistema de namespaces...
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Conectando con el controlador
              </Typography>
            </Box>
          </Box>
        </Container>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography variant="h3" component="h1" gutterBottom>
              🎛️ Namespace Encendido EKS
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Sistema de apagado automático de namespaces para optimización de costos
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreateDialog}
            size="large"
          >
            Nuevo Horario
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Estado en tiempo real */}
          <Grid item xs={12}>
            <NamespaceStatus schedules={schedules} />
          </Grid>

          {/* Dashboard de estado */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  📊 Resumen del Sistema
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={3}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary">
                          {schedules.length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Horarios Configurados
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          {schedules.filter(s => s.enabled).length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Horarios Activos
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="warning.main">
                          {schedules.filter(s => getScheduleStatus(s).color === 'success').length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Namespaces Encendidos
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="secondary">
                          ${schedules.reduce((sum, s) => sum + (parseInt(s.metadata?.cost_savings_target) || 0), 0)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Ahorro Estimado/mes
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Lista de horarios */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  📋 Horarios Configurados
                </Typography>
                
                {schedules.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <ScheduleIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      No hay horarios configurados
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Crea tu primer horario para comenzar a optimizar costos
                    </Typography>
                    <Button variant="contained" onClick={openCreateDialog}>
                      Crear Primer Horario
                    </Button>
                  </Box>
                ) : (
                  <List>
                    {schedules.map((schedule) => {
                      const status = getScheduleStatus(schedule);
                      return (
                        <ListItem key={schedule.id} divider>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="h6">
                                  📦 {schedule.namespace}
                                </Typography>
                                <Chip 
                                  label={status.text} 
                                  color={status.color} 
                                  size="small" 
                                />
                              </Box>
                            }
                            secondary={
                              <Box sx={{ mt: 1 }}>
                                <Typography variant="body2" color="text.secondary">
                                  🕐 {schedule.startup_time} - {schedule.shutdown_time} ({schedule.timezone})
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  📅 {formatDays(schedule.days_of_week)}
                                </Typography>
                                {schedule.metadata?.business_unit && (
                                  <Typography variant="body2" color="text.secondary">
                                    🏢 {schedule.metadata.business_unit}
                                  </Typography>
                                )}
                                {schedule.metadata?.cost_savings_target && (
                                  <Typography variant="body2" color="text.secondary">
                                    💰 Meta de ahorro: ${schedule.metadata.cost_savings_target}/mes
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                          <ListItemSecondaryAction>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <IconButton
                                edge="end"
                                onClick={() => handleToggleSchedule(schedule.id)}
                                color={schedule.enabled ? 'success' : 'default'}
                              >
                                <PowerIcon />
                              </IconButton>
                              <IconButton
                                edge="end"
                                onClick={() => openEditDialog(schedule)}
                              >
                                <EditIcon />
                              </IconButton>
                              <IconButton
                                edge="end"
                                onClick={() => handleDeleteSchedule(schedule.id)}
                                color="error"
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Box>
                          </ListItemSecondaryAction>
                        </ListItem>
                      );
                    })}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Dialog para crear/editar horarios */}
        <ScheduleForm
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          onSubmit={editingSchedule ? handleEditSchedule : handleCreateSchedule}
          schedule={editingSchedule}
          namespaces={namespaces}
        />

        {/* Notificaciones */}
        <Snackbar
          open={!!success}
          autoHideDuration={4000}
          onClose={() => setSuccess('')}
        >
          <Alert onClose={() => setSuccess('')} severity="success" sx={{ width: '100%' }}>
            {success}
          </Alert>
        </Snackbar>

        <Snackbar
          open={!!error}
          autoHideDuration={6000}
          onClose={() => setError('')}
        >
          <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>
      </Container>
    </ThemeProvider>
  );
}

export default App;
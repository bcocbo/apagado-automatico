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
  CircularProgress
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newSchedule, setNewSchedule] = useState({
    namespace: '',
    startup: '08:00',
    shutdown: '17:00'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Aquí iría la llamada a la API
      console.log('Creating schedule:', newSchedule);
      
      // Simular éxito
      setSchedules([...schedules, { ...newSchedule, id: Date.now() }]);
      setNewSchedule({ namespace: '', startup: '08:00', shutdown: '17:00' });
      
    } catch (err) {
      setError('Error creating schedule: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          🎛️ Namespace Auto-Shutdown
        </Typography>
        
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Sistema de apagado automático de namespaces para optimización de costos
        </Typography>

        <Grid container spacing={3}>
          {/* Formulario para crear schedule */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  📅 Crear Horario
                </Typography>
                
                {error && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                  </Alert>
                )}

                <Box component="form" onSubmit={handleSubmit}>
                  <TextField
                    fullWidth
                    label="Namespace"
                    value={newSchedule.namespace}
                    onChange={(e) => setNewSchedule({
                      ...newSchedule,
                      namespace: e.target.value
                    })}
                    margin="normal"
                    required
                    placeholder="mi-aplicacion"
                  />
                  
                  <TextField
                    fullWidth
                    label="Hora de Encendido"
                    type="time"
                    value={newSchedule.startup}
                    onChange={(e) => setNewSchedule({
                      ...newSchedule,
                      startup: e.target.value
                    })}
                    margin="normal"
                    InputLabelProps={{ shrink: true }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Hora de Apagado"
                    type="time"
                    value={newSchedule.shutdown}
                    onChange={(e) => setNewSchedule({
                      ...newSchedule,
                      shutdown: e.target.value
                    })}
                    margin="normal"
                    InputLabelProps={{ shrink: true }}
                  />
                  
                  <Button
                    type="submit"
                    variant="contained"
                    fullWidth
                    disabled={loading}
                    sx={{ mt: 2 }}
                  >
                    {loading ? <CircularProgress size={24} /> : 'Crear Horario'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Lista de schedules */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  📋 Horarios Configurados
                </Typography>
                
                {schedules.length === 0 ? (
                  <Typography color="text.secondary">
                    No hay horarios configurados
                  </Typography>
                ) : (
                  schedules.map((schedule) => (
                    <Card key={schedule.id} variant="outlined" sx={{ mb: 1 }}>
                      <CardContent sx={{ py: 1 }}>
                        <Typography variant="h6">
                          📦 {schedule.namespace}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          🟢 Encendido: {schedule.startup} | 🔴 Apagado: {schedule.shutdown}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Dashboard de estado */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  📊 Estado del Sistema
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary">
                          {schedules.length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Namespaces Configurados
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          ✅
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Sistema Activo
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="secondary">
                          💰
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Ahorro Estimado
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </ThemeProvider>
  );
}

export default App;
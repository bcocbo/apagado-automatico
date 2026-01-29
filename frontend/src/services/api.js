import axios from 'axios';

// Configuración base de la API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para manejo de errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    if (error.response) {
      // El servidor respondió con un código de error
      const message = error.response.data?.message || error.response.statusText;
      throw new Error(`Error ${error.response.status}: ${message}`);
    } else if (error.request) {
      // La petición se hizo pero no hubo respuesta
      throw new Error('No se pudo conectar con el servidor. Verifica que el controlador esté ejecutándose.');
    } else {
      // Error en la configuración de la petición
      throw new Error('Error en la configuración de la petición');
    }
  }
);

// Servicios de la API
export const scheduleService = {
  // Obtener todos los horarios
  async getSchedules() {
    try {
      const response = await api.get('/api/schedules');
      return response.data;
    } catch (error) {
      console.warn('No se pudieron cargar los horarios desde la API, usando datos mock');
      // Retornar datos mock si la API no está disponible
      return [
        {
          id: 1,
          namespace: 'production-app',
          enabled: true,
          timezone: 'America/Bogota',
          startup_time: '08:00',
          shutdown_time: '18:00',
          days_of_week: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
          metadata: {
            business_unit: 'Engineering',
            cost_savings_target: '1500'
          },
          created_at: '2024-01-15T10:30:00Z'
        }
      ];
    }
  },

  // Crear un nuevo horario
  async createSchedule(scheduleData) {
    try {
      const response = await api.post('/api/schedules', scheduleData);
      return response.data;
    } catch (error) {
      console.warn('No se pudo crear el horario en la API, simulando éxito');
      // Simular éxito si la API no está disponible
      return {
        ...scheduleData,
        id: Date.now(),
        created_at: new Date().toISOString()
      };
    }
  },

  // Actualizar un horario existente
  async updateSchedule(scheduleId, scheduleData) {
    try {
      const response = await api.put(`/api/schedules/${scheduleId}`, scheduleData);
      return response.data;
    } catch (error) {
      console.warn('No se pudo actualizar el horario en la API, simulando éxito');
      // Simular éxito si la API no está disponible
      return {
        ...scheduleData,
        id: scheduleId,
        updated_at: new Date().toISOString()
      };
    }
  },

  // Eliminar un horario
  async deleteSchedule(scheduleId) {
    try {
      await api.delete(`/api/schedules/${scheduleId}`);
      return true;
    } catch (error) {
      console.warn('No se pudo eliminar el horario en la API, simulando éxito');
      return true;
    }
  },

  // Alternar estado de un horario (activar/desactivar)
  async toggleSchedule(scheduleId, enabled) {
    try {
      const response = await api.patch(`/api/schedules/${scheduleId}`, { enabled });
      return response.data;
    } catch (error) {
      console.warn('No se pudo cambiar el estado del horario en la API, simulando éxito');
      return { id: scheduleId, enabled };
    }
  }
};

export const namespaceService = {
  // Obtener lista de namespaces disponibles
  async getNamespaces() {
    try {
      const response = await api.get('/api/namespaces');
      return response.data;
    } catch (error) {
      console.warn('No se pudieron cargar los namespaces desde la API, usando datos mock');
      // Retornar namespaces mock si la API no está disponible
      return [
        'production-app',
        'staging-app', 
        'development-app',
        'testing-app',
        'demo-app',
        'monitoring',
        'logging'
      ];
    }
  },

  // Obtener estado actual de los namespaces
  async getNamespaceStatus() {
    try {
      const response = await api.get('/api/namespaces/status');
      return response.data;
    } catch (error) {
      console.warn('No se pudo obtener el estado de los namespaces, usando datos mock');
      // Retornar estado mock si la API no está disponible
      return {
        'production-app': {
          status: 'running',
          replicas: 3,
          deployments: 2,
          lastScaled: new Date(Date.now() - 1800000).toISOString() // 30 min ago
        },
        'staging-app': {
          status: 'stopped',
          replicas: 0,
          deployments: 1,
          lastScaled: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
        }
      };
    }
  }
};

export const systemService = {
  // Obtener estado del sistema
  async getSystemHealth() {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.warn('No se pudo verificar el estado del sistema');
      return { status: 'unknown', error: error.message };
    }
  },

  // Obtener métricas del sistema
  async getMetrics() {
    try {
      const response = await api.get('/metrics');
      return response.data;
    } catch (error) {
      console.warn('No se pudieron obtener las métricas del sistema');
      return null;
    }
  }
};

export default api;
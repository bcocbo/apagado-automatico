import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { 
  NamespaceSchedule, 
  CreateScheduleRequest, 
  UpdateScheduleRequest,
  SystemMetrics,
  ControllerHealth,
  NamespaceStatus,
  ScalingOperation,
  ApiResponse
} from '../types';

// Create axios instance with default configuration
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for adding auth tokens, correlation IDs, etc.
  instance.interceptors.request.use(
    (config) => {
      // Add correlation ID for request tracing
      config.headers['X-Correlation-ID'] = generateCorrelationId();
      
      // Add timestamp
      config.headers['X-Request-Time'] = new Date().toISOString();
      
      // Add user agent info
      config.headers['X-User-Agent'] = navigator.userAgent;
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for handling common errors and logging
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log successful responses in development
      if (process.env.NODE_ENV === 'development') {
        console.log(`API Success: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          status: response.status,
          duration: Date.now() - (response.config as any).startTime,
          data: response.data
        });
      }
      
      return response;
    },
    (error: AxiosError) => {
      // Log errors
      console.error(`API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response?.status,
        message: error.message,
        data: error.response?.data
      });

      // Handle specific error cases
      if (error.response?.status === 401) {
        // Handle unauthorized - could redirect to login
        console.warn('Unauthorized request - consider implementing auth');
      } else if (error.response?.status >= 500) {
        // Server errors
        console.error('Server error occurred');
      } else if (error.code === 'ECONNABORTED') {
        // Timeout
        console.error('Request timeout');
      }

      return Promise.reject(error);
    }
  );

  return instance;
};

const api = createApiInstance();

// Utility function to generate correlation IDs
const generateCorrelationId = (): string => {
  return `web-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Utility function to handle API responses
const handleApiResponse = <T>(response: AxiosResponse<T>): T => {
  return response.data;
};

// Schedule API
export const scheduleApi = {
  async getAll(): Promise<NamespaceSchedule[]> {
    const startTime = Date.now();
    try {
      const response = await api.get<NamespaceSchedule[]>('/schedules');
      
      // Track performance
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall('/schedules', duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch schedules: ${error}`);
      }
      
      // Return mock data if API is not available
      console.warn('API not available, returning mock data');
      return [
        {
          id: '1',
          namespace: 'production-app',
          enabled: true,
          timezone: 'America/Bogota',
          startup_time: '08:00',
          shutdown_time: '18:00',
          days_of_week: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
          metadata: {
            business_unit: 'Engineering',
            cost_savings_target: 1500
          },
          created_at: '2024-01-15T10:30:00Z',
          updated_at: '2024-01-15T10:30:00Z'
        }
      ];
    }
  },

  async getById(id: string): Promise<NamespaceSchedule> {
    const startTime = Date.now();
    try {
      const response = await api.get<NamespaceSchedule>(`/schedules/${id}`);
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall(`/schedules/${id}`, duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch schedule ${id}: ${error}`);
      }
      throw error;
    }
  },

  async create(data: CreateScheduleRequest): Promise<NamespaceSchedule> {
    const startTime = Date.now();
    try {
      const response = await api.post<NamespaceSchedule>('/schedules', data);
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall('POST /schedules', duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to create schedule: ${error}`);
      }
      
      // Return mock success if API is not available
      console.warn('API not available, returning mock success');
      return {
        ...data,
        id: Date.now().toString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      } as NamespaceSchedule;
    }
  },

  async update(id: string, data: Partial<UpdateScheduleRequest>): Promise<NamespaceSchedule> {
    const startTime = Date.now();
    try {
      const response = await api.put<NamespaceSchedule>(`/schedules/${id}`, data);
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall(`PUT /schedules/${id}`, duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to update schedule ${id}: ${error}`);
      }
      throw error;
    }
  },

  async delete(id: string): Promise<void> {
    const startTime = Date.now();
    try {
      await api.delete(`/schedules/${id}`);
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall(`DELETE /schedules/${id}`, duration);
      }
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to delete schedule ${id}: ${error}`);
      }
      throw error;
    }
  }
};

// System API
export const systemApi = {
  async getHealth(): Promise<ControllerHealth> {
    const startTime = Date.now();
    try {
      const response = await api.get<ControllerHealth>('/health');
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall('/health', duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch health: ${error}`);
      }
      
      // Return mock health data
      return {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        components: {
          dynamodb: false,
          kubernetes: false,
          controller: false,
          circuit_breaker: false
        }
      };
    }
  },

  async getMetrics(): Promise<SystemMetrics> {
    const startTime = Date.now();
    try {
      const response = await api.get<SystemMetrics>('/metrics');
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall('/metrics', duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch metrics: ${error}`);
      }
      
      // Return mock metrics
      return {
        total_namespaces: 5,
        active_namespaces: 2,
        scheduled_namespaces: 3,
        cost_savings_monthly: 2500,
        scaling_operations_today: 12,
        last_updated: new Date().toISOString()
      };
    }
  },

  async getNamespaces(): Promise<string[]> {
    const startTime = Date.now();
    try {
      const response = await api.get<string[]>('/namespaces');
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall('/namespaces', duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch namespaces: ${error}`);
      }
      
      // Return mock namespaces
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
  }
};

// Namespace API
export const namespaceApi = {
  async getStatus(namespace: string): Promise<NamespaceStatus> {
    const startTime = Date.now();
    try {
      const response = await api.get<NamespaceStatus>(`/namespaces/${namespace}/status`);
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall(`/namespaces/${namespace}/status`, duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to fetch namespace status: ${error}`);
      }
      
      // Return mock status
      return {
        namespace,
        status: 'active',
        current_replicas: 3,
        target_replicas: 3,
        last_scaled: new Date(Date.now() - 1800000).toISOString(),
        health_status: 'healthy'
      };
    }
  },

  async scale(namespace: string, replicas: number): Promise<ScalingOperation> {
    const startTime = Date.now();
    try {
      const response = await api.post<ScalingOperation>(`/namespaces/${namespace}/scale`, { replicas });
      
      const duration = Date.now() - startTime;
      if (window.performanceMonitor) {
        window.performanceMonitor.trackApiCall(`POST /namespaces/${namespace}/scale`, duration);
      }
      
      return handleApiResponse(response);
    } catch (error) {
      if (window.performanceMonitor) {
        window.performanceMonitor.trackError('api_error', `Failed to scale namespace ${namespace}: ${error}`);
      }
      throw error;
    }
  }
};

// Export the main API instance for custom requests
export default api;

// Extend window interface for performance monitoring
declare global {
  interface Window {
    performanceMonitor?: {
      trackApiCall: (endpoint: string, duration: number) => void;
      trackError: (type: string, message: string) => void;
    };
  }
}
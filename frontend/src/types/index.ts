// Types for the Namespace Auto-Shutdown System Frontend

export interface NamespaceSchedule {
  id: string;
  namespace: string;
  enabled: boolean;
  timezone: string;
  startup_time: string;
  shutdown_time: string;
  days_of_week: DayOfWeek[];
  metadata: ScheduleMetadata;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface ScheduleMetadata {
  business_unit?: string;
  cost_savings_target?: number;
  description?: string;
  contact_email?: string;
  priority?: 'low' | 'medium' | 'high';
}

export type DayOfWeek = 
  | 'monday' 
  | 'tuesday' 
  | 'wednesday' 
  | 'thursday' 
  | 'friday' 
  | 'saturday' 
  | 'sunday';

export interface NamespaceStatus {
  namespace: string;
  status: 'active' | 'inactive' | 'scaling' | 'error';
  current_replicas: number;
  target_replicas: number;
  last_scaled: string;
  next_action?: 'startup' | 'shutdown';
  next_action_time?: string;
  health_status: 'healthy' | 'unhealthy' | 'unknown';
}

export interface SystemMetrics {
  total_namespaces: number;
  active_namespaces: number;
  scheduled_namespaces: number;
  cost_savings_monthly: number;
  scaling_operations_today: number;
  last_updated: string;
}

export interface ScalingOperation {
  id: string;
  namespace: string;
  operation: 'startup' | 'shutdown';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  duration?: number;
  error_message?: string;
  correlation_id: string;
}

export interface ControllerHealth {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  components: {
    dynamodb: boolean;
    kubernetes: boolean;
    controller: boolean;
    circuit_breaker: boolean;
  };
  circuit_breaker?: {
    state: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
    failure_count: number;
    is_open: boolean;
  };
  last_successful_operations?: Record<string, any>;
}

export interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  namespace?: string;
  timestamp: string;
  acknowledged: boolean;
  resolved: boolean;
}

export interface WebSocketMessage {
  type: 'namespace_status' | 'scaling_operation' | 'system_metrics' | 'alert' | 'health_update';
  data: any;
  timestamp: string;
}

export interface PerformanceMetrics {
  page_load_time: number;
  api_response_times: Record<string, number>;
  user_interactions: UserInteraction[];
  errors: ErrorEvent[];
  memory_usage?: number;
  connection_status: 'online' | 'offline';
}

export interface UserInteraction {
  type: 'click' | 'navigation' | 'form_submit' | 'search';
  element: string;
  timestamp: string;
  duration?: number;
}

export interface ErrorEvent {
  type: 'api_error' | 'websocket_error' | 'component_error' | 'network_error';
  message: string;
  stack?: string;
  timestamp: string;
  url?: string;
  user_agent?: string;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
  timestamp: string;
}

export interface CreateScheduleRequest {
  namespace: string;
  timezone: string;
  startup_time: string;
  shutdown_time: string;
  days_of_week: DayOfWeek[];
  enabled?: boolean;
  metadata?: ScheduleMetadata;
}

export interface UpdateScheduleRequest extends Partial<CreateScheduleRequest> {
  id: string;
}

// Theme and UI Types
export interface ThemeConfig {
  mode: 'light' | 'dark';
  primary_color: string;
  secondary_color: string;
}

export interface NotificationSettings {
  enabled: boolean;
  types: ('success' | 'warning' | 'error' | 'info')[];
  duration: number;
  position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

export interface UserPreferences {
  theme: ThemeConfig;
  notifications: NotificationSettings;
  timezone: string;
  refresh_interval: number;
  items_per_page: number;
}

// WebSocket Connection State
export interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  last_message: WebSocketMessage | null;
  reconnect_attempts: number;
  max_reconnect_attempts: number;
}

// Cache Types
export interface CacheEntry<T> {
  data: T;
  timestamp: string;
  expires_at: string;
}

export interface CacheState {
  schedules: CacheEntry<NamespaceSchedule[]> | null;
  namespaces: CacheEntry<string[]> | null;
  metrics: CacheEntry<SystemMetrics> | null;
  health: CacheEntry<ControllerHealth> | null;
}

// Form Types
export interface ScheduleFormData {
  namespace: string;
  timezone: string;
  startup_time: string;
  shutdown_time: string;
  days_of_week: DayOfWeek[];
  enabled: boolean;
  business_unit: string;
  cost_savings_target: string;
  description: string;
  contact_email: string;
  priority: 'low' | 'medium' | 'high';
}

export interface FilterOptions {
  status?: ('active' | 'inactive' | 'error')[];
  business_unit?: string[];
  enabled?: boolean;
  search?: string;
}

export interface SortOptions {
  field: keyof NamespaceSchedule;
  direction: 'asc' | 'desc';
}

export interface PaginationOptions {
  page: number;
  per_page: number;
  total: number;
}

// Component Props Types
export interface BaseComponentProps {
  className?: string;
  'data-testid'?: string;
}

export interface LoadingState {
  loading: boolean;
  error: string | null;
}

export interface AsyncState<T> extends LoadingState {
  data: T | null;
}
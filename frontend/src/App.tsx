import React, { Suspense, useEffect, ErrorInfo } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, CircularProgress } from '@mui/material';
import { ErrorBoundary } from 'react-error-boundary';
import { HelmetProvider } from 'react-helmet-async';

// Components
import Layout from './components/Layout/Layout';
import ErrorFallback from './components/ErrorBoundary/ErrorFallback';
import LoadingSpinner from './components/LoadingSpinner/LoadingSpinner';

// Pages (lazy loaded)
const Dashboard = React.lazy(() => import('./pages/Dashboard/Dashboard'));
const Schedules = React.lazy(() => import('./pages/Schedules/Schedules'));
const ScheduleForm = React.lazy(() => import('./pages/ScheduleForm/ScheduleForm'));
const Monitoring = React.lazy(() => import('./pages/Monitoring/Monitoring'));
const Settings = React.lazy(() => import('./pages/Settings/Settings'));

// Hooks
import { usePerformanceMonitoring } from './hooks/usePerformanceMonitoring';
import { useWebSocket } from './hooks/useWebSocket';

// Types
import { WebSocketMessage } from './types';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
});

// Create Material-UI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
});

const App: React.FC = () => {
  // Performance monitoring
  const { trackError, trackInteraction } = usePerformanceMonitoring({
    enabled: process.env.NODE_ENV === 'production',
    onReport: (metrics) => {
      // Send metrics to monitoring service
      console.log('Performance metrics:', metrics);
    },
  });

  // WebSocket connection for real-time updates
  const webSocket = useWebSocket({
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:8081/ws',
    onMessage: (message: WebSocketMessage) => {
      console.log('WebSocket message received:', message);
      
      // Handle different message types
      switch (message.type) {
        case 'namespace_status':
          // Update namespace status in cache
          queryClient.setQueryData(['namespace-status', message.data.namespace], message.data);
          break;
        case 'scaling_operation':
          // Invalidate schedules to refresh UI
          queryClient.invalidateQueries({ queryKey: ['schedules'] });
          break;
        case 'system_metrics':
          // Update system metrics
          queryClient.setQueryData(['system-metrics'], message.data);
          break;
        case 'alert':
          // Handle alerts (could show notifications)
          console.log('Alert received:', message.data);
          break;
        case 'health_update':
          // Update health status
          queryClient.setQueryData(['system-health'], message.data);
          break;
        default:
          console.log('Unknown message type:', message.type);
      }
    },
    onConnect: () => {
      console.log('WebSocket connected');
      trackInteraction('websocket', 'connected');
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
      trackInteraction('websocket', 'disconnected');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      trackError('websocket_error', 'WebSocket connection error');
    },
  });

  // Set up global performance monitoring
  useEffect(() => {
    // Attach performance monitor to window for API service
    window.performanceMonitor = {
      trackApiCall: (endpoint: string, duration: number) => {
        // Track API call performance
        console.log(`API Call: ${endpoint} took ${duration}ms`);
      },
      trackError: (type: string, message: string) => {
        trackError(type as any, message);
      },
    };

    return () => {
      delete window.performanceMonitor;
    };
  }, [trackError]);

  // Global error handler
  const handleError = (error: Error, errorInfo: ErrorInfo) => {
    console.error('Application error:', error, errorInfo);
    trackError('component_error', error.message, error.stack);
  };

  return (
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <ErrorBoundary
            FallbackComponent={ErrorFallback}
            onError={handleError}
            onReset={() => window.location.reload()}
          >
            <Router>
              <Layout webSocketState={webSocket}>
                <Suspense
                  fallback={
                    <Box
                      display="flex"
                      justifyContent="center"
                      alignItems="center"
                      minHeight="400px"
                    >
                      <LoadingSpinner size={60} />
                    </Box>
                  }
                >
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/schedules" element={<Schedules />} />
                    <Route path="/schedules/new" element={<ScheduleForm />} />
                    <Route path="/schedules/:id/edit" element={<ScheduleForm />} />
                    <Route path="/monitoring" element={<Monitoring />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Suspense>
              </Layout>
            </Router>
          </ErrorBoundary>
          
          {/* React Query DevTools (only in development) */}
          {process.env.NODE_ENV === 'development' && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </ThemeProvider>
      </QueryClientProvider>
    </HelmetProvider>
  );
};

export default App;
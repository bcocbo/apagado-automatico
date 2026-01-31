import { useEffect, useRef, useState, useCallback } from 'react';
import { PerformanceMetrics, UserInteraction, ErrorEvent } from '../types';

interface UsePerformanceMonitoringOptions {
  enabled?: boolean;
  sampleRate?: number;
  reportInterval?: number;
  onReport?: (metrics: PerformanceMetrics) => void;
}

export const usePerformanceMonitoring = (options: UsePerformanceMonitoringOptions = {}) => {
  const {
    enabled = true,
    sampleRate = 1.0,
    reportInterval = 30000, // 30 seconds
    onReport
  } = options;

  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    page_load_time: 0,
    api_response_times: {},
    user_interactions: [],
    errors: [],
    connection_status: navigator.onLine ? 'online' : 'offline'
  });

  const startTimeRef = useRef<number>(Date.now());
  const reportIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const interactionsRef = useRef<UserInteraction[]>([]);
  const errorsRef = useRef<ErrorEvent[]>([]);
  const apiTimesRef = useRef<Record<string, number>>({});

  // Track page load time
  useEffect(() => {
    if (!enabled) return;

    const measurePageLoad = () => {
      if (performance && performance.timing) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        setMetrics(prev => ({ ...prev, page_load_time: loadTime }));
      }
    };

    if (document.readyState === 'complete') {
      measurePageLoad();
    } else {
      window.addEventListener('load', measurePageLoad);
      return () => window.removeEventListener('load', measurePageLoad);
    }
  }, [enabled]);

  // Track user interactions
  const trackInteraction = useCallback((
    type: UserInteraction['type'],
    element: string,
    duration?: number
  ) => {
    if (!enabled || Math.random() > sampleRate) return;

    const interaction: UserInteraction = {
      type,
      element,
      timestamp: new Date().toISOString(),
      duration
    };

    interactionsRef.current.push(interaction);
    
    // Keep only last 100 interactions to prevent memory issues
    if (interactionsRef.current.length > 100) {
      interactionsRef.current = interactionsRef.current.slice(-100);
    }

    setMetrics(prev => ({
      ...prev,
      user_interactions: [...interactionsRef.current]
    }));
  }, [enabled, sampleRate]);

  // Track API response times
  const trackApiCall = useCallback((endpoint: string, responseTime: number) => {
    if (!enabled) return;

    apiTimesRef.current[endpoint] = responseTime;
    setMetrics(prev => ({
      ...prev,
      api_response_times: { ...apiTimesRef.current }
    }));
  }, [enabled]);

  // Track errors
  const trackError = useCallback((
    type: ErrorEvent['type'],
    message: string,
    stack?: string,
    url?: string
  ) => {
    if (!enabled) return;

    const error: ErrorEvent = {
      type,
      message,
      stack,
      url,
      timestamp: new Date().toISOString(),
      user_agent: navigator.userAgent
    };

    errorsRef.current.push(error);
    
    // Keep only last 50 errors
    if (errorsRef.current.length > 50) {
      errorsRef.current = errorsRef.current.slice(-50);
    }

    setMetrics(prev => ({
      ...prev,
      errors: [...errorsRef.current]
    }));
  }, [enabled]);

  // Track memory usage (if available)
  const updateMemoryUsage = useCallback(() => {
    if (!enabled) return;

    if ('memory' in performance) {
      const memoryInfo = (performance as any).memory;
      setMetrics(prev => ({
        ...prev,
        memory_usage: memoryInfo.usedJSHeapSize
      }));
    }
  }, [enabled]);

  // Track connection status
  useEffect(() => {
    if (!enabled) return;

    const handleOnline = () => {
      setMetrics(prev => ({ ...prev, connection_status: 'online' }));
    };

    const handleOffline = () => {
      setMetrics(prev => ({ ...prev, connection_status: 'offline' }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enabled]);

  // Set up global error tracking
  useEffect(() => {
    if (!enabled) return;

    const handleError = (event: ErrorEvent) => {
      trackError('component_error', event.message, event.error?.stack, event.filename);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      trackError('api_error', event.reason?.message || 'Unhandled promise rejection');
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [enabled, trackError]);

  // Set up automatic reporting
  useEffect(() => {
    if (!enabled || !onReport) return;

    reportIntervalRef.current = setInterval(() => {
      updateMemoryUsage();
      onReport(metrics);
    }, reportInterval);

    return () => {
      if (reportIntervalRef.current) {
        clearInterval(reportIntervalRef.current);
      }
    };
  }, [enabled, onReport, reportInterval, metrics, updateMemoryUsage]);

  // Add click tracking to document
  useEffect(() => {
    if (!enabled) return;

    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const element = target.tagName.toLowerCase() + 
        (target.id ? `#${target.id}` : '') +
        (target.className ? `.${target.className.split(' ').join('.')}` : '');
      
      trackInteraction('click', element);
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [enabled, trackInteraction]);

  // Performance observer for navigation timing
  useEffect(() => {
    if (!enabled || !('PerformanceObserver' in window)) return;

    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          if (entry.entryType === 'navigation') {
            const navEntry = entry as PerformanceNavigationTiming;
            setMetrics(prev => ({
              ...prev,
              page_load_time: navEntry.loadEventEnd - navEntry.fetchStart
            }));
          }
        });
      });

      observer.observe({ entryTypes: ['navigation'] });

      return () => observer.disconnect();
    } catch (error) {
      console.warn('PerformanceObserver not supported:', error);
    }
  }, [enabled]);

  return {
    metrics,
    trackInteraction,
    trackApiCall,
    trackError,
    updateMemoryUsage
  };
};
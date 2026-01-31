import { useState, useEffect, useCallback } from 'react';

interface OfflineData {
  [key: string]: {
    data: any;
    timestamp: number;
    ttl: number; // Time to live in milliseconds
  };
}

interface UseOfflineCapabilityOptions {
  storageKey?: string;
  defaultTTL?: number; // Default TTL in milliseconds
}

export const useOfflineCapability = (options: UseOfflineCapabilityOptions = {}) => {
  const {
    storageKey = 'namespace-controller-offline-data',
    defaultTTL = 5 * 60 * 1000, // 5 minutes default
  } = options;

  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineData, setOfflineData] = useState<OfflineData>({});

  // Load cached data from localStorage on mount
  useEffect(() => {
    try {
      const cached = localStorage.getItem(storageKey);
      if (cached) {
        const parsedData = JSON.parse(cached);
        setOfflineData(parsedData);
      }
    } catch (error) {
      console.error('Failed to load offline data:', error);
    }
  }, [storageKey]);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Save data to cache
  const cacheData = useCallback((key: string, data: any, ttl: number = defaultTTL) => {
    const cacheEntry = {
      data,
      timestamp: Date.now(),
      ttl,
    };

    const newOfflineData = {
      ...offlineData,
      [key]: cacheEntry,
    };

    setOfflineData(newOfflineData);

    try {
      localStorage.setItem(storageKey, JSON.stringify(newOfflineData));
    } catch (error) {
      console.error('Failed to save offline data:', error);
    }
  }, [offlineData, storageKey, defaultTTL]);

  // Get cached data
  const getCachedData = useCallback((key: string) => {
    const cached = offlineData[key];
    
    if (!cached) {
      return null;
    }

    // Check if data has expired
    const now = Date.now();
    if (now - cached.timestamp > cached.ttl) {
      // Data has expired, remove it
      const newOfflineData = { ...offlineData };
      delete newOfflineData[key];
      setOfflineData(newOfflineData);
      
      try {
        localStorage.setItem(storageKey, JSON.stringify(newOfflineData));
      } catch (error) {
        console.error('Failed to update offline data:', error);
      }
      
      return null;
    }

    return cached.data;
  }, [offlineData, storageKey]);

  // Check if cached data exists and is valid
  const hasCachedData = useCallback((key: string) => {
    return getCachedData(key) !== null;
  }, [getCachedData]);

  // Clear all cached data
  const clearCache = useCallback(() => {
    setOfflineData({});
    try {
      localStorage.removeItem(storageKey);
    } catch (error) {
      console.error('Failed to clear offline data:', error);
    }
  }, [storageKey]);

  // Clear specific cached data
  const clearCachedData = useCallback((key: string) => {
    const newOfflineData = { ...offlineData };
    delete newOfflineData[key];
    setOfflineData(newOfflineData);

    try {
      localStorage.setItem(storageKey, JSON.stringify(newOfflineData));
    } catch (error) {
      console.error('Failed to clear cached data:', error);
    }
  }, [offlineData, storageKey]);

  // Get cache statistics
  const getCacheStats = useCallback(() => {
    const keys = Object.keys(offlineData);
    const now = Date.now();
    
    const stats = {
      totalEntries: keys.length,
      validEntries: 0,
      expiredEntries: 0,
      totalSize: 0,
    };

    keys.forEach(key => {
      const entry = offlineData[key];
      if (now - entry.timestamp <= entry.ttl) {
        stats.validEntries++;
      } else {
        stats.expiredEntries++;
      }
    });

    try {
      const serialized = JSON.stringify(offlineData);
      stats.totalSize = new Blob([serialized]).size;
    } catch (error) {
      console.error('Failed to calculate cache size:', error);
    }

    return stats;
  }, [offlineData]);

  return {
    isOnline,
    cacheData,
    getCachedData,
    hasCachedData,
    clearCache,
    clearCachedData,
    getCacheStats,
  };
};
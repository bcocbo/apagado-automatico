import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { NamespaceSchedule, CreateScheduleRequest, UpdateScheduleRequest, ApiResponse } from '../types';
import { scheduleApi } from '../services/api';

export const useSchedules = () => {
  return useQuery({
    queryKey: ['schedules'],
    queryFn: scheduleApi.getAll,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};

export const useSchedule = (id: string) => {
  return useQuery({
    queryKey: ['schedule', id],
    queryFn: () => scheduleApi.getById(id),
    enabled: !!id,
    staleTime: 30000,
  });
};

export const useCreateSchedule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateScheduleRequest) => scheduleApi.create(data),
    onSuccess: (newSchedule) => {
      // Update the schedules list cache
      queryClient.setQueryData(['schedules'], (old: NamespaceSchedule[] | undefined) => {
        return old ? [...old, newSchedule] : [newSchedule];
      });

      // Invalidate and refetch schedules to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error) => {
      console.error('Failed to create schedule:', error);
    },
  });
};

export const useUpdateSchedule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateScheduleRequest) => scheduleApi.update(data.id, data),
    onSuccess: (updatedSchedule, variables) => {
      // Update the specific schedule cache
      queryClient.setQueryData(['schedule', variables.id], updatedSchedule);

      // Update the schedules list cache
      queryClient.setQueryData(['schedules'], (old: NamespaceSchedule[] | undefined) => {
        return old?.map(schedule => 
          schedule.id === variables.id ? updatedSchedule : schedule
        ) || [];
      });

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error) => {
      console.error('Failed to update schedule:', error);
    },
  });
};

export const useDeleteSchedule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => scheduleApi.delete(id),
    onSuccess: (_, deletedId) => {
      // Remove from schedules list cache
      queryClient.setQueryData(['schedules'], (old: NamespaceSchedule[] | undefined) => {
        return old?.filter(schedule => schedule.id !== deletedId) || [];
      });

      // Remove the specific schedule cache
      queryClient.removeQueries({ queryKey: ['schedule', deletedId] });

      // Invalidate schedules list
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
    onError: (error) => {
      console.error('Failed to delete schedule:', error);
    },
  });
};

export const useToggleSchedule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      scheduleApi.update(id, { enabled }),
    onSuccess: (updatedSchedule, variables) => {
      // Update caches
      queryClient.setQueryData(['schedule', variables.id], updatedSchedule);
      queryClient.setQueryData(['schedules'], (old: NamespaceSchedule[] | undefined) => {
        return old?.map(schedule => 
          schedule.id === variables.id ? updatedSchedule : schedule
        ) || [];
      });
    },
    onError: (error) => {
      console.error('Failed to toggle schedule:', error);
    },
  });
};

// Hook for optimistic updates
export const useOptimisticScheduleUpdate = () => {
  const queryClient = useQueryClient();

  const updateScheduleOptimistically = (id: string, updates: Partial<NamespaceSchedule>) => {
    // Optimistically update the cache
    queryClient.setQueryData(['schedule', id], (old: NamespaceSchedule | undefined) => {
      return old ? { ...old, ...updates } : undefined;
    });

    queryClient.setQueryData(['schedules'], (old: NamespaceSchedule[] | undefined) => {
      return old?.map(schedule => 
        schedule.id === id ? { ...schedule, ...updates } : schedule
      ) || [];
    });
  };

  const revertOptimisticUpdate = (id: string) => {
    // Invalidate to refetch from server
    queryClient.invalidateQueries({ queryKey: ['schedule', id] });
    queryClient.invalidateQueries({ queryKey: ['schedules'] });
  };

  return {
    updateScheduleOptimistically,
    revertOptimisticUpdate,
  };
};
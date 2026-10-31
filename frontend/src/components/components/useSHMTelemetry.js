import { useSHMTelemetry as useSharedTelemetry } from './hooks/useSHMTelemetry';

export function useSHMTelemetry() {
  return useSharedTelemetry({fallbackUrl: 'ws://127.0.0.1:8010/ws/shm_telemetry', useBackendUrl: true, retryDelay: 5000});
}

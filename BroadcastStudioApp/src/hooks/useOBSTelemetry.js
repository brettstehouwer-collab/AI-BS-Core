/** Compatibility export for retired external-engine telemetry.
 * No socket, retry loop, credential use or scene dispatch remains.
 */
export function useOBSTelemetry() {
  return {
    connected: false,
    telemetry: {
      fps: null, cpuUsage: null, memoryUsage: null, freeDiskSpace: null,
      activeScene: null, streaming: null, recording: null,
    },
    setScene: () => false,
  };
}

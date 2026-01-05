import type { DevPodStatus } from '../types.js';

/**
 * Format a DevPod status for display.
 */
export function formatDevPodStatus(status: DevPodStatus): string {
  const statusMap: Record<DevPodStatus, string> = {
    idle: 'Idle',
    running: 'Running',
    stale: 'Stale',
    unknown: 'Unknown',
  };
  return statusMap[status];
}

/**
 * Check if a DevPod status indicates activity.
 */
export function isActiveStatus(status: DevPodStatus): boolean {
  return status === 'running';
}

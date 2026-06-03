export const ACTIVE_DEVICE_THRESHOLD_MS = 24 * 60 * 60 * 1000

export function isDeviceActive(lastSeenAt: string, now = Date.now()): boolean {
  return now - new Date(lastSeenAt).getTime() <= ACTIVE_DEVICE_THRESHOLD_MS
}

export function formatLastSeen(lastSeenAt: string): string {
  const diffMs = Date.now() - new Date(lastSeenAt).getTime()
  const minutes = Math.floor(diffMs / 60_000)

  if (minutes < 1) {
    return "Just now"
  }
  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `${hours}h ago`
  }

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

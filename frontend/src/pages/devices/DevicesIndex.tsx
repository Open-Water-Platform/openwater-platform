import { Navigate } from "react-router-dom"

import { DeviceEmptyState } from "@/components/devices/device-empty-state"
import { isDeviceActive } from "@/lib/device-status"
import { useDevices } from "@/hooks/use-devices"

export default function DevicesIndex() {
  const { devices, loading, error } = useDevices()

  if (loading) {
    return null
  }

  if (error) {
    return (
      <DeviceEmptyState
        title="Unable to load devices"
        description={error}
      />
    )
  }

  if (devices.length === 0) {
    return (
      <DeviceEmptyState
        title="No devices registered"
        description="When field devices connect, they will appear in the sidebar."
      />
    )
  }

  const defaultDevice =
    devices.find((device) => isDeviceActive(device.last_seen_at)) ?? devices[0]

  return <Navigate to={`/devices/${defaultDevice.device_id}`} replace />
}

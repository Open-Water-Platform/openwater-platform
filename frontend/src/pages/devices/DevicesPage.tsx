import { Outlet } from "react-router-dom"

import { DeviceSidebar } from "@/components/devices/device-sidebar"
import { useDevices } from "@/hooks/use-devices"

export default function DevicesPage() {
  const { devices, loading } = useDevices()

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      <DeviceSidebar devices={devices} loading={loading} />
      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  )
}

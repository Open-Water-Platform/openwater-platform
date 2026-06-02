import { Outlet } from "react-router-dom"

import { DeviceSidebar } from "@/components/devices/device-sidebar"
import { useDevices } from "@/hooks/use-devices"

export default function DevicesPage() {
  const { devices, loading } = useDevices()

  return (
    <div className="flex min-h-0 flex-1">
      <DeviceSidebar devices={devices} loading={loading} />
      <div className="flex min-w-0 flex-1 flex-col overflow-auto">
        <Outlet />
      </div>
    </div>
  )
}

import { Skeleton } from "@/components/ui/skeleton"
import { DeviceSidebarItem } from "@/components/devices/device-sidebar-item"
import { isDeviceActive } from "@/lib/device-status"
import type { Device } from "@/types/api"

export function DeviceSidebar({
  devices,
  loading,
}: {
  devices: Device[]
  loading: boolean
}) {
  const activeDevices = devices.filter((device) =>
    isDeviceActive(device.last_seen_at),
  )
  const inactiveDevices = devices.filter(
    (device) => !isDeviceActive(device.last_seen_at),
  )

  return (
    <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col overflow-hidden border-r bg-background">
      <div className="shrink-0 border-b px-4 py-3">
        <h2 className="text-sm font-medium">Devices</h2>
        <p className="text-xs text-muted-foreground">
          {activeDevices.length} active · {devices.length} total
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="space-y-2 px-2 py-1">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {activeDevices.length > 0 ? (
              <div className="space-y-1">
                <p className="px-3 text-xs font-medium text-muted-foreground">
                  Active
                </p>
                {activeDevices.map((device) => (
                  <DeviceSidebarItem key={device.device_id} device={device} />
                ))}
              </div>
            ) : null}
            {inactiveDevices.length > 0 ? (
              <div className="space-y-1">
                <p className="px-3 text-xs font-medium text-muted-foreground">
                  Inactive
                </p>
                {inactiveDevices.map((device) => (
                  <DeviceSidebarItem key={device.device_id} device={device} />
                ))}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </aside>
  )
}

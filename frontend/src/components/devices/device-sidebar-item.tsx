import { NavLink } from "react-router-dom"

import { formatLastSeen, isDeviceActive } from "@/lib/device-status"
import { cn } from "@/lib/utils"
import type { Device } from "@/types/api"

export function DeviceSidebarItem({ device }: { device: Device }) {
  const active = isDeviceActive(device.last_seen_at)

  return (
    <NavLink
      to={`/devices/${device.device_id}`}
      className={({ isActive }) =>
        cn(
          "flex flex-col gap-1 rounded-md border border-transparent px-3 py-2 text-sm transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          isActive && "border-border bg-sidebar-accent text-sidebar-accent-foreground",
        )
      }
    >
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 shrink-0 rounded-full",
            active ? "bg-emerald-500" : "bg-muted-foreground/40",
          )}
          aria-hidden="true"
        />
        <span className="truncate font-medium">{device.device_id}</span>
      </div>
      <span className="pl-4 text-xs text-muted-foreground">
        {active ? "Active" : "Inactive"} · {formatLastSeen(device.last_seen_at)}
      </span>
    </NavLink>
  )
}

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import type { Device } from "@/types/api"

export function DeviceMetadataCard({ device }: { device: Device }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{device.device_id}</CardTitle>
        <CardDescription>Device metadata</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <p className="text-muted-foreground">Firmware</p>
          <p className="font-medium">{device.firmware_version ?? "Unknown"}</p>
        </div>
        <div>
          <p className="text-muted-foreground">First seen</p>
          <p className="font-medium">
            {new Date(device.first_seen_at).toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Last seen</p>
          <p className="font-medium">
            {new Date(device.last_seen_at).toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Location</p>
          <p className="font-medium">
            {device.location
              ? `${device.location.lat.toFixed(4)}, ${device.location.lon.toFixed(4)}`
              : "Not set"}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

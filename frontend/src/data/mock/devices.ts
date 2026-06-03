import type { Device } from "@/types/api"

const hoursAgo = (hours: number) =>
  new Date(Date.now() - hours * 60 * 60 * 1000).toISOString()

const daysAgo = (days: number) => hoursAgo(days * 24)

export const mockDevices: Device[] = [
  {
    device_id: "sensor-001",
    first_seen_at: daysAgo(45),
    last_seen_at: hoursAgo(1),
    firmware_version: "1.2.0",
    location: { lat: 51.5074, lon: -0.1278 },
  },
  {
    device_id: "sensor-002",
    first_seen_at: daysAgo(30),
    last_seen_at: hoursAgo(3),
    firmware_version: "1.2.0",
    location: { lat: 51.4545, lon: -2.5879 },
  },
  {
    device_id: "sensor-003",
    first_seen_at: daysAgo(14),
    last_seen_at: hoursAgo(6),
    firmware_version: "1.1.4",
    location: { lat: 53.4808, lon: -2.2426 },
  },
  {
    device_id: "sensor-004",
    first_seen_at: daysAgo(60),
    last_seen_at: daysAgo(3),
    firmware_version: "1.0.9",
    location: null,
  },
]

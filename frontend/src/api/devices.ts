import { mockDevices } from "@/data/mock/devices"
import type { Device, Paginated } from "@/types/api"

const MOCK_DELAY_MS = 250

function delay(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export async function listDevices(
  limit = 50,
  offset = 0,
): Promise<Paginated<Device>> {
  await delay(MOCK_DELAY_MS)

  const items = mockDevices.slice(offset, offset + limit)
  return {
    items,
    limit,
    offset,
    total: mockDevices.length,
  }
}

export async function getDevice(deviceId: string): Promise<Device | null> {
  await delay(MOCK_DELAY_MS)
  return mockDevices.find((device) => device.device_id === deviceId) ?? null
}

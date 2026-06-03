import {
  getMockLatestReadings,
  getMockReadings,
} from "@/data/mock/readings"
import type { Paginated, Reading, ReadingsQuery } from "@/types/api"

const MOCK_DELAY_MS = 250

function delay(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export async function latestReadings(deviceId: string): Promise<Reading[]> {
  await delay(MOCK_DELAY_MS)
  return getMockLatestReadings(deviceId)
}

export async function listReadings(
  deviceId: string,
  query: ReadingsQuery = {},
): Promise<Paginated<Reading>> {
  await delay(MOCK_DELAY_MS)

  const parameter = query.parameter ?? "ph"
  const days =
    query.from !== undefined
      ? Math.ceil(
          (Date.now() - new Date(query.from).getTime()) / (24 * 60 * 60 * 1000),
        )
      : 90

  let items = getMockReadings(deviceId, parameter, days)

  if (query.to) {
    const toTime = new Date(query.to).getTime()
    items = items.filter(
      (reading) => new Date(reading.recorded_at).getTime() <= toTime,
    )
  }

  if (query.order === "desc") {
    items = [...items].reverse()
  }

  const offset = query.offset ?? 0
  const limit = query.limit ?? items.length
  const page = items.slice(offset, offset + limit)

  return {
    items: page,
    limit,
    offset,
    total: items.length,
  }
}

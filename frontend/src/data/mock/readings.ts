import type { Reading } from "@/types/api"

const PARAMETERS = [
  { parameter: "ph", unit: "pH", base: 7.2, variance: 0.4 },
  { parameter: "temperature", unit: "°C", base: 18.5, variance: 3 },
  { parameter: "turbidity", unit: "NTU", base: 4.2, variance: 1.5 },
  { parameter: "flow_rate", unit: "L/min", base: 12, variance: 4 },
] as const

function seededValue(deviceId: string, parameter: string, dayOffset: number): number {
  const config = PARAMETERS.find((entry) => entry.parameter === parameter)
  if (!config) {
    return 0
  }

  let hash = 0
  const key = `${deviceId}:${parameter}:${dayOffset}`
  for (let index = 0; index < key.length; index += 1) {
    hash = (hash << 5) - hash + key.charCodeAt(index)
    hash |= 0
  }

  const wave = Math.sin(dayOffset / 4 + hash) * config.variance
  return Number((config.base + wave).toFixed(2))
}

function buildSeries(deviceId: string, parameter: string, days: number): Reading[] {
  const readings: Reading[] = []

  for (let day = days; day >= 0; day -= 1) {
    const recordedAt = new Date(Date.now() - day * 24 * 60 * 60 * 1000)
    recordedAt.setHours(12, 0, 0, 0)

    const config = PARAMETERS.find((entry) => entry.parameter === parameter)
    if (!config) {
      continue
    }

    readings.push({
      device_id: deviceId,
      recorded_at: recordedAt.toISOString(),
      parameter,
      value: seededValue(deviceId, parameter, day),
      unit: config.unit,
    })
  }

  return readings
}

const mockSeriesByDevice = new Map<string, Map<string, Reading[]>>()

function getDeviceSeries(deviceId: string, parameter: string): Reading[] {
  if (!mockSeriesByDevice.has(deviceId)) {
    mockSeriesByDevice.set(deviceId, new Map())
  }

  const deviceSeries = mockSeriesByDevice.get(deviceId)!
  if (!deviceSeries.has(parameter)) {
    deviceSeries.set(parameter, buildSeries(deviceId, parameter, 90))
  }

  return deviceSeries.get(parameter)!
}

export function getMockLatestReadings(deviceId: string): Reading[] {
  return PARAMETERS.map((config) => {
    const series = getDeviceSeries(deviceId, config.parameter)
    return series[series.length - 1]
  })
}

export function getMockReadings(
  deviceId: string,
  parameter: string,
  days: number,
): Reading[] {
  const series = getDeviceSeries(deviceId, parameter)
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000

  return series.filter(
    (reading) => new Date(reading.recorded_at).getTime() >= cutoff,
  )
}

export const mockParameters = PARAMETERS.map((entry) => entry.parameter)

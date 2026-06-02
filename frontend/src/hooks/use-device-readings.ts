import { useEffect, useState } from "react"

import { latestReadings, listReadings } from "@/api/readings"
import type { Reading } from "@/types/api"

export type ChartRange = "7d" | "30d" | "90d"

const RANGE_DAYS: Record<ChartRange, number> = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
}

type UseDeviceReadingsState = {
  latest: Reading[]
  series: Reading[]
  loading: boolean
  error: string | null
}

export function useDeviceReadings(
  deviceId: string | undefined,
  parameter: string,
  range: ChartRange,
) {
  const [state, setState] = useState<UseDeviceReadingsState>({
    latest: [],
    series: [],
    loading: Boolean(deviceId),
    error: null,
  })

  useEffect(() => {
    if (!deviceId) {
      setState({ latest: [], series: [], loading: false, error: null })
      return
    }

    let cancelled = false
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }))

    const from = new Date(
      Date.now() - RANGE_DAYS[range] * 24 * 60 * 60 * 1000,
    ).toISOString()

    Promise.all([
      latestReadings(deviceId),
      listReadings(deviceId, {
        parameter,
        from,
        order: "asc",
      }),
    ])
      .then(([latest, readingsPage]) => {
        if (!cancelled) {
          setState({
            latest,
            series: readingsPage.items,
            loading: false,
            error: null,
          })
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            latest: [],
            series: [],
            loading: false,
            error:
              error instanceof Error
                ? error.message
                : "Failed to load readings",
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [deviceId, parameter, range])

  return state
}

export { RANGE_DAYS }

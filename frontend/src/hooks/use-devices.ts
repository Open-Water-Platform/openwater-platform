import { useEffect, useState } from "react"

import { listDevices } from "@/api/devices"
import type { Device } from "@/types/api"

type UseDevicesState = {
  devices: Device[]
  loading: boolean
  error: string | null
}

export function useDevices() {
  const [state, setState] = useState<UseDevicesState>({
    devices: [],
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    listDevices()
      .then((response) => {
        if (!cancelled) {
          setState({
            devices: response.items,
            loading: false,
            error: null,
          })
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            devices: [],
            loading: false,
            error:
              error instanceof Error ? error.message : "Failed to load devices",
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return state
}

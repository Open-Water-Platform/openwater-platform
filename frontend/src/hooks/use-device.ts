import { useEffect, useState } from "react"

import { getDevice } from "@/api/devices"
import type { Device } from "@/types/api"

type UseDeviceState = {
  device: Device | null
  loading: boolean
  error: string | null
}

export function useDevice(deviceId: string | undefined) {
  const [state, setState] = useState<UseDeviceState>({
    device: null,
    loading: Boolean(deviceId),
    error: null,
  })

  useEffect(() => {
    if (!deviceId) {
      setState({ device: null, loading: false, error: null })
      return
    }

    let cancelled = false
    setState({ device: null, loading: true, error: null })

    getDevice(deviceId)
      .then((device) => {
        if (cancelled) {
          return
        }

        if (!device) {
          setState({
            device: null,
            loading: false,
            error: "Device not found",
          })
          return
        }

        setState({ device, loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            device: null,
            loading: false,
            error:
              error instanceof Error ? error.message : "Failed to load device",
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [deviceId])

  return state
}

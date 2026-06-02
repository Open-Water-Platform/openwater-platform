import { useState } from "react"
import { useParams } from "react-router-dom"

import { DeviceEmptyState } from "@/components/devices/device-empty-state"
import { DeviceKpiCards } from "@/components/devices/device-kpi-cards"
import { DeviceMetadataCard } from "@/components/devices/device-metadata-card"
import { DeviceReadingsChart } from "@/components/devices/device-readings-chart"
import { useDevice } from "@/hooks/use-device"
import {
  useDeviceReadings,
  type ChartRange,
} from "@/hooks/use-device-readings"

export default function DeviceAnalytics() {
  const { deviceId } = useParams()
  const [parameter, setParameter] = useState("ph")
  const [range, setRange] = useState<ChartRange>("30d")

  const { device, loading: deviceLoading, error: deviceError } =
    useDevice(deviceId)
  const {
    latest,
    series,
    loading: readingsLoading,
    error: readingsError,
  } = useDeviceReadings(deviceId, parameter, range)

  if (deviceLoading) {
    return null
  }

  if (deviceError || !device) {
    return (
      <DeviceEmptyState
        title="Device not found"
        description={
          deviceError ??
          "Select a device from the sidebar or choose a different device."
        }
      />
    )
  }

  const error = readingsError

  return (
    <div className="flex flex-col gap-4 p-4 md:gap-6 md:p-6">
      <DeviceMetadataCard device={device} />
      {error ? (
        <DeviceEmptyState
          title="Unable to load readings"
          description={error}
        />
      ) : (
        <>
          <DeviceKpiCards readings={latest} loading={readingsLoading} />
          <DeviceReadingsChart
            readings={series}
            loading={readingsLoading}
            parameter={parameter}
            range={range}
            onParameterChange={setParameter}
            onRangeChange={setRange}
          />
        </>
      )}
    </div>
  )
}

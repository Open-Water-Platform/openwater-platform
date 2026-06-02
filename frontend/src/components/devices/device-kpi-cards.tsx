import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { Reading } from "@/types/api"

function formatParameterLabel(parameter: string) {
  return parameter
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function DeviceKpiCards({
  readings,
  loading,
}: {
  readings: Reading[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {readings.map((reading) => (
        <Card key={reading.parameter}>
          <CardHeader>
            <CardDescription>{formatParameterLabel(reading.parameter)}</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums">
              {reading.value}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                {reading.unit}
              </span>
            </CardTitle>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

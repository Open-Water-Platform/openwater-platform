import { useMemo } from "react"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { mockParameters } from "@/data/mock/readings"
import type { ChartRange } from "@/hooks/use-device-readings"
import { Skeleton } from "@/components/ui/skeleton"
import type { Reading } from "@/types/api"

function formatParameterLabel(parameter: string) {
  return parameter
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function DeviceReadingsChart({
  readings,
  loading,
  parameter,
  range,
  onParameterChange,
  onRangeChange,
}: {
  readings: Reading[]
  loading: boolean
  parameter: string
  range: ChartRange
  onParameterChange: (parameter: string) => void
  onRangeChange: (range: ChartRange) => void
}) {
  const chartData = useMemo(
    () =>
      readings.map((reading) => ({
        date: reading.recorded_at,
        value: reading.value,
      })),
    [readings],
  )

  const chartConfig = {
    value: {
      label: formatParameterLabel(parameter),
      color: "var(--chart-1)",
    },
  } satisfies ChartConfig

  const unit = readings[0]?.unit ?? ""

  return (
    <Card>
      <CardHeader className="gap-4 border-b @container/card-header sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>{formatParameterLabel(parameter)}</CardTitle>
          <CardDescription>
            Historical readings for the selected device
          </CardDescription>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Select
            value={parameter}
            onValueChange={(value) => {
              if (value !== null) {
                onParameterChange(value)
              }
            }}
          >
            <SelectTrigger className="w-40" size="sm">
              <SelectValue placeholder="Parameter" />
            </SelectTrigger>
            <SelectContent>
              {mockParameters.map((entry) => (
                <SelectItem key={entry} value={entry}>
                  {formatParameterLabel(entry)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <ToggleGroup
            multiple={false}
            value={range ? [range] : []}
            onValueChange={(value) => {
              const next = value[0]
              if (next) {
                onRangeChange(next as ChartRange)
              }
            }}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="90d">90d</ToggleGroupItem>
            <ToggleGroupItem value="30d">30d</ToggleGroupItem>
            <ToggleGroupItem value="7d">7d</ToggleGroupItem>
          </ToggleGroup>
        </div>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {loading ? (
          <Skeleton className="aspect-auto h-[250px] w-full" />
        ) : (
          <ChartContainer
            config={chartConfig}
            className="aspect-auto h-[250px] w-full"
          >
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="fillValue" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor="var(--color-value)"
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor="var(--color-value)"
                    stopOpacity={0.1}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={32}
                tickFormatter={(value) =>
                  new Date(value).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })
                }
              />
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent
                    labelFormatter={(value) =>
                      new Date(value).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })
                    }
                    formatter={(value) => [`${value} ${unit}`, "Value"]}
                    indicator="dot"
                  />
                }
              />
              <Area
                dataKey="value"
                type="natural"
                fill="url(#fillValue)"
                stroke="var(--color-value)"
              />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}

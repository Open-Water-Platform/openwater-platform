export type Location = {
  lat: number
  lon: number
}

export type Device = {
  device_id: string
  first_seen_at: string
  last_seen_at: string
  firmware_version: string | null
  location: Location | null
}

export type Reading = {
  device_id: string
  recorded_at: string
  parameter: string
  value: number
  unit: string
}

export type Paginated<T> = {
  items: T[]
  limit: number
  offset: number
  total: number
}

export type ReadingsQuery = {
  from?: string
  to?: string
  parameter?: string
  limit?: number
  offset?: number
  order?: "asc" | "desc"
}

import toast from 'svelte-french-toast'

export const backend_url = 'https://pumptech.surf/api'

type PumpStrategy = {
  '1.1': boolean
  '1.2': boolean
  '1.3': boolean
  '1.4': boolean
  '2.1': boolean
  '2.2': boolean
  '2.3': boolean
  '2.4': boolean
}

type PerformanceCurve = {
  head_values: number[]
  flow_values: number[]
}

type PumpData = {
  pump_name: string
  performance_curve: PerformanceCurve
  values_24h: number[]
}

export type SimulationDTO = {
  id: string
  name: string
  timestamp: string
  timestamps_24h: string[]
  rain_forecast_24h: number[]
  electricity_price_24h: number[]
  inflow_estimate_24h: number[]
  pumping_strategy_24h: PumpStrategy[]
  water_level_estimate_24h: number[]
  electricity_consumption_24h: number[]
  cost_24h: number[]
  pumps: PumpData[]
  total_cost: number
  starting_water_level: number
}

export type SimulationMetadataDTO = {
  id: string
  name: string
  timestamp: string

  // Value summary fields
  total_cost: number
  starting_water_level: number
  average_water_level: number
  total_electricity_consumption: number
}

export const getSimulation = async (id: string, f?: typeof fetch): Promise<SimulationDTO> => {
  const response = await (f || fetch)(`${backend_url}/simulations/${id}`)
  if (!response.ok) {
    const data = await response.json()
    toast.error(data.detail || 'Failed to fetch simulation')
    throw new Error(`Failed to fetch simulation: ${response.statusText}`)
  }
  return response.json()
}

export const generateNewSimulation = async (name?: string): Promise<SimulationDTO> => {
  const response = await fetch(`${backend_url}/simulate`, {
    method: 'POST',
    body: name ? JSON.stringify({ name }) : undefined,
    headers: {
      'Content-Type': 'application/json'
    }
  })
  if (!response.ok) {
    const data = await response.json()
    toast.error(data.detail || 'Failed to generate simulation')
    throw new Error(`Failed to generate simulation: ${response.statusText}`)
  }
  toast.success('Simulation generated successfully')
  return response.json()
}

export const getAllSimulations = async (f?: typeof fetch): Promise<SimulationMetadataDTO[]> => {
  const response = await (f || fetch)(`${backend_url}/simulations`)
  if (!response.ok) {
    const data = await response.json()
    toast.error(data.detail || 'Failed to fetch simulations')
    throw new Error(`Failed to fetch simulations: ${response.statusText}`)
  }
  return response.json()
}

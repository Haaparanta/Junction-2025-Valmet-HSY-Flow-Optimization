import type { SimulationDTO } from '$lib/api'
import { getContext, setContext } from 'svelte'
import { createVector, type Vector } from './utils'

export interface Pump {
  name: string
  performanceCurve: number[][]
  forecastedUse: Vector
}

interface Simulation {
  weatherForecast: Vector
  electricityPrices: Vector
  inflowPrediction: Vector
  outflowStrategy: Vector
  simulatedWaterLevel: Vector
  simulatedElectricityUse: Vector
  simulatedPrice: Vector

  timeStamps: string[]
  simulatedPumps: Pump[]
}

export class SimulationContext {
  weatherForecast = $state(createVector([], 0))
  electricityPrices = $state(createVector([], 0))
  inflowPrediction = $state(createVector([], 0))
  outflowStrategy = $state(createVector([], 0))
  simulatedWaterLevel = $state(createVector([], 0))
  simulatedElectricityUse = $state(createVector([], 0))
  simulatedPrice = $state(createVector([], 0))
  simulatedPumps = $state<Pump[]>([])
  timeStamps = $state<string[]>([Date.now().toString()])

  currentTimeIndex = $state(0)

  current = $derived({
    weatherForecast: this.weatherForecast[this.currentTimeIndex],
    electricityPrices: this.electricityPrices[this.currentTimeIndex],
    inflowPrediction: this.inflowPrediction[this.currentTimeIndex],
    outflowStrategy: this.outflowStrategy[this.currentTimeIndex],
    simulatedWaterLevel: this.simulatedWaterLevel[this.currentTimeIndex],
    simulatedElectricityUse: this.simulatedElectricityUse[this.currentTimeIndex],
    simulatedPrice: this.simulatedPrice[this.currentTimeIndex],
    timeStamp: this.timeStamps[this.currentTimeIndex],
    simulatedPumps: this.simulatedPumps.map((pump) => ({
      ...pump,
      forecastedUse: pump.forecastedUse[this.currentTimeIndex]
    }))
  })

  setSimulation(sim: SimulationDTO) {
    this.weatherForecast = createVector(sim.rain_forecast_24h)
    this.electricityPrices = createVector(sim.electricity_price_24h)
    this.inflowPrediction = createVector(sim.inflow_estimate_24h)
    // Calculate total outflow from all pumps at each timestamp
    this.outflowStrategy = createVector(
      sim.electricity_consumption_24h.map((_, index) =>
        sim.pumps.reduce((sum, pump) => sum + pump.values_24h[index], 0)
      )
    )
    this.simulatedWaterLevel = createVector(sim.water_level_estimate_24h)
    this.simulatedElectricityUse = createVector(sim.electricity_consumption_24h)
    this.simulatedPrice = createVector(sim.cost_24h)
    this.simulatedPumps = sim.pumps.map((pump) => ({
      name: pump.pump_name,
      performanceCurve: pump.performance_curve.head_values.map((head, i) => [
        pump.performance_curve.flow_values[i],
        head
      ]),
      forecastedUse: createVector(pump.values_24h)
    }))
    this.timeStamps = sim.timestamps_24h
  }

  // For prototyping purposes
  generateDummyPump(index: number): Pump {
    const length = 96
    return {
      name: `Pump ${index + 1}`,
      performanceCurve: [
        [0, 0],
        [50, 10],
        [100, 20],
        [150, 30],
        [200, 40]
      ],
      forecastedUse: createVector(Array.from({ length }, () => Math.random() * 20))
    }
  }

  generateDummyData() {
    const length = 96
    this.weatherForecast = createVector(Array.from({ length }, () => Math.random() * 10))
    this.electricityPrices = createVector(Array.from({ length }, () => Math.random() * 0.3))
    this.inflowPrediction = createVector(Array.from({ length }, () => Math.random() * 5))
    this.outflowStrategy = createVector(Array.from({ length }, () => Math.random() * 5))
    this.simulatedWaterLevel = createVector(Array.from({ length }, () => Math.random() * 100))
    this.simulatedElectricityUse = createVector(Array.from({ length }, () => Math.random() * 20))
    this.simulatedPrice = createVector(Array.from({ length }, () => Math.random() * 0.5))
    this.timeStamps = Array.from({ length }, (_, i) => new Date(Date.now() + i * 15 * 60 * 1000).toISOString())
    this.simulatedPumps = Array.from({ length: 3 }, (_, i) => this.generateDummyPump(i))
  }
}

const SimulationContextKey = Symbol('SimulationContext')

export const createSimulationContext = () => setContext(SimulationContextKey, new SimulationContext())
export const getSimulationContext = () => getContext<SimulationContext>(SimulationContextKey)

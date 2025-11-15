import { getAllSimulations } from '$lib/api'

export const load = async ({ fetch }) => {
  const simulations = getAllSimulations(fetch)

  return {
    simulations
  }
}

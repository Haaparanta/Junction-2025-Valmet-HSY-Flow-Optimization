import { getSimulation } from '$lib/api'
import { error } from '@sveltejs/kit'

export const load = async ({ params, fetch }) => {
  const { id } = params

  try {
    const simulation = await getSimulation(id, fetch)

    return {
      simulation
    }
  } catch (err) {
    error(404, 'Simulation not found')
  }
}

import { getAllSimulations } from '$lib/api'
import { error } from '@sveltejs/kit'

export const load = async ({ fetch }) => {
  try {
    return {
      simulations: await getAllSimulations(fetch)
    }
  } catch (e) {
    error(500, "Upstream error: couldn't fetch simulations")
  }
}

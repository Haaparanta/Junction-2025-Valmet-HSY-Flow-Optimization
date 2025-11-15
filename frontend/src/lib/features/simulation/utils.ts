// 24 hours * 4 bins per hour = 96 bins (15-minute resolution)
export const DAY_VECTOR_LENGTH = 96;

// A DayVector is an array of numbers with a fixed length of 96.
// Represented as a number[] with a length property to help with static typing checks.
export type Vector = number[] & { length: typeof DAY_VECTOR_LENGTH };

export function isDayVector(v: unknown): v is Vector {
	return (
		Array.isArray(v) && v.length === DAY_VECTOR_LENGTH && v.every((n) => typeof n === 'number')
	);
}

/**
 * Create a DayVector, optionally from an input array. If the input is shorter, it's padded with `fill`.
 * If longer, it's truncated to 96 values.
 */
export function createVector(values?: number[], fill = 0): Vector {
	const arr = new Array(DAY_VECTOR_LENGTH).fill(fill) as number[];
	if (Array.isArray(values)) {
		for (let i = 0; i < DAY_VECTOR_LENGTH; i++) {
			if (i < values.length) arr[i] = values[i] as number;
		}
	}
	return arr as Vector;
}

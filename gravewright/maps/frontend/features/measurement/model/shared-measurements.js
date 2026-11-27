// Serialize local edits without replacing other participants' measurements.
import {createSharedRows, rowChanges} from '../../../shared/lib/shared-rows.js';

export const measurementChanges = rowChanges;

/** Measurement saves and scene reads carry their rows under `markers`. */
export function createSharedMeasurements(options) {
    return createSharedRows({...options, key: 'markers'});
}

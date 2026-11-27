// features/measurement/model/shared-measurements.js
import { createSharedRows, rowChanges } from "../../../shared/lib/shared-rows.js";
var measurementChanges = rowChanges;
function createSharedMeasurements(options) {
  return createSharedRows({ ...options, key: "markers" });
}
export {
  createSharedMeasurements,
  measurementChanges
};

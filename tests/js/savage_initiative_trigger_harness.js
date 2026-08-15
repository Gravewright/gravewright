const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../data/packages/rulesets/savage-worlds/scripts/character-sheet.js"),
  "utf8"
);
const start = source.indexOf("  function initiativeStateSnapshot(");
const end = source.indexOf("\n  async function observeInitiativeState", start);
if (start < 0 || end < 0) throw new Error("initiative trigger function not found");
const factory = new Function(`${source.slice(start, end)}; return shouldDealForObservedState;`);
const shouldDeal = factory();
const active = (round, ids = ["a", "b"], initiatives = ["", ""]) => ({
  active: true,
  round,
  combatants: ids.map((id, index) => ({ id, initiative: initiatives[index] || "" })),
});
const snapshot = (state) => ({
  round: Number(state.round),
  combatants: state.combatants.map((combatant) => combatant.id).sort().join("|"),
});
const roundOne = active(1);

const results = {
  initialBlank: shouldDeal(null, roundOne),
  initialPopulated: shouldDeal(null, active(1, ["a", "b"], ["A♠", "K♥"])),
  add: shouldDeal(snapshot(roundOne), active(1, ["a", "b", "c"])),
  nextPlayer: shouldDeal(snapshot(roundOne), { ...roundOne, turn_index: 1 }),
  reorderedRows: shouldDeal(snapshot(roundOne), active(1, ["b", "a"], ["K♥", "A♠"])),
  wrappedRound: shouldDeal(snapshot(roundOne), active(2)),
  repaint: shouldDeal(snapshot(roundOne), roundOne),
  inactive: shouldDeal(null, { active: false, round: 1, combatants: roundOne.combatants }),
};
process.stdout.write(JSON.stringify(results));

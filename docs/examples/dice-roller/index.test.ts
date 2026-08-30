import assert from "node:assert/strict";
import test from "node:test";
import module from "./index.js";

test("dice roller rejects an invalid die", () => {
  const instance = module({
    diagnostic: { record() {} },
    use() { throw new Error("not used by this module"); },
  });
  assert.throws(() => instance.roll(1), /between 2 and 10000/);
});

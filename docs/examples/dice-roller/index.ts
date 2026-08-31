import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "dice-roller",
  kind: "addon",
  provider: "community",
  version: "1.0.0",
  exports: { get: ["read", "write", "stat", "roll"] },
  create(ctx) {
    return {
      read(_resource: string) { return undefined; },
      write(_resource: string, _value: unknown) {},
      stat() { return { ready: true }; },
      roll(sides: number, actor = "Player") {
        if (!Number.isInteger(sides) || sides < 2 || sides > 10_000) {
          ctx.diagnostic.record({
            event: "dice.roll",
            actor,
            action: "Roll dice",
            status: "failure",
            reason: "Invalid number of sides",
          });
          throw new RangeError("sides must be an integer between 2 and 10000");
        }

        const result = Math.floor(Math.random() * sides) + 1;
        ctx.diagnostic.record({
          event: "dice.roll",
          actor,
          action: `Roll d${sides}`,
          status: "success",
          details: { sides, result },
        });
        return result;
      },
    };
  },
});

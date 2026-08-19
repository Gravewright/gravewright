# Scene zones

Scene zones are persistent, campaign-owned semantic regions in world coordinates. Packages need `scene.zones.read` to inspect visible zones and observable members, and `scene.zones.write` to mutate them under current scene authority.

Supported geometry is `circle`, `rect`, and simple `polygon` (3–256 vertices). Optional vertical bounds are inclusive. Zones use campaign, GM, or explicit-user audiences; invisible geometry never prevents server-side membership calculation.

```js
const zone = await sdk.scene.zones.create(sceneId, {
  type: "altar",
  geometry: { shape: "circle", x: 700, y: 350, radius: 140 },
  vertical: { bottom: 0, top: 20 },
  audience: { kind: "gm" },
  tags: ["holy"]
});
```

`zone.entered`, `zone.left`, and `zone.crossed` are authoritative data events. Continuous movement may cross a zone while ending outside; teleport-like mutations do not imply a path. Updates use `expectedVersion`. Deleting a zone silently discards derived membership and emits `scene.zones.changed`, not synthetic leave events. Package unload does not delete campaign-owned zones.


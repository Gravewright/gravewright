import assert from 'node:assert/strict';
import { sceneDarkness } from './scene-darkness.js';
const configured = { mode: 'dynamic', darkness: .85, lights_out: true };
assert.equal(sceneDarkness(configured), .85);
assert.equal(sceneDarkness({ ...configured, lights_out: false }), 0);
assert.equal(configured.darkness, .85); // Switching on does not erase the saved setting.
assert.equal(sceneDarkness({ ...configured, lights_out: false, effective_darkness: .85 }), 0);
assert.equal(sceneDarkness({ ...configured, mode: 'none' }), 0);
assert.equal(sceneDarkness({ ...configured, mode: 'manual' }), 0);
assert.equal(sceneDarkness({ ...configured, darkness: 0 }), 0);
assert.equal(sceneDarkness({ ...configured, effective_darkness: .4 }), .4);

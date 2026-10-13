import assert from "node:assert/strict";
import test from "node:test";
import { crossfadeCurves } from "../src/crossfade.js";

test("crossfade curves keep constant power from start to finish", () => {
  const { fadeIn, fadeOut } = crossfadeCurves();
  assert.equal(fadeIn.length, 128);
  assert.equal(fadeOut.length, 128);
  assert.equal(fadeIn[0], 0);
  assert.equal(fadeOut[0], 1);
  assert.equal(fadeIn[127], 1);
  assert.ok(Math.abs(fadeOut[127]) < 1e-6);
  for (let i = 0; i < fadeIn.length; i++) {
    assert.ok(Math.abs(fadeIn[i] ** 2 + fadeOut[i] ** 2 - 1) < 1e-6);
  }
});

import test from "node:test";
import assert from "node:assert/strict";

import {
  formatTokenCompact,
  hasTokenData,
  tokenBreakdownModel,
  tokenBreakdownPlacement,
  tokenBreakdownRows,
  tokenTotal,
} from "../src/stockroom/dashboard/static/dashboard-tokens.mjs";

test("tokenBreakdownPlacement prefers below the trigger", () => {
  /*
   * When the viewport has room beneath the trigger, place the popover
   * below so it can bleed into page space under the sessions panel.
   */
  const result = tokenBreakdownPlacement(
    { top: 100, right: 200, bottom: 120, left: 120, width: 80, height: 20 },
    { width: 176, height: 140 },
    { width: 1200, height: 800 },
    6,
  );
  assert.deepEqual(result, {
    top: 126,
    left: 120,
    placement: "below",
  });
});

test("tokenBreakdownPlacement flips above near the viewport bottom", () => {
  /*
   * When placing below would overflow the viewport, flip above the trigger
   * instead of forcing scroll inside an overflow ancestor.
   */
  const result = tokenBreakdownPlacement(
    { top: 700, right: 200, bottom: 720, left: 120, width: 80, height: 20 },
    { width: 176, height: 140 },
    { width: 1200, height: 800 },
    6,
  );
  assert.equal(result.placement, "above");
  assert.equal(result.top, 700 - 140 - 6);
  assert.equal(result.left, 120);
});

test("tokenBreakdownPlacement clamps horizontally to the viewport", () => {
  /*
   * Keep the popover fully visible when the trigger sits near the right edge.
   */
  const result = tokenBreakdownPlacement(
    { top: 100, right: 1190, bottom: 120, left: 1110, width: 80, height: 20 },
    { width: 176, height: 140 },
    { width: 1200, height: 800 },
    6,
  );
  assert.equal(result.placement, "below");
  assert.equal(result.top, 126);
  assert.equal(result.left, 1200 - 176 - 8);
});

test("hasTokenData is false for null/undefined/non-objects", () => {
  assert.equal(hasTokenData(null), false);
  assert.equal(hasTokenData(undefined), false);
  assert.equal(hasTokenData("123"), false);
  assert.equal(hasTokenData([]), false);
});

test("hasTokenData is false when any required field is missing or non-numeric", () => {
  assert.equal(hasTokenData({}), false);
  assert.equal(
    hasTokenData({
      input: 1,
      output: 2,
      cache_creation: 3,
    }),
    false,
  );
  assert.equal(
    hasTokenData({
      input: 1,
      output: "2",
      cache_creation: 3,
      cache_read: 4,
    }),
    false,
  );
  assert.equal(
    hasTokenData({
      input: 1,
      output: 2,
      cache_creation: Number.NaN,
      cache_read: 4,
    }),
    false,
  );
  assert.equal(
    hasTokenData({
      input: -1,
      output: 0,
      cache_creation: 0,
      cache_read: 0,
    }),
    false,
  );
});

test("hasTokenData is true for a tokens object including zeros", () => {
  assert.equal(
    hasTokenData({
      input: 0,
      output: 0,
      cache_creation: 0,
      cache_read: 0,
    }),
    true,
  );
});

test("tokenTotal sums the four fields", () => {
  assert.equal(
    tokenTotal({
      input: 100,
      output: 50,
      cache_creation: 0,
      cache_read: 25,
    }),
    175,
  );
});

test("tokenTotal is null when token data is absent", () => {
  assert.equal(tokenTotal(null), null);
  assert.equal(tokenTotal({}), null);
});

test("formatTokenCompact uses cursor-style K/M truncation", () => {
  assert.equal(formatTokenCompact(0), "0");
  assert.equal(formatTokenCompact(999), "999");
  assert.equal(formatTokenCompact(1000), "1K");
  assert.equal(formatTokenCompact(1234), "1.2K");
  assert.equal(formatTokenCompact(1_500_000), "1.5M");
  assert.equal(formatTokenCompact(2_000_000_000), "2B");
});

test("tokenBreakdownRows lists all four metrics with zeros preserved", () => {
  assert.deepEqual(
    tokenBreakdownRows({
      input: 10,
      output: 0,
      cache_creation: 3,
      cache_read: 0,
    }),
    [
      { label: "Input", value: 10 },
      { label: "Output", value: 0 },
      { label: "Cache write", value: 3 },
      { label: "Cache read", value: 0 },
    ],
  );
});

test("tokenBreakdownModel includes metric rows plus total for the footer", () => {
  assert.equal(tokenBreakdownModel(null), null);
  assert.deepEqual(
    tokenBreakdownModel({
      input: 10,
      output: 0,
      cache_creation: 3,
      cache_read: 0,
    }),
    {
      rows: [
        { label: "Input", value: 10 },
        { label: "Output", value: 0 },
        { label: "Cache write", value: 3 },
        { label: "Cache read", value: 0 },
      ],
      total: 13,
    },
  );
});

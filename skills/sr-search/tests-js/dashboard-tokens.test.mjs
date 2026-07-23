import test from "node:test";
import assert from "node:assert/strict";

import {
  formatTokenCompact,
  hasTokenData,
  tokenBreakdownModel,
  tokenBreakdownRows,
  tokenTotal,
} from "../src/stockroom/dashboard/static/dashboard-tokens.mjs";

test("hasTokenData is false for null/undefined/non-objects", () => {
  assert.equal(hasTokenData(null), false);
  assert.equal(hasTokenData(undefined), false);
  assert.equal(hasTokenData("123"), false);
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

test("mount decisions: absent tokens → emdash, no hover; present → compact + hover", () => {
  assert.deepEqual(
    {
      text: "—",
      hover: false,
    },
    (() => {
      if (!hasTokenData(null)) {
        return { text: "—", hover: false };
      }
      return { text: "x", hover: true };
    })(),
  );
  const tokens = {
    input: 1234,
    output: 0,
    cache_creation: 0,
    cache_read: 0,
  };
  assert.equal(hasTokenData(tokens), true);
  assert.equal(formatTokenCompact(tokenTotal(tokens)), "1.2K");
});

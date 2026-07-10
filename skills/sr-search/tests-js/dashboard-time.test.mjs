import test from "node:test";
import assert from "node:assert/strict";

import {
  formatDate,
  parseDisplayDate,
} from "../src/stockroom/dashboard/static/dashboard-core.mjs";

test("parseDisplayDate treats naive ISO datetimes as UTC", () => {
  const parsed = parseDisplayDate("2026-07-10T03:22:00");
  assert.ok(parsed);
  assert.equal(parsed.getTime(), Date.parse("2026-07-10T03:22:00Z"));
});

test("parseDisplayDate honors explicit Z and offsets", () => {
  assert.equal(
    parseDisplayDate("2026-07-10T03:22:00Z").getTime(),
    Date.parse("2026-07-10T03:22:00Z"),
  );
  assert.equal(
    parseDisplayDate("2026-07-09T22:22:00-05:00").getTime(),
    Date.parse("2026-07-10T03:22:00Z"),
  );
});

test("parseDisplayDate keeps date-only labels as local calendar midnight", () => {
  const parsed = parseDisplayDate("2026-07-10", true);
  assert.ok(parsed);
  assert.equal(parsed.getTime(), new Date("2026-07-10T00:00:00").getTime());
});

test("formatDate returns em dash for empty values", () => {
  assert.equal(formatDate(""), "—");
  assert.equal(formatDate(null), "—");
});

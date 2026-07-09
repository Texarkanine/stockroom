import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsPanel,
  buildProjectsPanel,
  buildToolsPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  chartHeight,
  deriveHarnessBreakdown,
  deriveOverviewCards,
  displayHarness,
  formatDelta,
  harnessColors,
  sortedHarnesses,
  sumAligned,
  transitionViewState,
  weightedSeries,
} from "../src/stockroom/dashboard/static/dashboard-core.mjs";

const COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#f43f5e",
  "#06b6d4",
  "#8b5cf6",
  "#ec4899",
  "#84cc16",
];

const selected = ["claude-code", "cursor"];
const colors = {
  "claude-code": COLORS[0],
  cursor: COLORS[1],
};

function assertDataset(panel, label, data) {
  const dataset = panel.datasets.find((item) => item.label === label);
  assert.ok(dataset, `missing ${label} dataset`);
  assert.deepEqual(dataset.data, data);
}

test("sorts arbitrary harnesses and cycles stable positional colors", () => {
  const raw = ["zeta", "alpha", "alpha", "nine", "beta", "eta", "gamma", "iota", "delta", "theta"];
  assert.deepEqual(sortedHarnesses(raw), [
    "alpha",
    "beta",
    "delta",
    "eta",
    "gamma",
    "iota",
    "nine",
    "theta",
    "zeta",
  ]);
  assert.deepEqual(harnessColors(raw), {
    alpha: COLORS[0],
    beta: COLORS[1],
    delta: COLORS[2],
    eta: COLORS[3],
    gamma: COLORS[4],
    iota: COLORS[5],
    nine: COLORS[6],
    theta: COLORS[7],
    zeta: COLORS[0],
  });
});

test("derives generic display labels from raw harness keys", () => {
  assert.equal(displayHarness("claude-code"), "Claude Code");
  assert.equal(displayHarness("cursor_cli"), "Cursor Cli");
  assert.equal(displayHarness("  future--harness  "), "Future Harness");
  assert.equal(displayHarness(null), "Unknown");
});

test("aggregates selected aligned series without mutating inputs", () => {
  const source = {
    cursor: [1, "2", null],
    "claude-code": [3, 4],
    ignored: [100, 100, 100],
  };
  const before = structuredClone(source);
  assert.deepEqual(sumAligned(source, selected, 4), [4, 6, 0, 0]);
  assert.deepEqual(source, before);
});

test("computes weighted averages with zero-observation guards", () => {
  const averages = { cursor: [10, 99], "claude-code": [4, 2] };
  const counts = { cursor: [1, 0], "claude-code": [3, 0] };
  assert.deepEqual(weightedSeries(averages, counts, selected), [5.5, 0]);
});

test("derives mode-independent overview cards and selected deltas", () => {
  const overview = {
    distinct_projects: 2,
    per_harness: {
      cursor: {
        sessions: 2,
        messages: 6,
        projects: 2,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 1,
      },
      "claude-code": {
        sessions: 1,
        messages: 3,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 2,
        prev_projects: 0,
      },
    },
  };
  assert.deepEqual(deriveOverviewCards(overview, selected), [
    {
      key: "sessions",
      label: "Sessions",
      value: 3,
      delta: { text: "+200%", trend: "up" },
    },
    {
      key: "messages",
      label: "Messages",
      value: 9,
      delta: { text: "+125%", trend: "up" },
    },
    {
      key: "projects",
      label: "Projects",
      value: 2,
      delta: { text: "+100%", trend: "up" },
    },
    {
      key: "average",
      label: "Avg Msgs / Session",
      value: 3,
      delta: { text: "-25%", trend: "down" },
    },
  ]);
  assert.equal(deriveOverviewCards({ per_harness: {} }, [])[3].value, 0);
});

test("derives per-harness KPI breakdown proportions", () => {
  const overview = {
    per_harness: {
      cursor: { sessions: 3, messages: 9, projects: 2 },
      "claude-code": { sessions: 1, messages: 2, projects: 1 },
    },
  };
  assert.deepEqual(deriveHarnessBreakdown(overview, selected, "sessions"), [
    {
      harness: "claude-code",
      label: "Claude Code",
      value: 1,
      share: 25,
    },
    { harness: "cursor", label: "Cursor", value: 3, share: 75 },
  ]);
  assert.deepEqual(deriveHarnessBreakdown(overview, selected, "average"), [
    {
      harness: "claude-code",
      label: "Claude Code",
      value: 2,
      share: 40,
    },
    { harness: "cursor", label: "Cursor", value: 3, share: 60 },
  ]);
  assert.deepEqual(
    deriveHarnessBreakdown({ per_harness: { cursor: {} } }, ["cursor"], "messages"),
    [{ harness: "cursor", label: "Cursor", value: 0, share: 0 }],
  );
});

test("formats percentage deltas including new and neutral values", () => {
  assert.deepEqual(formatDelta(125, 100), { text: "+25%", trend: "up" });
  assert.deepEqual(formatDelta(80, 100), { text: "-20%", trend: "down" });
  assert.deepEqual(formatDelta(2, 0), { text: "New", trend: "up" });
  assert.deepEqual(formatDelta(0, 0), { text: "No change", trend: "neutral" });
  assert.deepEqual(formatDelta(null, "bad"), { text: "No change", trend: "neutral" });
});

test("derives deterministic chart heights from label counts", () => {
  assert.equal(chartHeight(0), 240);
  assert.equal(chartHeight(3), 240);
  assert.equal(chartHeight(10), 340);
  assert.equal(chartHeight("bad"), 240);
});

test("defaults discovered harnesses and rejects an empty selection", () => {
  const initial = { harnesses: [], selected: [], mode: "aggregate" };
  const discovered = transitionViewState(initial, {
    type: "discover",
    harnesses: ["cursor", "claude-code", "cursor"],
  });
  assert.deepEqual(discovered, {
    state: {
      harnesses: ["claude-code", "cursor"],
      selected: ["claude-code", "cursor"],
      mode: "aggregate",
    },
    effect: "render",
  });
  const refused = transitionViewState(
    { harnesses: ["cursor"], selected: ["cursor"], mode: "aggregate" },
    { type: "toggle", harness: "cursor" },
  );
  assert.deepEqual(refused, {
    state: { harnesses: ["cursor"], selected: ["cursor"], mode: "aggregate" },
    effect: "none",
  });
});

test("distinguishes mode redraws from selection refetches", () => {
  const state = {
    harnesses: ["claude-code", "cursor"],
    selected: ["claude-code", "cursor"],
    mode: "aggregate",
  };
  assert.equal(
    transitionViewState(state, { type: "mode", mode: "compare" }).effect,
    "render",
  );
  assert.equal(
    transitionViewState(state, { type: "toggle", harness: "cursor" }).effect,
    "refetch",
  );
  assert.equal(
    transitionViewState(state, { type: "mode", mode: "aggregate" }).effect,
    "none",
  );
});

test("builds aggregate and compare daily activity models", () => {
  const payload = {
    days: ["2026-01-01", "2026-01-02"],
    sessions: { cursor: [1, 2], "claude-code": [3, 0] },
  };
  const aggregate = buildDailyPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "bar");
  assert.equal(aggregate.stacked, false);
  assertDataset(aggregate, "Sessions", [4, 2]);
  const compare = buildDailyPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Claude Code", [3, 0]);
  assertDataset(compare, "Cursor", [1, 2]);
});

test("builds aggregate and compare project models", () => {
  const payload = {
    projects: ["stockroom", "other"],
    sessions: { cursor: [2, 0], "claude-code": [1, 4] },
  };
  const aggregate = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.indexAxis, "y");
  assertDataset(aggregate, "Sessions", [3, 4]);
  const compare = buildProjectsPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Cursor", [2, 0]);
});

test("builds aggregate doughnut and compare tool models", () => {
  const payload = {
    tools: ["Read", "Write"],
    calls: { cursor: [3, 1], "claude-code": [2, 4] },
  };
  const aggregate = buildToolsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "doughnut");
  assertDataset(aggregate, "Calls", [5, 5]);
  const compare = buildToolsPanel(payload, selected, "compare", colors);
  assert.equal(compare.kind, "bar");
  assert.equal(compare.indexAxis, "y");
  assertDataset(compare, "Claude Code", [2, 4]);
});

test("builds blended write and read models in either mode", () => {
  const payload = {
    weeks: ["2026-01-05", "2026-01-12"],
    writes: { cursor: [2, 1], "claude-code": [1, 0] },
    reads: { cursor: [4, 2], "claude-code": [0, 3] },
  };
  for (const mode of ["aggregate", "compare"]) {
    const panel = buildWriteReadPanel(payload, selected, mode);
    assert.equal(panel.kind, "line");
    assert.equal(panel.stacked, false);
    assert.equal(panel.datasets.length, 2);
    assertDataset(panel, "Writes", [3, 1]);
    assertDataset(panel, "Reads", [4, 5]);
  }
});

test("builds aggregate and compare efficiency models", () => {
  const payload = {
    buckets: ["abandoned", "short"],
    sessions: { cursor: [1, 2], "claude-code": [3, 4] },
  };
  const aggregate = buildEfficiencyPanel(payload, selected, "aggregate", colors);
  assertDataset(aggregate, "Sessions", [4, 6]);
  const compare = buildEfficiencyPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Cursor", [1, 2]);
});

test("builds all-model aggregate and compare models", () => {
  const payload = {
    models: Array.from({ length: 10 }, (_, index) => `model-${index}`),
    sessions: {
      cursor: Array(10).fill(1),
      "claude-code": Array(10).fill(2),
    },
  };
  const aggregate = buildModelsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.labels.length, 10);
  assert.equal(aggregate.height, 340);
  assertDataset(aggregate, "Sessions", Array(10).fill(3));
  const compare = buildModelsPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Claude Code", Array(10).fill(2));
});

test("builds weighted aggregate and grouped compare first-prompt models", () => {
  const payload = {
    labels: ["short", "detailed"],
    avg_msgs: { cursor: [10, 8], "claude-code": [4, 2] },
    n: { cursor: [1, 0], "claude-code": [3, 2] },
  };
  const aggregate = buildFirstPromptPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.stacked, false);
  assertDataset(aggregate, "Avg messages", [5.5, 2]);
  const compare = buildFirstPromptPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, false);
  assertDataset(compare, "Cursor", [10, 8]);
  assertDataset(compare, "Claude Code", [4, 2]);
});

test("builds exactly eight factual wrapped cells with nullable fallbacks", () => {
  const payload = {
    totals: {
      sessions: 12,
      messages: 80,
      span: { start: "2026-01-01", end: "2026-01-05", days: 5 },
    },
    distinct_projects: 3,
    busiest_harness: { name: "claude-code", pct: 58.3 },
    best_streak: { days: 3, start: "2026-01-01", end: "2026-01-03" },
    marathon_session: {
      messages: 20,
      project_name: "stockroom",
      harness: "cursor",
    },
    peak_hour: { hour: 14, count: 4 },
    top_tool: { name: "ReadFile", calls: 30 },
  };
  const cells = buildWrappedPanel(payload);
  assert.equal(cells.length, 8);
  assert.deepEqual(cells.map((cell) => cell.label), [
    "Total Sessions",
    "Total Messages",
    "Distinct Projects",
    "Busiest Harness",
    "Best Streak",
    "Marathon Session",
    "Peak Hour",
    "Top Tool",
  ]);
  assert.equal(cells[3].value, "Claude Code");
  assert.equal(cells[7].value, "ReadFile");
  const empty = buildWrappedPanel({});
  assert.equal(empty.length, 8);
  assert.equal(empty[0].value, "0");
  assert.equal(empty[3].value, "—");
  assert.equal(empty[5].value, "—");
  assert.equal(
    buildWrappedPanel({ peak_hour: { hour: null, count: 0 } })[6].value,
    "—",
  );
});

test("formats wrapped span and streak dates with short local dates", () => {
  const formatter = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const start = formatter.format(new Date("2026-01-01T00:00:00"));
  const end = formatter.format(new Date("2026-01-05T00:00:00"));
  const streakEnd = formatter.format(new Date("2026-01-03T00:00:00"));
  const cells = buildWrappedPanel({
    totals: {
      sessions: 1,
      messages: 1,
      span: { start: "2026-01-01", end: "2026-01-05", days: 5 },
    },
    best_streak: { days: 3, start: "2026-01-01", end: "2026-01-03" },
  });
  assert.equal(cells[0].subtitle, `5 days · ${start} – ${end}`);
  assert.equal(cells[4].subtitle, `${start} – ${streakEnd}`);
});

test("keeps every pure transformation input unchanged", () => {
  const payload = {
    projects: ["one"],
    sessions: { cursor: [1], "claude-code": [2] },
  };
  const before = structuredClone(payload);
  buildProjectsPanel(payload, selected, "compare", colors);
  deriveOverviewCards(
    {
      distinct_projects: 1,
      per_harness: {
        cursor: {
          sessions: 1,
          messages: 1,
          projects: 1,
          prev_sessions: 0,
          prev_messages: 0,
          prev_projects: 0,
        },
      },
    },
    ["cursor"],
  );
  assert.deepEqual(payload, before);
});

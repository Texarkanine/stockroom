import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsConversationPanel,
  buildModelsMessagePanel,
  buildModelTrendsPanel,
  assignModelColors,
  colorForModel,
  buildProjectsPanel,
  buildToolsPanel,
  assignSkillSunburstColors,
  buildSkillsNestedPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  chartHeight,
  chartInteractionOptions,
  closePanelHelp,
  deriveHarnessBreakdown,
  deriveOverviewCards,
  displayHarness,
  doughnutTooltipLabel,
  formatDelta,
  formatRingPercent,
  harnessColors,
  projectHoverTitle,
  resolveWindowBounds,
  sessionsEllipsisCount,
  sessionsPaginationVisible,
  buildTruncatedPaginationItems,
  buildSessionsPanelRows,
  sortedHarnesses,
  sumAligned,
  summarizeChartPanel,
  togglePanelHelp,
  tooltipLabelColors,
  tooltipTitleFromLabelTitles,
  transitionViewState,
  weightedSeries,
  writeShare,
} from "../src/stockroom/dashboard/static/dashboard-core.mjs";

/** Matches dashboard `--accent` / aggregate series (not a harness slot). */
const AGGREGATE_COLOR = "#6366f1";

/** Doughnut/pie segment separators (both themes). */
const RING_BORDER = "#000000";

const COLORS = [
  "#EE7733",
  "#0077BB",
  "#EE3377",
  "#009988",
  "#CC3311",
  "#F3C300",
  "#332288",
  "#008856",
  "#66CCEE",
  "#875692",
  "#999933",
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
    zeta: COLORS[8],
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
    prev_distinct_projects: 1,
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

test("projects delta uses prev_distinct_projects not summed prev_projects", () => {
  const overview = {
    distinct_projects: 2,
    prev_distinct_projects: 2,
    per_harness: {
      cursor: {
        sessions: 1,
        messages: 2,
        projects: 1,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 2,
      },
      "claude-code": {
        sessions: 1,
        messages: 2,
        projects: 1,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 2,
      },
    },
  };
  const prevSum =
    overview.per_harness.cursor.prev_projects +
    overview.per_harness["claude-code"].prev_projects;
  assert.ok(prevSum > overview.prev_distinct_projects);
  const projects = deriveOverviewCards(overview, selected).find(
    (card) => card.key === "projects",
  );
  assert.deepEqual(projects, {
    key: "projects",
    label: "Projects",
    value: 2,
    delta: { text: "No change", trend: "neutral" },
  });
});

test("missing prev_distinct_projects degrades through formatDelta guards", () => {
  const overview = {
    distinct_projects: 2,
    per_harness: {
      cursor: {
        sessions: 1,
        messages: 1,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 0,
        prev_projects: 5,
      },
      "claude-code": {
        sessions: 1,
        messages: 1,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 0,
        prev_projects: 5,
      },
    },
  };
  const projects = deriveOverviewCards(overview, selected).find(
    (card) => card.key === "projects",
  );
  assert.deepEqual(projects.delta, { text: "New", trend: "up" });
  assert.deepEqual(
    deriveOverviewCards({ distinct_projects: 0, prev_distinct_projects: null }, [])
      .find((card) => card.key === "projects").delta,
    { text: "No change", trend: "neutral" },
  );
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
  const initial = {
    harnesses: [],
    selected: [],
    mode: "aggregate",
    dateRange: "default",
    window: null,
  };
  const discovered = transitionViewState(initial, {
    type: "discover",
    harnesses: ["cursor", "claude-code", "cursor"],
  });
  assert.deepEqual(discovered, {
    state: {
      harnesses: ["claude-code", "cursor"],
      selected: ["claude-code", "cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    effect: "render",
  });
  const refused = transitionViewState(
    {
      harnesses: ["cursor"],
      selected: ["cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    { type: "toggle", harness: "cursor" },
  );
  assert.deepEqual(refused, {
    state: {
      harnesses: ["cursor"],
      selected: ["cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    effect: "none",
  });
});

test("distinguishes mode redraws from selection refetches", () => {
  const state = {
    harnesses: ["claude-code", "cursor"],
    selected: ["claude-code", "cursor"],
    mode: "aggregate",
    dateRange: "default",
    window: null,
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

test("date-range changes refetch and identical presets are no-ops", () => {
  const now = new Date("2026-07-10T18:00:00.000Z");
  const state = {
    harnesses: ["cursor"],
    selected: ["cursor"],
    mode: "aggregate",
    dateRange: "default",
    window: null,
  };
  const changed = transitionViewState(state, {
    type: "daterange",
    preset: "7d",
    now,
  });
  assert.equal(changed.effect, "refetch");
  assert.equal(changed.state.dateRange, "7d");
  assert.deepEqual(changed.state.window, resolveWindowBounds("7d", now));
  assert.equal(changed.state.mode, "aggregate");

  const same = transitionViewState(changed.state, {
    type: "daterange",
    preset: "7d",
    now,
  });
  assert.equal(same.effect, "none");
  assert.equal(same.state.dateRange, "7d");

  const backToDefault = transitionViewState(changed.state, {
    type: "daterange",
    preset: "default",
    now,
  });
  assert.equal(backToDefault.effect, "refetch");
  assert.equal(backToDefault.state.dateRange, "default");
  assert.equal(backToDefault.state.window, null);

  const modeStillRenderOnly = transitionViewState(changed.state, {
    type: "mode",
    mode: "compare",
  });
  assert.equal(modeStillRenderOnly.effect, "render");
  assert.equal(modeStillRenderOnly.state.dateRange, "7d");
  assert.deepEqual(modeStillRenderOnly.state.window, changed.state.window);
});

test("resolveWindowBounds omits default and computes ISO since/until for presets", () => {
  const now = new Date("2026-07-10T18:00:00.000Z");
  assert.equal(resolveWindowBounds("default", now), null);
  assert.equal(resolveWindowBounds("nope", now), null);

  const week = resolveWindowBounds("7d", now);
  assert.equal(week.until, "2026-07-10T18:00:00.000Z");
  assert.equal(week.since, "2026-07-03T18:00:00.000Z");

  const year = resolveWindowBounds("1y", now);
  assert.equal(year.until, "2026-07-10T18:00:00.000Z");
  assert.equal(year.since, "2025-07-10T18:00:00.000Z");

  assert.equal(resolveWindowBounds("30d", now).since, "2026-06-10T18:00:00.000Z");
  assert.equal(resolveWindowBounds("90d", now).since, "2026-04-11T18:00:00.000Z");
});

test("builds aggregate and compare daily activity models", () => {
  const payload = {
    labels: ["2026-01-01", "2026-01-02"],
    sessions: { cursor: [1, 2], "claude-code": [3, 0] },
  };
  const aggregate = buildDailyPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "bar");
  assert.equal(aggregate.stacked, false);
  assertDataset(aggregate, "Sessions", [4, 2]);
  // Aggregate series uses accent, not the first harness (orange) slot.
  const aggregateSessions = aggregate.datasets.find((item) => item.label === "Sessions");
  assert.equal(aggregateSessions.backgroundColor, AGGREGATE_COLOR);
  assert.equal(aggregateSessions.borderColor, AGGREGATE_COLOR);
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
  const aggregateSessions = aggregate.datasets.find((item) => item.label === "Sessions");
  assert.equal(aggregateSessions.backgroundColor, AGGREGATE_COLOR);
  const compare = buildProjectsPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Cursor", [2, 0]);
});

test("projectHoverTitle returns id only when display differs", () => {
  assert.equal(projectHoverTitle("stockroom", "home-me-stockroom"), "home-me-stockroom");
  assert.equal(projectHoverTitle("slug", "slug"), null);
  assert.equal(projectHoverTitle("slug", null), null);
  assert.equal(projectHoverTitle(null, "slug"), "slug");
});

test("buildProjectsPanel prefers friendly labels and sets labelTitles", () => {
  const payload = {
    projects: ["home-me-stockroom", "other-slug"],
    labels: ["stockroom", "other-slug"],
    sessions: { cursor: [2, 1], "claude-code": [0, 0] },
  };
  const panel = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.deepEqual(panel.labels, ["stockroom", "other-slug"]);
  assert.deepEqual(panel.labelTitles, ["home-me-stockroom", null]);
  assertDataset(panel, "Sessions", [2, 1]);
});

test("buildProjectsPanel falls back to projects when labels missing", () => {
  const payload = {
    projects: ["only-id"],
    sessions: { cursor: [1], "claude-code": [0] },
  };
  const panel = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.deepEqual(panel.labels, ["only-id"]);
  assert.deepEqual(panel.labelTitles, [null]);
});

test("tooltipTitleFromLabelTitles surfaces slug when present", () => {
  assert.equal(
    tooltipTitleFromLabelTitles(["home-me-stockroom", null], 0, "stockroom"),
    "home-me-stockroom",
  );
  assert.equal(tooltipTitleFromLabelTitles(["home-me-stockroom", null], 1, "other"), "other");
  assert.equal(tooltipTitleFromLabelTitles(undefined, 0, "friendly"), "friendly");
});

test("chartInteractionOptions uses y axis for horizontal bars", () => {
  /**
   * Horizontal charts (indexAxis "y") must search along y for index-mode
   * hover/tooltip; Chart.js defaults index mode to axis "x", which tracks
   * the value axis and misses swimlanes.
   */
  assert.deepEqual(chartInteractionOptions("y"), {
    mode: "index",
    intersect: false,
    axis: "y",
  });
});

test("chartInteractionOptions uses x axis for vertical bars", () => {
  /** Vertical charts keep category search on x (Chart.js index-mode default). */
  assert.deepEqual(chartInteractionOptions("x"), {
    mode: "index",
    intersect: false,
    axis: "x",
  });
  assert.deepEqual(chartInteractionOptions(), {
    mode: "index",
    intersect: false,
    axis: "x",
  });
});

test("chartInteractionOptions uses nearest for doughnut and pie", () => {
  /** Arc hover must target one segment; index mode breaks nested two-ring charts. */
  assert.deepEqual(chartInteractionOptions("x", "doughnut"), {
    mode: "nearest",
    intersect: true,
  });
  assert.deepEqual(chartInteractionOptions("x", "pie"), {
    mode: "nearest",
    intersect: true,
  });
});

test("togglePanelHelp opens one, re-toggles closed, and switches panels", () => {
  assert.equal(togglePanelHelp(null, "efficiency"), "efficiency");
  assert.equal(togglePanelHelp("efficiency", "efficiency"), null);
  assert.equal(togglePanelHelp("efficiency", "first-prompt"), "first-prompt");
  assert.equal(closePanelHelp(), null);
});

test("buildWrappedPanel marathon exposes subtitleTitle when name differs from id", () => {
  const cells = buildWrappedPanel({
    totals: { sessions: 1, messages: 5, span: { start: null, end: null, days: 0 } },
    distinct_projects: 1,
    busiest_harness: { name: null, pct: 0 },
    best_streak: { days: 0, start: null, end: null },
    marathon_session: {
      messages: 5,
      project_name: "stockroom",
      project_id: "home-me-stockroom",
      harness: "cursor",
    },
    peak_hour: { hour: null, count: 0 },
    top_tool: { name: null, calls: 0 },
  });
  const marathon = cells.find((cell) => cell.key === "marathon");
  assert.equal(marathon.subtitleTitle, "home-me-stockroom");
  const same = buildWrappedPanel({
    totals: { sessions: 0, messages: 0, span: {} },
    distinct_projects: 0,
    busiest_harness: {},
    best_streak: {},
    marathon_session: {
      messages: 1,
      project_name: "p1",
      project_id: "p1",
      harness: "cursor",
    },
    peak_hour: {},
    top_tool: {},
  }).find((cell) => cell.key === "marathon");
  assert.equal(same.subtitleTitle, null);
});

test("builds aggregate doughnut and compare tool models", () => {
  const payload = {
    tools: ["Read", "Write"],
    calls: { cursor: [3, 1], "claude-code": [2, 4] },
  };
  const aggregate = buildToolsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "doughnut");
  assertDataset(aggregate, "Calls", [5, 5]);
  // Per-segment fills; shared black border (not the first fill / aggregate hue).
  const calls = aggregate.datasets.find((item) => item.label === "Calls");
  assert.deepEqual(calls.backgroundColor, [COLORS[0], COLORS[1]]);
  assert.equal(calls.borderColor, RING_BORDER);
  const compare = buildToolsPanel(payload, selected, "compare", colors);
  assert.equal(compare.kind, "bar");
  assert.equal(compare.indexAxis, "y");
  assertDataset(compare, "Claude Code", [2, 4]);
});

const skillsPayload = {
  skills: ["niko", "gm"],
  invokers: ["user", "agent"],
  calls: {
    "claude-code": { user: [1, 0], agent: [2, 5] },
    cursor: { user: [0, 0], agent: [3, 0] },
  },
};

test("assignSkillSunburstColors follows overall payload rank", () => {
  /**
   * Like Tool Distribution: hue = position in the API-ranked skills list
   * (overall totals), not agent-count rank. Agent-heavy #2 must not steal
   * COLORS[0] from overall #1.
   */
  const colorsBySkill = assignSkillSunburstColors(["overall-first", "agent-heavy", "solo"]);
  assert.equal(colorsBySkill.get("overall-first"), COLORS[0]);
  assert.equal(colorsBySkill.get("agent-heavy"), COLORS[1]);
  assert.equal(colorsBySkill.get("solo"), COLORS[2]);
});

test("assignSkillSunburstColors keeps top-10 skills on distinct hues", () => {
  /**
   * Full categorical series (11 hues) covers a default top-10 without reuse.
   */
  const ranked = Array.from({ length: 10 }, (_, index) => `skill-${index}`);
  const colorsBySkill = assignSkillSunburstColors(ranked);
  const assigned = [...colorsBySkill.values()];
  assert.equal(assigned.length, 10);
  assert.equal(new Set(assigned).size, 10);
  assert.equal(colorsBySkill.get("skill-9"), COLORS[9]);
});

test("builds skills nested aggregate as aligned sunburst", () => {
  /**
   * Outer = user skills then agent skills; inner = [userTotal, agentTotal];
   * circumference sums match; dual-invoker skill appears twice on the outer ring.
   */
  const aggregate = buildSkillsNestedPanel(skillsPayload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "doughnut");
  assert.equal(aggregate.empty, false);
  // user: niko=1; agent: niko=5, gm=5 (ties keep payload order)
  assert.deepEqual(aggregate.labels, ["niko", "niko", "gm"]);
  assert.deepEqual(aggregate.innerLabels, ["user", "agent"]);
  assertDataset(aggregate, "Skills", [1, 5, 5]);
  assertDataset(aggregate, "Invokers", [1, 10]);
  const outer = aggregate.datasets.find((item) => item.label === "Skills");
  const inner = aggregate.datasets.find((item) => item.label === "Invokers");
  const userOuter = outer.data.slice(0, 1);
  const agentOuter = outer.data.slice(1);
  assert.equal(
    userOuter.reduce((sum, value) => sum + value, 0),
    inner.data[0],
  );
  assert.equal(
    agentOuter.reduce((sum, value) => sum + value, 0),
    inner.data[1],
  );
});

test("builds skills nested sunburst wedges largest-to-smallest within each ring half", () => {
  /**
   * Payload order must not dictate wedge order — each invoker group sorts by
   * count descending so agent-heavy skills aren't stuck mid-arc.
   */
  const payload = {
    skills: ["alpha", "beta", "gamma"],
    invokers: ["user", "agent"],
    calls: {
      cursor: { user: [10, 3, 1], agent: [2, 20, 5] },
      "claude-code": { user: [0, 0, 0], agent: [0, 0, 0] },
    },
  };
  const aggregate = buildSkillsNestedPanel(payload, selected, "aggregate", colors);
  // user desc: alpha10, beta3, gamma1; agent desc: beta20, gamma5, alpha2
  assert.deepEqual(aggregate.labels, ["alpha", "beta", "gamma", "beta", "gamma", "alpha"]);
  assertDataset(aggregate, "Skills", [10, 3, 1, 20, 5, 2]);
});

test("builds skills nested sunburst legend once per skill with agent-preferred color", () => {
  /**
   * Legend lists each skill once: solid agent color when the skill has agent
   * uses; faded user color only for user-only skills.
   */
  const payload = {
    skills: ["shared", "solo"],
    invokers: ["user", "agent"],
    calls: {
      cursor: { user: [2, 4], agent: [6, 0] },
      "claude-code": { user: [0, 0], agent: [0, 0] },
    },
  };
  const aggregate = buildSkillsNestedPanel(payload, selected, "aggregate", colors);
  assert.deepEqual(
    aggregate.legendItems.map((item) => item.text),
    ["shared", "solo"],
  );
  // shared has agent → solid COLORS[0]; solo user-only → faded COLORS[1]
  assert.deepEqual(
    aggregate.legendItems.map((item) => item.fillStyle),
    [COLORS[0], "rgba(0, 119, 187, 0.55)"],
  );
  assert.deepEqual(
    aggregate.legendItems.map((item) => item.strokeStyle),
    [COLORS[0], "rgba(0, 119, 187, 0.55)"],
  );
});

test("builds skills nested sunburst colors from payload rank not agent rank", () => {
  /**
   * Inner invoker ring stays AGGREGATE_COLOR. Skill hues follow overall payload
   * order (Tools-like): user wedges are faded twins of the same skill color.
   * Agent-count rank must not reassign hues when overall rank differs.
   */
  const payload = {
    skills: ["stable-top", "agent-spike"],
    invokers: ["user", "agent"],
    calls: {
      // overall: stable-top=55, agent-spike=40; agent: spike=40, top=5
      cursor: { user: [50, 0], agent: [5, 40] },
      "claude-code": { user: [0, 0], agent: [0, 0] },
    },
  };
  const aggregate = buildSkillsNestedPanel(payload, selected, "aggregate", colors);
  const outer = aggregate.datasets.find((item) => item.label === "Skills");
  const inner = aggregate.datasets.find((item) => item.label === "Invokers");
  // user: stable-top; agent: agent-spike, stable-top
  assert.deepEqual(aggregate.labels, ["stable-top", "agent-spike", "stable-top"]);
  assert.deepEqual(outer.backgroundColor, [
    "rgba(238, 119, 51, 0.55)",
    COLORS[1],
    COLORS[0],
  ]);
  assert.deepEqual(inner.backgroundColor, [
    "rgba(99, 102, 241, 0.55)",
    AGGREGATE_COLOR,
  ]);
  assert.deepEqual(outer.borderColor, [RING_BORDER, RING_BORDER, RING_BORDER]);
  assert.deepEqual(inner.borderColor, [RING_BORDER, RING_BORDER]);
});


test("tooltipLabelColors uses backgroundColor fill not borderColor", () => {
  /**
   * Stacked skill datasets pair faded fills with solid borders; tooltip swatches
   * must match the bar/legend fill, not the border.
   */
  const stacked = {
    backgroundColor: "rgba(99, 102, 241, 0.55)",
    borderColor: AGGREGATE_COLOR,
  };
  assert.deepEqual(tooltipLabelColors(stacked, 0), {
    borderColor: "rgba(99, 102, 241, 0.55)",
    backgroundColor: "rgba(99, 102, 241, 0.55)",
  });
  const arcs = {
    backgroundColor: ["#10b981", "#f59e0b"],
    borderColor: ["#000000", "#ffffff"],
  };
  assert.deepEqual(tooltipLabelColors(arcs, 1), {
    borderColor: "#f59e0b",
    backgroundColor: "#f59e0b",
  });
});

test("formatRingPercent and doughnutTooltipLabel include ring share", () => {
  /**
   * Pie/doughnut tooltips show count and percent of that ring's total.
   */
  assert.equal(formatRingPercent(0, 0), "0%");
  assert.equal(formatRingPercent(1, 10), "10%");
  assert.equal(formatRingPercent(1, 30), "3.3%");
  assert.equal(
    doughnutTooltipLabel({ label: "Calls", data: [1, 3] }, 1, "Write"),
    "Write: 3 (75%)",
  );
});


test("builds skills nested compare stacked bar unchanged", () => {
  /** Compare mode stays harness×invoker stacked bars (not sunburst geometry). */
  const compare = buildSkillsNestedPanel(skillsPayload, selected, "compare", colors);
  assert.equal(compare.kind, "bar");
  assert.equal(compare.indexAxis, "y");
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Claude Code · user", [1, 0]);
  assertDataset(compare, "Claude Code · agent", [2, 5]);
  assertDataset(compare, "Cursor · agent", [3, 0]);
});

test("builds skills nested sunburst for user-only and agent-only edges", () => {
  /**
   * All-user / all-agent still emit both inner values (zeros allowed); user-only
   * skills take the first categorical palette slot.
   */
  const userOnly = buildSkillsNestedPanel(
    {
      skills: ["solo"],
      invokers: ["user", "agent"],
      calls: {
        cursor: { user: [3], agent: [0] },
        "claude-code": { user: [0], agent: [0] },
      },
    },
    selected,
    "aggregate",
    colors,
  );
  assert.deepEqual(userOnly.labels, ["solo"]);
  assertDataset(userOnly, "Skills", [3]);
  assertDataset(userOnly, "Invokers", [3, 0]);
  const userOuter = userOnly.datasets.find((item) => item.label === "Skills");
  // No agent skills → first categorical slot is COLORS[0].
  assert.deepEqual(userOuter.backgroundColor, ["rgba(238, 119, 51, 0.55)"]);

  const agentOnly = buildSkillsNestedPanel(
    {
      skills: ["bot"],
      invokers: ["user", "agent"],
      calls: {
        cursor: { user: [0], agent: [4] },
        "claude-code": { user: [0], agent: [0] },
      },
    },
    selected,
    "aggregate",
    colors,
  );
  assert.deepEqual(agentOnly.labels, ["bot"]);
  assertDataset(agentOnly, "Skills", [4]);
  assertDataset(agentOnly, "Invokers", [0, 4]);
  const agentOuter = agentOnly.datasets.find((item) => item.label === "Skills");
  assert.deepEqual(agentOuter.backgroundColor, [COLORS[0]]);
});



test("marks skills panels empty when payload has no skill calls", () => {
  const emptyPayload = {
    skills: [],
    invokers: ["user", "agent"],
    calls: {
      cursor: { user: [], agent: [] },
      "claude-code": { user: [], agent: [] },
    },
  };
  for (const builder of [buildSkillsNestedPanel]) {
    const panel = builder(emptyPayload, selected, "aggregate", colors);
    assert.equal(panel.empty, true, `${builder.name} should be empty`);
  }
});

test("writeShare returns zero on zero denominator and finite ratios otherwise", () => {
  assert.equal(writeShare(0, 0), 0);
  assert.equal(writeShare(0, 4), 0);
  assert.equal(writeShare(3, 1), 0.75);
  assert.equal(writeShare(2, 2), 0.5);
});

test("builds aggregate write-share ratio line with zeros for idle buckets", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12", "2026-01-19"],
    writes: { cursor: [2, 0, 0], "claude-code": [1, 0, 0] },
    reads: { cursor: [4, 0, 5], "claude-code": [0, 0, 0] },
  };
  const panel = buildWriteReadPanel(payload, selected, "aggregate", colors);
  assert.equal(panel.kind, "line");
  assert.equal(panel.stacked, false);
  assert.equal(panel.empty, false);
  assert.equal(panel.yMax, 1);
  assert.equal(panel.datasets.length, 1);
  // week0: (2+1)/(2+1+4+0)=3/7; week1: 0/0 → 0; week2: 0/(0+5)=0
  assertDataset(panel, "Write share", [3 / 7, 0, 0]);
});

test("builds compare write-share ratio lines per harness", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12"],
    writes: { cursor: [2, 0], "claude-code": [1, 0] },
    reads: { cursor: [2, 0], "claude-code": [3, 4] },
  };
  const panel = buildWriteReadPanel(payload, selected, "compare", colors);
  assert.equal(panel.datasets.length, 2);
  assert.equal(panel.empty, false);
  assert.equal(panel.yMax, 1);
  // orderedSelection sorts: claude-code, cursor
  assertDataset(panel, "Claude Code", [0.25, 0]);
  assertDataset(panel, "Cursor", [0.5, 0]);
  assert.equal(panel.datasets[0].borderColor, colors["claude-code"]);
  assert.equal(panel.datasets[1].borderColor, colors.cursor);
});

test("marks write-read panel empty when every bucket has no tool activity", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12"],
    writes: { cursor: [0, 0], "claude-code": [0, 0] },
    reads: { cursor: [0, 0], "claude-code": [0, 0] },
  };
  const panel = buildWriteReadPanel(payload, selected, "aggregate", colors);
  assert.equal(panel.empty, true);
  assert.deepEqual(panel.datasets[0].data, [0, 0]);
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

test("assignModelColors follows ranked order like harness/skill palettes", () => {
  const ranked = Array.from({ length: 10 }, (_, index) => `model-${index}`);
  const colorsByModel = assignModelColors(ranked);
  assert.equal(colorsByModel.get("model-0"), assignModelColors(["solo"]).get("solo"));
  const hues = ranked.map((model) => colorsByModel.get(model));
  assert.equal(new Set(hues).size, 10);
  // First-seen wins: message-first union keeps m1 on slot 0
  const shared = assignModelColors(["m1", "m2", "m3"]);
  const extended = assignModelColors(["m1", "m2", "m3", "m4"]);
  assert.equal(extended.get("m1"), shared.get("m1"));
  assert.equal(extended.get("m4"), assignModelColors(["a", "b", "c", "d"]).get("d"));
});

test("builds conversation and message model bar panels", () => {
  const conversation = {
    models: Array.from({ length: 10 }, (_, index) => `model-${index}`),
    sessions: {
      cursor: Array(10).fill(1),
      "claude-code": Array(10).fill(2),
    },
  };
  const message = {
    models: ["composer", "opus"],
    messages: {
      cursor: [5, 0],
      "claude-code": [0, 3],
    },
  };
  // Canonical message rank first, then conversation-only extras.
  const modelColors = assignModelColors([
    ...message.models,
    ...conversation.models,
  ]);
  const convAgg = buildModelsConversationPanel(
    conversation,
    selected,
    "aggregate",
    colors,
    modelColors,
  );
  assert.equal(convAgg.labels.length, 10);
  assert.equal(convAgg.height, 340);
  assert.equal(convAgg.indexAxis, "y");
  assertDataset(convAgg, "Sessions", Array(10).fill(3));
  assert.equal(convAgg.datasets[0].backgroundColor.length, 10);
  // model-0 is conversation-only → third palette slot after composer, opus
  assert.equal(convAgg.datasets[0].backgroundColor[0], modelColors.get("model-0"));
  assert.equal(modelColors.get("composer"), assignModelColors(["solo"]).get("solo"));

  const convCompare = buildModelsConversationPanel(
    conversation,
    selected,
    "compare",
    colors,
    modelColors,
  );
  assert.equal(convCompare.stacked, true);
  assertDataset(convCompare, "Claude Code", Array(10).fill(2));

  const msgAgg = buildModelsMessagePanel(
    message,
    selected,
    "aggregate",
    colors,
    modelColors,
  );
  assertDataset(msgAgg, "Messages", [5, 3]);
  assert.equal(msgAgg.datasets[0].backgroundColor[0], modelColors.get("composer"));
  const msgCompare = buildModelsMessagePanel(
    message,
    selected,
    "compare",
    colors,
    modelColors,
  );
  assert.equal(msgCompare.stacked, true);
  assertDataset(msgCompare, "Cursor", [5, 0]);
});

test("builds stacked area model trends with ranked palette", () => {
  const payload = {
    labels: ["2026-01-10", "2026-01-11"],
    granularity: "day",
    models: ["m1", "m2"],
    counts: {
      m1: [2, 0],
      m2: [1, 3],
    },
  };
  const modelColors = assignModelColors(["m1", "m2"]);
  const panel = buildModelTrendsPanel(
    payload,
    selected,
    "aggregate",
    colors,
    modelColors,
  );
  assert.equal(panel.kind, "line");
  assert.equal(panel.stacked, true);
  assert.equal(panel.fill, true);
  assert.equal(panel.omitZeroTooltip, true);
  assert.equal(panel.datasets.length, 2);
  assert.equal(panel.datasets[0].fill, true);
  assert.equal(panel.datasets[0].label, "m1");
  assert.deepEqual(panel.datasets[0].data, [2, 0]);
  assert.equal(panel.datasets[0].backgroundColor, modelColors.get("m1"));
  assert.equal(panel.datasets[1].backgroundColor, modelColors.get("m2"));
  // Same set/order as message bars → same first hue
  assert.equal(
    panel.datasets[0].backgroundColor,
    buildModelsMessagePanel(
      { models: ["m1", "m2"], messages: { cursor: [2, 1] } },
      selected,
      "aggregate",
      colors,
      modelColors,
    ).datasets[0].backgroundColor[0],
  );
});

test("model trends panel does not invent harness datasets", () => {
  const panel = buildModelTrendsPanel(
    {
      labels: ["2026-01-10"],
      models: ["solo"],
      counts: { solo: [4] },
    },
    selected,
    "compare",
    colors,
  );
  assert.equal(panel.datasets.length, 1);
  assert.equal(panel.datasets[0].label, "solo");
  assert.ok(!panel.datasets.some((dataset) => /cursor|claude/i.test(dataset.label)));
});

test("empty model panels set empty flag", () => {
  const emptyBars = buildModelsConversationPanel(
    { models: [], sessions: {} },
    selected,
    "aggregate",
    colors,
  );
  assert.equal(emptyBars.empty, true);
  const emptyArea = buildModelTrendsPanel(
    { labels: ["2026-01-10"], models: [], counts: {} },
    selected,
    "aggregate",
    colors,
  );
  assert.equal(emptyArea.empty, true);
});

test("colorForModel reads shared rank map", () => {
  const map = assignModelColors(["composer", "opus"]);
  assert.equal(colorForModel("composer", map), map.get("composer"));
  assert.equal(colorForModel("opus", map), map.get("opus"));
  assert.notEqual(colorForModel("composer", map), colorForModel("opus", map));
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
    "Peak Hour (UTC)",
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

test("summarizes aggregate panel measured content", () => {
  const model = {
    kind: "bar",
    labels: ["stockroom", "other"],
    datasets: [{ label: "Sessions", data: [3, 4] }],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Sessions by project", "aggregate", model),
    "Sessions by project. Aggregate view. Sessions: stockroom 3, other 4.",
  );
});

test("summarizes compare panel per-harness measured content", () => {
  const model = {
    kind: "bar",
    labels: ["stockroom", "other"],
    datasets: [
      { label: "Claude Code", data: [1, 4] },
      { label: "Cursor", data: [2, 0] },
    ],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Sessions by project", "compare", model),
    "Sessions by project. Compare view. Claude Code: stockroom 1, other 4; Cursor: stockroom 2, other 0.",
  );
});

test("summarizes empty panel without inventing values", () => {
  const model = {
    kind: "bar",
    labels: ["a", "b"],
    datasets: [{ label: "Sessions", data: [0, 0] }],
    empty: true,
  };
  assert.equal(
    summarizeChartPanel("Daily session activity", "aggregate", model),
    "Daily session activity. Aggregate view. No data in this period.",
  );
});

test("summarizes write-share ratio panel including idle zeros", () => {
  const model = {
    kind: "line",
    labels: ["2026-01-05", "2026-01-12"],
    datasets: [{ label: "Write share", data: [0.5, 0] }],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Weekly write share", "aggregate", model),
    "Weekly write share. Aggregate view. Write share: 2026-01-05 0.5, 2026-01-12 0.",
  );
});

test("summarizeChartPanel leaves the input model unchanged", () => {
  const model = {
    kind: "bar",
    labels: ["one"],
    datasets: [{ label: "Sessions", data: [2] }],
    empty: false,
  };
  const before = structuredClone(model);
  summarizeChartPanel("Sessions by project", "aggregate", model);
  assert.deepEqual(model, before);
});

test("sessionsEllipsisCount is total minus twenty when over the panel cap", () => {
  assert.equal(sessionsEllipsisCount(0), 0);
  assert.equal(sessionsEllipsisCount(20), 0);
  assert.equal(sessionsEllipsisCount(21), 1);
  assert.equal(sessionsEllipsisCount(25), 5);
});

test("sessionsPaginationVisible only when paging and total exceeds page size", () => {
  assert.equal(sessionsPaginationVisible(100, 50), true);
  assert.equal(sessionsPaginationVisible(50, 50), false);
  assert.equal(sessionsPaginationVisible(100, "all"), false);
  assert.equal(sessionsPaginationVisible(0, 25), false);
});

test("buildTruncatedPaginationItems uses sibling and boundary windows with ellipsis", () => {
  // Default siblingCount=2 → up to five pages around the current page.
  assert.deepEqual(buildTruncatedPaginationItems(1, 1), [1]);
  assert.deepEqual(buildTruncatedPaginationItems(1, 0), []);
  assert.deepEqual(
    buildTruncatedPaginationItems(1, 11),
    [1, 2, 3, 4, 5, 6, 7, "ellipsis", 11],
  );
  assert.deepEqual(
    buildTruncatedPaginationItems(6, 11),
    [1, "ellipsis", 4, 5, 6, 7, 8, "ellipsis", 11],
  );
  assert.deepEqual(
    buildTruncatedPaginationItems(10, 11),
    [1, "ellipsis", 5, 6, 7, 8, 9, 10, 11],
  );
  assert.deepEqual(
    buildTruncatedPaginationItems(1, 4),
    [1, 2, 3, 4],
  );
  assert.deepEqual(
    buildTruncatedPaginationItems(5, 11, { siblingCount: 1, boundaryCount: 1 }),
    [1, "ellipsis", 4, 5, 6, "ellipsis", 11],
  );
});

test("buildSessionsPanelRows emits newest, optional ellipsis, then oldest", () => {
  const newest = [{ session_id: "n1" }, { session_id: "n0" }];
  const oldest = [{ session_id: "o0" }, { session_id: "o1" }];
  assert.deepEqual(buildSessionsPanelRows({ total: 2, newest, oldest: [] }), [
    { kind: "session", session: newest[0] },
    { kind: "session", session: newest[1] },
  ]);
  assert.deepEqual(
    buildSessionsPanelRows({ total: 25, newest, oldest }),
    [
      { kind: "session", session: newest[0] },
      { kind: "session", session: newest[1] },
      { kind: "more", count: 5 },
      { kind: "session", session: oldest[0] },
      { kind: "session", session: oldest[1] },
    ],
  );
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
      prev_distinct_projects: 0,
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

/**
 * Aggregate / “All harnesses” series color — matches CSS ``--accent``.
 * Kept separate from the categorical harness/tool/skill palette so sum charts
 * do not inherit the first harness hue (orange).
 */
const AGGREGATE_COLOR = "#6366f1";

/** Doughnut/pie arc separators — black in both light and dark themes. */
const RING_BORDER = "#000000";

/**
 * Categorical palette for harnesses, tools, and sunburst skill wedges
 * (operator pick: mockup B).
 *
 * Sequence: Paul Tol vibrant reordered so adjacent indexes are hue-distant
 * (no blue→cyan neighbors), topped up with Kelly fillers.
 * @see https://sronpersonalpages.nl/~pault/
 */
const PALETTE = [
  "#EE7733", // orange
  "#0077BB", // blue
  "#EE3377", // magenta
  "#009988", // teal
  "#CC3311", // red
  "#F3C300", // Kelly yellow
  "#332288", // muted indigo
  "#008856", // Kelly green
  "#66CCEE", // bright cyan
  "#875692", // Kelly purple
  "#999933", // muted olive
];

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function orderedSelection(selected) {
  return sortedHarnesses(selected ?? []);
}

function alignedLength(series, selected, length) {
  const explicit = Number(length);
  if (Number.isInteger(explicit) && explicit >= 0) {
    return explicit;
  }
  return orderedSelection(selected).reduce(
    (maximum, harness) =>
      Math.max(maximum, Array.isArray(series?.[harness]) ? series[harness].length : 0),
    0,
  );
}

function seriesFor(series, harness, length) {
  const values = Array.isArray(series?.[harness]) ? series[harness] : [];
  return Array.from({ length }, (_, index) => finiteNumber(values[index]));
}

function selectedDatasets(series, selected, labels, colors) {
  const keys = orderedSelection(selected);
  const assigned = colors ?? harnessColors(keys);
  return keys.map((harness) => ({
    label: displayHarness(harness),
    data: seriesFor(series, harness, labels.length),
    backgroundColor: assigned[harness],
    borderColor: assigned[harness],
    borderWidth: 1,
  }));
}

function hasValues(datasets) {
  return datasets.some((dataset) => dataset.data.some((value) => finiteNumber(value) !== 0));
}

function panelModel(kind, labels, datasets, options = {}) {
  return {
    kind,
    labels: [...labels],
    datasets,
    indexAxis: options.indexAxis ?? "x",
    stacked: options.stacked ?? false,
    empty: options.empty ?? !hasValues(datasets),
    ...(options.fill === undefined ? {} : { fill: options.fill }),
    ...(options.omitZeroTooltip === undefined
      ? {}
      : { omitZeroTooltip: options.omitZeroTooltip }),
    ...(options.height === undefined ? {} : { height: options.height }),
    ...(options.yMax === undefined ? {} : { yMax: options.yMax }),
    ...(options.labelTitles === undefined ? {} : { labelTitles: [...options.labelTitles] }),
    ...(options.innerLabels === undefined ? {} : { innerLabels: [...options.innerLabels] }),
    ...(options.legendItems === undefined
      ? {}
      : {
          legendItems: options.legendItems.map((item) => ({
            text: item.text,
            fillStyle: item.fillStyle,
            strokeStyle: item.strokeStyle ?? item.fillStyle,
          })),
        }),
  };
}

/**
 * Hover / accessible title for a project display label.
 *
 * @param {string | null | undefined} label Visible name.
 * @param {string | null | undefined} id Stable project_id slug.
 * @returns {string | null} Slug when it differs from the label; otherwise null.
 */
export function projectHoverTitle(label, id) {
  if (!id) {
    return null;
  }
  return label === id ? null : id;
}

/**
 * Chart.js tooltip title: prefer slug from labelTitles when set.
 *
 * @param {(string | null)[] | undefined} labelTitles Parallel hover titles.
 * @param {number} index Data index under the cursor.
 * @param {string} fallbackLabel Visible tick / default tooltip label.
 * @returns {string}
 */
export function tooltipTitleFromLabelTitles(labelTitles, index, fallbackLabel) {
  if (Array.isArray(labelTitles)) {
    const title = labelTitles[index];
    if (title) {
      return title;
    }
  }
  return fallbackLabel ?? "";
}

/**
 * Chart.js tooltip swatch colors from the dataset fill (not border).
 *
 * Callers should keep ``borderColor`` equal to ``backgroundColor`` on faded
 * stacks — point-style legends weight the border, so a solid border + faded
 * fill makes legend/tooltip disagree (especially on dark tooltip chrome).
 *
 * @param {object | null | undefined} dataset Chart.js dataset.
 * @param {number} [dataIndex=0] Segment index for per-arc color arrays.
 * @returns {{borderColor: string, backgroundColor: string}}
 */
export function tooltipLabelColors(dataset, dataIndex = 0) {
  const entry = safeObject(dataset);
  const index = Number.isInteger(dataIndex) && dataIndex >= 0 ? dataIndex : 0;
  const pick = (value) => (Array.isArray(value) ? value[index] : value);
  const fill = pick(entry.backgroundColor) ?? pick(entry.borderColor) ?? "";
  return {
    borderColor: fill,
    backgroundColor: fill,
  };
}

/**
 * Format a ring segment's share of its doughnut/pie dataset total.
 *
 * @param {number} value Segment value.
 * @param {number} total Sum of the ring's values.
 * @returns {string} Percent label (integer when ≥10%, else one decimal).
 */
export function formatRingPercent(value, total) {
  const amount = finiteNumber(value);
  const sum = finiteNumber(total);
  if (!(sum > 0)) {
    return "0%";
  }
  const percent = (amount / sum) * 100;
  if (percent === 0) {
    return "0%";
  }
  if (percent >= 10) {
    return `${Math.round(percent)}%`;
  }
  return `${Math.round(percent * 10) / 10}%`;
}

/**
 * Doughnut/pie tooltip line: ``{segment}: {value} ({percent})``.
 *
 * Percent is relative to that ring's dataset total (outer and inner sunburst
 * rings each sum to the same circumference total).
 *
 * @param {object | null | undefined} dataset Chart.js dataset.
 * @param {number} dataIndex Segment index.
 * @param {string} [segmentLabel] Visible segment name (skill / invoker / tool).
 * @returns {string}
 */
export function doughnutTooltipLabel(dataset, dataIndex, segmentLabel) {
  const entry = safeObject(dataset);
  const data = Array.isArray(entry.data) ? entry.data : [];
  const index = Number.isInteger(dataIndex) && dataIndex >= 0 ? dataIndex : 0;
  const value = finiteNumber(data[index]);
  const total = data.reduce((sum, item) => sum + finiteNumber(item), 0);
  const name = displayValue(segmentLabel || entry.label, "Segment");
  return `${name}: ${value} (${formatRingPercent(value, total)})`;
}

/**
 * Chart.js ``interaction`` / tooltip settings for a chart kind and category axis.
 *
 * Doughnut/pie use nearest+intersect so hover targets one arc (index mode and
 * a shared labels array break nested two-ring tooltips). Bars keep index mode;
 * horizontal bars (``indexAxis: "y"``) search along ``y``.
 * See https://www.chartjs.org/docs/latest/configuration/interactions.html
 *
 * @param {string} [indexAxis="x"] Panel category axis (``"x"`` or ``"y"``).
 * @param {string} [kind="bar"] Chart.js type (``"bar"``, ``"doughnut"``, …).
 * @returns {{mode: string, intersect: boolean, axis?: string}}
 */
export function chartInteractionOptions(indexAxis = "x", kind = "bar") {
  if (kind === "doughnut" || kind === "pie") {
    return {
      mode: "nearest",
      intersect: true,
    };
  }
  return {
    mode: "index",
    intersect: false,
    axis: indexAxis === "y" ? "y" : "x",
  };
}

/**
 * Static help copy for Session Efficiency and First-Prompt Quality.
 *
 * Thresholds mirror metrics.EFFICIENCY_BUCKETS / FIRST_PROMPT_BUCKETS
 * (abandoned ≤2, short 3–10, medium 11–40, long 41+ messages; first-prompt
 * short <100, medium ≤500, detailed >500 chars). Keep in sync manually.
 */
export const PANEL_HELP = {
  efficiency:
    "Buckets by message count per session: abandoned (≤2), short (3–10), medium (11–40), long (41+). Counts sessions in the selected window.",
  "first-prompt":
    "Buckets by first user-prompt length: short (<100 chars), medium (100–500), detailed (>500). Bars show average session message count per bucket.",
};

/**
 * Toggle which panel help popover is open (one at a time).
 *
 * @param {string | null} openId Currently open help id, or null.
 * @param {string} targetId Help id the user activated.
 * @returns {string | null} Next open id.
 */
export function togglePanelHelp(openId, targetId) {
  if (!targetId) {
    return null;
  }
  return openId === targetId ? null : targetId;
}

/** Close any open panel help popover. */
export function closePanelHelp() {
  return null;
}

function aggregateDataset(label, data, color = AGGREGATE_COLOR) {
  return {
    label,
    data,
    backgroundColor: color,
    borderColor: color,
    borderWidth: 1,
  };
}

function safeObject(value) {
  return value && typeof value === "object" ? value : {};
}

function displayValue(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const HAS_EXPLICIT_ZONE = /(?:[zZ]|[+-]\d{2}:\d{2})$/;

/**
 * Parse a warehouse date/datetime for display.
 *
 * Date-only values stay local calendar midnights. Datetime values are UTC:
 * explicit ``Z``/offset is honored; naive ISO strings are treated as UTC.
 *
 * @param {unknown} value ISO date or datetime string.
 * @param {boolean} [dateOnly=false] When true, parse as a calendar date label.
 * @returns {Date|null} Parsed date, or null when invalid.
 */
export function parseDisplayDate(value, dateOnly = false) {
  if (typeof value !== "string" || !value) {
    return null;
  }
  const normalized = dateOnly
    ? `${value}T00:00:00`
    : HAS_EXPLICIT_ZONE.test(value)
      ? value
      : `${value}Z`;
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Format a warehouse date/datetime in the runtime locale/timezone.
 *
 * @param {unknown} value ISO date or datetime string.
 * @param {boolean} [dateOnly=false] When true, format as a date-only label.
 * @returns {string} Localized display string, or an em dash when invalid.
 */
export function formatDate(value, dateOnly = false) {
  const parsed = parseDisplayDate(value, dateOnly);
  return parsed ? (dateOnly ? dateFormatter : dateTimeFormatter).format(parsed) : "—";
}

function formatShortDate(value) {
  if (typeof value !== "string" || !value) {
    return "—";
  }
  const parsed = parseDisplayDate(value, true);
  return parsed ? shortDateFormatter.format(parsed) : "—";
}

/**
 * Return sorted unique harness keys from any iterable.
 *
 * @param {Iterable<string>} harnesses Raw warehouse harness keys.
 * @returns {string[]} Deterministically ordered harness keys.
 */
export function sortedHarnesses(harnesses) {
  const values = harnesses && typeof harnesses[Symbol.iterator] === "function" ? harnesses : [];
  return [...new Set([...values].filter((value) => typeof value === "string" && value.trim()))]
    .map((value) => value.trim())
    .sort((left, right) => left.localeCompare(right));
}

/**
 * Derive a human-readable label from a raw harness key.
 *
 * @param {unknown} harness Raw warehouse harness key.
 * @returns {string} Generic display label.
 */
export function displayHarness(harness) {
  if (typeof harness !== "string" || !harness.trim()) {
    return "Unknown";
  }
  return harness
    .trim()
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Assign the fixed positional palette to sorted harness keys.
 *
 * @param {Iterable<string>} harnesses Raw warehouse harness keys.
 * @returns {Record<string, string>} Harness-to-color map.
 */
export function harnessColors(harnesses) {
  return Object.fromEntries(
    sortedHarnesses(harnesses).map((harness, index) => [
      harness,
      PALETTE[index % PALETTE.length],
    ]),
  );
}

/**
 * Ranked positional palette for model series (same sequence as harness/skills).
 *
 * Pass models in popularity order (canonical: message-grain rank). First-seen
 * wins, so extras (e.g. conversation-only models) take later palette slots.
 *
 * @param {Iterable<string> | null | undefined} rankedModels Model names in rank order.
 * @returns {Map<string, string>} model name → ``#rrggbb``.
 */
export function assignModelColors(rankedModels) {
  const colorsByModel = new Map();
  const slotCount = Math.max(PALETTE.length, 1);
  for (const model of rankedModels ?? []) {
    if (!model || colorsByModel.has(model)) {
      continue;
    }
    colorsByModel.set(model, PALETTE[colorsByModel.size % slotCount]);
  }
  return colorsByModel;
}

/**
 * Look up a model color from a shared rank map (from :func:`assignModelColors`).
 *
 * @param {string | null | undefined} model Model identifier.
 * @param {Map<string, string> | null | undefined} colorMap Shared model→color map.
 * @returns {string} Palette hex color.
 */
export function colorForModel(model, colorMap) {
  if (colorMap instanceof Map && model && colorMap.has(model)) {
    return colorMap.get(model);
  }
  if (model) {
    return assignModelColors([model]).get(model) ?? PALETTE[0];
  }
  return PALETTE[0];
}

/** Supported date-range preset ids for the top controls strip. */
const DATE_RANGE_PRESETS = Object.freeze([
  "default",
  "7d",
  "30d",
  "90d",
  "1y",
]);

const DATE_RANGE_DURATIONS_MS = Object.freeze({
  "7d": 7 * 24 * 60 * 60 * 1000,
  "30d": 30 * 24 * 60 * 60 * 1000,
  "90d": 90 * 24 * 60 * 60 * 1000,
  "1y": 365 * 24 * 60 * 60 * 1000,
});

const DATE_RANGE_WINDOW_LABELS = Object.freeze({
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
  "1y": "Last 1 year",
});

const DEFAULT_PANEL_RANGE_LABELS = Object.freeze({
  overviewAria: "Thirty-day overview",
  daily: "Last 14 days",
  projects: "Last 30 days",
  tools: "Last 30 days",
  skillsNested: "Last 30 days",
  writeRead: "Last 12 weeks",
  efficiency: "Last 30 days",
  models: "Last 30 days",
  modelTrends: "Last 30 days",
  firstPrompt: "Last 30 days",
});

/**
 * Normalize a date-range preset id.
 *
 * @param {unknown} preset Raw preset id.
 * @returns {"default"|"7d"|"30d"|"90d"|"1y"} Known preset, else default.
 */
function normalizeDateRangePreset(preset) {
  return DATE_RANGE_PRESETS.includes(preset) ? preset : "default";
}

/**
 * Resolve ISO window bounds for a date-range preset.
 *
 * @param {unknown} preset Preset id (`default` omits bounds).
 * @param {Date|string|number} [now] Clock used for `until` (injectable for tests).
 * @returns {{since: string, until: string} | null} Encoded bounds, or null when unset.
 */
export function resolveWindowBounds(preset, now = new Date()) {
  const id = normalizeDateRangePreset(preset);
  const durationMs = DATE_RANGE_DURATIONS_MS[id];
  if (!durationMs) {
    return null;
  }
  const untilDate = now instanceof Date ? new Date(now.getTime()) : new Date(now);
  if (Number.isNaN(untilDate.getTime())) {
    return null;
  }
  const sinceDate = new Date(untilDate.getTime() - durationMs);
  return {
    since: sinceDate.toISOString(),
    until: untilDate.toISOString(),
  };
}

/**
 * Panel-range and overview aria copy for the active date-range preset.
 *
 * @param {unknown} preset Preset id.
 * @returns {{
 *   overviewAria: string,
 *   daily: string,
 *   projects: string,
 *   tools: string,
 *   writeRead: string,
 *   efficiency: string,
 *   models: string,
 *   modelTrends: string,
 *   firstPrompt: string,
 * }} Label map for windowed panels.
 */
export function panelRangeLabels(preset) {
  const id = normalizeDateRangePreset(preset);
  if (id === "default") {
    return { ...DEFAULT_PANEL_RANGE_LABELS };
  }
  const windowLabel = DATE_RANGE_WINDOW_LABELS[id];
  return {
    overviewAria: `${windowLabel} overview`,
    daily: windowLabel,
    projects: windowLabel,
    tools: windowLabel,
    skillsNested: windowLabel,
    writeRead: windowLabel,
    efficiency: windowLabel,
    models: windowLabel,
    modelTrends: `${windowLabel} · by message`,
    firstPrompt: `Average session length by prompt detail · ${windowLabel}`,
  };
}

/**
 * Hidden-row count for the metrics Sessions panel ellipsis (``total − 20``).
 *
 * @param {number} total
 * @returns {number}
 */
export function sessionsEllipsisCount(total) {
  const n = Number(total) || 0;
  return n > 20 ? n - 20 : 0;
}

/**
 * Whether top/bottom pagination chrome should show on the sessions list.
 *
 * @param {number} total
 * @param {25 | 50 | 100 | "all"} perPage
 * @returns {boolean}
 */
export function sessionsPaginationVisible(total, perPage) {
  if (perPage === "all") {
    return false;
  }
  return (Number(total) || 0) > perPage;
}

/**
 * Truncated pagination page tokens (sibling/boundary windows with ellipsis).
 *
 * Same algorithm shape as common UI kits (``siblingCount`` / ``boundaryCount``).
 * Defaults to ``siblingCount=2`` (up to five pages around current) and
 * ``boundaryCount=1``. Returns page numbers and ``"ellipsis"`` — prev/next are separate.
 *
 * @param {number} page Current 1-based page.
 * @param {number} count Total pages.
 * @param {{siblingCount?: number, boundaryCount?: number}} [options]
 * @returns {Array<number | "ellipsis">}
 */
export function buildTruncatedPaginationItems(page, count, options = {}) {
  const total = Math.max(0, Math.floor(Number(count) || 0));
  if (total <= 0) {
    return [];
  }
  const current = Math.min(Math.max(1, Math.floor(Number(page) || 1)), total);
  const siblingCount = Math.max(
    0,
    Number.isFinite(options.siblingCount)
      ? Math.floor(options.siblingCount)
      : 2,
  );
  const boundaryCount = Math.max(
    0,
    Number.isFinite(options.boundaryCount)
      ? Math.floor(options.boundaryCount)
      : 1,
  );

  const range = (start, end) => {
    const length = end - start + 1;
    if (length <= 0) {
      return [];
    }
    return Array.from({ length }, (_, index) => start + index);
  };

  const startPages = range(1, Math.min(boundaryCount, total));
  const endPages = range(
    Math.max(total - boundaryCount + 1, boundaryCount + 1),
    total,
  );
  const siblingsStart = Math.max(
    Math.min(current - siblingCount, total - boundaryCount - siblingCount * 2 - 1),
    boundaryCount + 2,
  );
  const siblingsEnd = Math.min(
    Math.max(current + siblingCount, boundaryCount + siblingCount * 2 + 2),
    total - boundaryCount - 1,
  );

  return [
    ...startPages,
    ...(siblingsStart > boundaryCount + 2
      ? ["ellipsis"]
      : boundaryCount + 1 < total - boundaryCount
        ? [boundaryCount + 1]
        : []),
    ...range(siblingsStart, siblingsEnd),
    ...(siblingsEnd < total - boundaryCount - 1
      ? ["ellipsis"]
      : total - boundaryCount > boundaryCount
        ? [total - boundaryCount]
        : []),
    ...endPages,
  ];
}

/**
 * Build render rows for the capped Sessions panel from a ``sessions_ends`` payload.
 *
 * @param {{total: number, newest?: object[], oldest?: object[]}} ends
 * @returns {Array<{kind: "session", session: object} | {kind: "more", count: number}>}
 */
export function buildSessionsPanelRows(ends) {
  const newest = Array.isArray(ends?.newest) ? ends.newest : [];
  const oldest = Array.isArray(ends?.oldest) ? ends.oldest : [];
  const more = sessionsEllipsisCount(ends?.total);
  /** @type {Array<{kind: "session", session: object} | {kind: "more", count: number}>} */
  const rows = newest.map((session) => ({ kind: "session", session }));
  if (more > 0) {
    rows.push({ kind: "more", count: more });
  }
  for (const session of oldest) {
    rows.push({ kind: "session", session });
  }
  return rows;
}

function normalizeViewState(state) {
  const dateRange = normalizeDateRangePreset(state?.dateRange);
  const window =
    dateRange === "default"
      ? null
      : state?.window &&
          typeof state.window === "object" &&
          typeof state.window.since === "string" &&
          typeof state.window.until === "string"
        ? { since: state.window.since, until: state.window.until }
        : resolveWindowBounds(dateRange);
  return {
    harnesses: sortedHarnesses(state?.harnesses ?? []),
    selected: sortedHarnesses(state?.selected ?? []),
    mode: state?.mode === "compare" ? "compare" : "aggregate",
    dateRange,
    window,
  };
}

/**
 * Apply one deterministic dashboard state transition.
 *
 * @param {{harnesses: string[], selected: string[], mode: string, dateRange?: string, window?: {since: string, until: string}|null}} state Current state.
 * @param {Record<string, unknown>} action Transition description.
 * @returns {{state: object, effect: "none"|"render"|"refetch"}} Next state and effect.
 */
export function transitionViewState(state, action) {
  const current = normalizeViewState(state);
  const type = action?.type;
  if (type === "discover") {
    const harnesses = sortedHarnesses(action.harnesses ?? []);
    return {
      state: {
        harnesses,
        selected: [...harnesses],
        mode: current.mode,
        dateRange: current.dateRange,
        window: current.window,
      },
      effect: "render",
    };
  }
  if (type === "mode") {
    const mode = action.mode === "compare" ? "compare" : "aggregate";
    return {
      state: { ...current, mode },
      effect: mode === current.mode ? "none" : "render",
    };
  }
  if (type === "daterange") {
    const dateRange = normalizeDateRangePreset(action.preset);
    if (dateRange === current.dateRange) {
      return { state: current, effect: "none" };
    }
    const window = resolveWindowBounds(dateRange, action.now ?? new Date());
    return {
      state: { ...current, dateRange, window },
      effect: "refetch",
    };
  }
  if (type === "toggle") {
    const harness = action.harness;
    if (!current.harnesses.includes(harness)) {
      return { state: current, effect: "none" };
    }
    const includes = current.selected.includes(harness);
    if (includes && current.selected.length === 1) {
      return { state: current, effect: "none" };
    }
    const selected = includes
      ? current.selected.filter((item) => item !== harness)
      : sortedHarnesses([...current.selected, harness]);
    return { state: { ...current, selected }, effect: "refetch" };
  }
  if (type === "all") {
    if (action.selected === false || current.harnesses.length === 0) {
      return { state: current, effect: "none" };
    }
    const changed =
      current.selected.length !== current.harnesses.length ||
      current.selected.some((item, index) => item !== current.harnesses[index]);
    return {
      state: { ...current, selected: [...current.harnesses] },
      effect: changed ? "refetch" : "none",
    };
  }
  return { state: current, effect: "none" };
}

/**
 * Sum aligned values for selected harnesses without mutating the source.
 *
 * @param {Record<string, unknown[]>} series Harness-keyed aligned arrays.
 * @param {Iterable<string>} selected Selected harness keys.
 * @param {number} [length] Explicit output length.
 * @returns {number[]} Element-wise sums.
 */
export function sumAligned(series, selected, length) {
  const size = alignedLength(series, selected, length);
  const result = Array(size).fill(0);
  for (const harness of orderedSelection(selected)) {
    const values = seriesFor(series, harness, size);
    values.forEach((value, index) => {
      result[index] += value;
    });
  }
  return result;
}

/**
 * Compute selected-harness weighted averages for aligned buckets.
 *
 * @param {Record<string, unknown[]>} averages Harness-keyed averages.
 * @param {Record<string, unknown[]>} counts Harness-keyed observation counts.
 * @param {Iterable<string>} selected Selected harness keys.
 * @param {number} [length] Explicit output length.
 * @returns {number[]} Weighted averages with zero guards.
 */
export function weightedSeries(averages, counts, selected, length) {
  const size = Math.max(
    alignedLength(averages, selected, length),
    alignedLength(counts, selected, length),
  );
  const weighted = Array(size).fill(0);
  const observations = Array(size).fill(0);
  for (const harness of orderedSelection(selected)) {
    const harnessAverages = seriesFor(averages, harness, size);
    const harnessCounts = seriesFor(counts, harness, size);
    for (let index = 0; index < size; index += 1) {
      weighted[index] += harnessAverages[index] * harnessCounts[index];
      observations[index] += harnessCounts[index];
    }
  }
  return weighted.map((total, index) =>
    observations[index] > 0 ? total / observations[index] : 0,
  );
}

/**
 * Derive the four mode-independent KPI card models.
 *
 * @param {Record<string, unknown>} overview Overview endpoint payload.
 * @param {Iterable<string>} selected Selected harness keys.
 * @returns {object[]} Ordered KPI card models.
 */
export function deriveOverviewCards(overview, selected) {
  const payload = safeObject(overview);
  const perHarness = safeObject(payload.per_harness);
  const totals = {
    sessions: 0,
    messages: 0,
    previousSessions: 0,
    previousMessages: 0,
  };
  for (const harness of orderedSelection(selected)) {
    const values = safeObject(perHarness[harness]);
    totals.sessions += finiteNumber(values.sessions);
    totals.messages += finiteNumber(values.messages);
    totals.previousSessions += finiteNumber(values.prev_sessions);
    totals.previousMessages += finiteNumber(values.prev_messages);
  }
  const projects = finiteNumber(payload.distinct_projects);
  const previousProjects = finiteNumber(payload.prev_distinct_projects);
  const average = totals.sessions > 0 ? totals.messages / totals.sessions : 0;
  const previousAverage =
    totals.previousSessions > 0 ? totals.previousMessages / totals.previousSessions : 0;
  const roundedAverage = Math.round(average * 10) / 10;
  return [
    {
      key: "sessions",
      label: "Sessions",
      value: totals.sessions,
      delta: formatDelta(totals.sessions, totals.previousSessions),
    },
    {
      key: "messages",
      label: "Messages",
      value: totals.messages,
      delta: formatDelta(totals.messages, totals.previousMessages),
    },
    {
      key: "projects",
      label: "Projects",
      value: projects,
      delta: formatDelta(projects, previousProjects),
    },
    {
      key: "average",
      label: "Avg Msgs / Session",
      value: roundedAverage,
      delta: formatDelta(average, previousAverage),
    },
  ];
}

/**
 * Derive a selected-harness proportional breakdown for one KPI.
 *
 * @param {Record<string, unknown>} overview Overview endpoint payload.
 * @param {Iterable<string>} selected Selected harness keys.
 * @param {"sessions"|"messages"|"projects"|"average"} metric KPI key.
 * @returns {object[]} Ordered harness value/share models.
 */
export function deriveHarnessBreakdown(overview, selected, metric) {
  const perHarness = safeObject(safeObject(overview).per_harness);
  const rows = orderedSelection(selected).map((harness) => {
    const values = safeObject(perHarness[harness]);
    let value;
    if (metric === "average") {
      const sessions = finiteNumber(values.sessions);
      value = sessions > 0 ? finiteNumber(values.messages) / sessions : 0;
    } else {
      value = finiteNumber(values[metric]);
    }
    return {
      harness,
      label: displayHarness(harness),
      value: Math.round(value * 10) / 10,
    };
  });
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  return rows.map((row) => ({
    ...row,
    share: total > 0 ? Math.round((row.value * 1000) / total) / 10 : 0,
  }));
}

/**
 * Build the exact ordered eight-cell all-time recap model.
 *
 * @param {Record<string, unknown>} wrapped Wrapped endpoint payload.
 * @returns {object[]} Ordered factual cell models.
 */
export function buildWrappedPanel(wrapped) {
  const payload = safeObject(wrapped);
  const totals = safeObject(payload.totals);
  const span = safeObject(totals.span);
  const busiest = safeObject(payload.busiest_harness);
  const streak = safeObject(payload.best_streak);
  const marathon = safeObject(payload.marathon_session);
  const peak = safeObject(payload.peak_hour);
  const tool = safeObject(payload.top_tool);
  const spanSubtitle =
    span.start && span.end
      ? `${finiteNumber(span.days)} days · ${formatShortDate(span.start)} – ${formatShortDate(span.end)}`
      : "—";
  const streakSubtitle =
    streak.start && streak.end
      ? `${formatShortDate(streak.start)} – ${formatShortDate(streak.end)}`
      : "—";
  const marathonSubtitle =
    marathon.project_name || marathon.harness
      ? [displayValue(marathon.project_name), displayHarness(marathon.harness)]
          .filter((value) => value !== "—" && value !== "Unknown")
          .join(" · ") || "—"
      : "—";
  const marathonSubtitleTitle = projectHoverTitle(
    marathon.project_name,
    marathon.project_id,
  );
  const hour = peak.hour;
  const peakHour =
    typeof hour === "number" && Number.isInteger(hour)
      ? `${String(hour).padStart(2, "0")}:00`
      : "—";
  return [
    {
      key: "sessions",
      label: "Total Sessions",
      value: String(finiteNumber(totals.sessions)),
      subtitle: spanSubtitle,
    },
    {
      key: "messages",
      label: "Total Messages",
      value: String(finiteNumber(totals.messages)),
      subtitle: "All time",
    },
    {
      key: "projects",
      label: "Distinct Projects",
      value: String(finiteNumber(payload.distinct_projects)),
      subtitle: "All time",
    },
    {
      key: "harness",
      label: "Busiest Harness",
      value: busiest.name ? displayHarness(busiest.name) : "—",
      subtitle: busiest.name ? `${finiteNumber(busiest.pct)}% of sessions` : "—",
    },
    {
      key: "streak",
      label: "Best Streak",
      value: streak.days ? `${finiteNumber(streak.days)} days` : "0 days",
      subtitle: streakSubtitle,
    },
    {
      key: "marathon",
      label: "Marathon Session",
      value:
        marathon.messages === null || marathon.messages === undefined
          ? "—"
          : `${finiteNumber(marathon.messages)} messages`,
      subtitle: marathonSubtitle,
      subtitleTitle: marathonSubtitleTitle,
    },
    {
      key: "peak",
      label: "Peak Hour (UTC)",
      value: peakHour,
      subtitle: `${finiteNumber(peak.count)} sessions`,
    },
    {
      key: "tool",
      label: "Top Tool",
      value: displayValue(tool.name),
      subtitle: `${finiteNumber(tool.calls)} calls`,
    },
  ];
}

/**
 * Format a signed rounded percentage change.
 *
 * @param {unknown} current Current value.
 * @param {unknown} previous Previous value.
 * @returns {{text: string, trend: "up"|"down"|"neutral"}} Display delta.
 */
export function formatDelta(current, previous) {
  const currentValue = finiteNumber(current);
  const previousValue = finiteNumber(previous);
  if (previousValue === 0) {
    return currentValue > 0
      ? { text: "New", trend: "up" }
      : { text: "No change", trend: "neutral" };
  }
  const percentage = Math.round(((currentValue - previousValue) / previousValue) * 100);
  if (percentage === 0) {
    return { text: "No change", trend: "neutral" };
  }
  return {
    text: `${percentage > 0 ? "+" : ""}${percentage}%`,
    trend: percentage > 0 ? "up" : "down",
  };
}

/**
 * Return a deterministic canvas height preserving all category labels.
 *
 * @param {unknown} labelCount Number of labels.
 * @param {{minimum?: number, perLabel?: number}} [options] Sizing overrides.
 * @returns {number} Canvas height in CSS pixels.
 */
export function chartHeight(labelCount, options) {
  const settings = safeObject(options);
  const minimum = finiteNumber(settings.minimum) || 240;
  const perLabel = finiteNumber(settings.perLabel) || 34;
  const count = Math.max(0, Math.floor(finiteNumber(labelCount)));
  return Math.max(minimum, count * perLabel);
}

/**
 * Build a concise accessible summary for a chart panel model.
 *
 * Reads only ``empty``, ``labels``, and ``datasets`` from the model. Empty
 * panels get an explicit no-data sentence; populated panels list measured
 * label/value pairs per dataset.
 *
 * @param {string} title Chart title.
 * @param {string} mode View mode (``aggregate`` or ``compare``).
 * @param {Record<string, unknown>} model Panel model from a builder.
 * @returns {string} Content-bearing accessible summary.
 */
export function summarizeChartPanel(title, mode, model) {
  const panel = safeObject(model);
  const modeLabel = mode === "compare" ? "Compare" : "Aggregate";
  const heading = `${displayValue(title, "Chart")}. ${modeLabel} view.`;
  if (panel.empty) {
    return `${heading} No data in this period.`;
  }
  const labels = Array.isArray(panel.labels) ? panel.labels : [];
  const datasets = Array.isArray(panel.datasets) ? panel.datasets : [];
  const fragments = datasets.map((dataset) => {
    const entry = safeObject(dataset);
    const seriesLabel = displayValue(entry.label, "Series");
    const data = Array.isArray(entry.data) ? entry.data : [];
    const pairs = labels.map((label, index) => {
      const raw = data[index];
      const rendered =
        raw === null || raw === undefined || !Number.isFinite(Number(raw))
          ? "—"
          : String(Number(raw));
      return `${displayValue(label)} ${rendered}`;
    });
    return `${seriesLabel}: ${pairs.join(", ")}`;
  });
  return `${heading} ${fragments.join("; ")}.`;
}

/** Build the Daily Activity chart model. */
export function buildDailyPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.labels)
    ? source.labels
    : Array.isArray(source.days)
      ? source.days
      : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, labels, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, labels.length))];
  return panelModel("bar", labels, datasets, { stacked: mode === "compare" });
}

/** Build the Sessions by Project chart model. */
export function buildProjectsPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const ids = Array.isArray(source.projects) ? source.projects : [];
  const labels = Array.isArray(source.labels) ? source.labels : ids;
  const labelTitles = labels.map((label, index) => projectHoverTitle(label, ids[index]));
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, ids, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, ids.length))];
  return panelModel("bar", labels, datasets, {
    indexAxis: "y",
    stacked: mode === "compare",
    height: chartHeight(labels.length),
    labelTitles,
  });
}

/** Build the Tool Distribution chart model. */
export function buildToolsPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.tools) ? source.tools : [];
  if (mode === "compare") {
    return panelModel(
      "bar",
      labels,
      selectedDatasets(source.calls, selected, labels, colors),
      { indexAxis: "y", stacked: true, height: chartHeight(labels.length) },
    );
  }
  const dataset = aggregateDataset("Calls", sumAligned(source.calls, selected, labels.length));
  dataset.backgroundColor = labels.map((_, index) => PALETTE[index % PALETTE.length]);
  // Replace aggregateDataset's single fill border — Chart.js would otherwise
  // stroke every arc (and legend swatch) with that one color.
  dataset.borderColor = RING_BORDER;
  return panelModel("doughnut", labels, [dataset]);
}

const SKILL_INVOKERS = Object.freeze(["user", "agent"]);
const SKILL_INVOKER_ALPHA = Object.freeze({ user: 0.55, agent: 1 });

/**
 * Sum one invoker series across selected harnesses for aligned skill indices.
 *
 * @param {Record<string, Record<string, number[]>> | undefined} calls
 * @param {Iterable<string>} selected
 * @param {string} invoker
 * @param {number} length
 * @returns {number[]}
 */
function sumSkillInvoker(calls, selected, invoker, length) {
  const totals = Array.from({ length }, () => 0);
  for (const harness of orderedSelection(selected)) {
    const series = calls?.[harness]?.[invoker];
    for (let index = 0; index < length; index += 1) {
      totals[index] += finiteNumber(Array.isArray(series) ? series[index] : 0);
    }
  }
  return totals;
}

/**
 * Convert ``#rrggbb`` to ``rgba(r,g,b,a)`` for invoker opacity in compare mode.
 *
 * @param {string} color
 * @param {number} alpha
 * @returns {string}
 */
function colorWithAlpha(color, alpha) {
  if (typeof color !== "string" || !/^#[0-9a-fA-F]{6}$/.test(color)) {
    return color;
  }
  const value = Number.parseInt(color.slice(1), 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

/**
 * Compare-mode datasets: one stack per ``{harness} · {invoker}``.
 *
 * Harness hue from ``colors``; user stacks use reduced alpha.
 *
 * @param {Record<string, Record<string, number[]>> | undefined} calls
 * @param {Iterable<string>} selected
 * @param {string[]} labels
 * @param {Record<string, string> | undefined} colors
 * @returns {object[]}
 */
function skillCompareDatasets(calls, selected, labels, colors) {
  const keys = orderedSelection(selected);
  const assigned = colors ?? harnessColors(keys);
  const datasets = [];
  for (const harness of keys) {
    const base = assigned[harness];
    for (const invoker of SKILL_INVOKERS) {
      const series = Array.isArray(calls?.[harness]?.[invoker])
        ? calls[harness][invoker]
        : [];
      const data = Array.from({ length: labels.length }, (_, index) =>
        finiteNumber(series[index]),
      );
      const fill = colorWithAlpha(base, SKILL_INVOKER_ALPHA[invoker]);
      datasets.push({
        label: `${displayHarness(harness)} · ${invoker}`,
        data,
        backgroundColor: fill,
        // Match fill so point-style legend + tooltip swatches agree with bars.
        borderColor: fill,
        borderWidth: 1,
      });
    }
  }
  return datasets;
}

/**
 * Payload-rank palette for sunburst skill segments (Tools-like).
 *
 * Hue follows position in the API-ranked ``skills`` list (overall totals), so
 * colors stay stable across windows when overall ranking does. The invoker
 * group arc uses ``AGGREGATE_COLOR`` separately. Callers fade user-side
 * segments with ``colorWithAlpha``.
 *
 * @param {string[]} rankedSkills Skill names in overall payload order.
 * @returns {Map<string, string>} skill name → ``#rrggbb`` base color.
 */
export function assignSkillSunburstColors(rankedSkills) {
  const colorsBySkill = new Map();
  const skillSlotCount = Math.max(PALETTE.length, 1);
  for (let index = 0; index < (rankedSkills ?? []).length; index += 1) {
    const skill = rankedSkills[index];
    if (!skill || colorsBySkill.has(skill)) {
      continue;
    }
    colorsBySkill.set(skill, PALETTE[index % skillSlotCount]);
  }
  return colorsBySkill;
}

/**
 * Nested sunburst mockup: outer skills within invoker groups, inner user/agent.
 *
 * Outer data is ordered user-group skills then agent-group skills so arcs align
 * with inner ``[userTotal, agentTotal]``. Compare mode stays stacked harness×invoker.
 *
 * @param {object | null | undefined} payload `/api/skills` body.
 * @param {Iterable<string>} selected
 * @param {"aggregate"|"compare"} mode
 * @param {Record<string, string> | undefined} colors
 * @returns {object}
 */
export function buildSkillsNestedPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const skills = Array.isArray(source.skills) ? source.skills : [];
  if (mode === "compare") {
    return panelModel(
      "bar",
      skills,
      skillCompareDatasets(source.calls, selected, skills, colors),
      { indexAxis: "y", stacked: true, height: chartHeight(skills.length) },
    );
  }
  const userTotals = sumSkillInvoker(source.calls, selected, "user", skills.length);
  const agentTotals = sumSkillInvoker(source.calls, selected, "agent", skills.length);
  const userSum = userTotals.reduce((sum, value) => sum + value, 0);
  const agentSum = agentTotals.reduce((sum, value) => sum + value, 0);

  const byCountDesc = (left, right) =>
    right.count - left.count || left.index - right.index;
  const userSegments = [];
  const agentSegments = [];
  for (let index = 0; index < skills.length; index += 1) {
    const skill = skills[index];
    if (userTotals[index] > 0) {
      userSegments.push({ skill, count: userTotals[index], index });
    }
    if (agentTotals[index] > 0) {
      agentSegments.push({ skill, count: agentTotals[index], index });
    }
  }
  userSegments.sort(byCountDesc);
  agentSegments.sort(byCountDesc);
  const colorsBySkill = assignSkillSunburstColors(skills);
  const skillColor = (skill) => colorsBySkill.get(skill) ?? PALETTE[0];

  const outerLabels = [
    ...userSegments.map((segment) => segment.skill),
    ...agentSegments.map((segment) => segment.skill),
  ];
  const outerData = [
    ...userSegments.map((segment) => segment.count),
    ...agentSegments.map((segment) => segment.count),
  ];
  const outerBackground = [
    ...userSegments.map((segment) => colorWithAlpha(skillColor(segment.skill), 0.55)),
    ...agentSegments.map((segment) => skillColor(segment.skill)),
  ];
  // Black separators (match-fill borders made opaque agent arcs look borderless
  // while faded user arcs still showed an edge).
  const outerBorder = outerBackground.map(() => RING_BORDER);
  const outer = {
    label: "Skills",
    data: outerData,
    backgroundColor: outerBackground,
    borderColor: outerBorder,
    borderWidth: 1,
  };
  const inner = {
    label: "Invokers",
    data: [userSum, agentSum],
    backgroundColor: [colorWithAlpha(AGGREGATE_COLOR, 0.55), AGGREGATE_COLOR],
    borderColor: [RING_BORDER, RING_BORDER],
    borderWidth: 1,
    weight: 0.6,
  };
  // Unique skill names; agent solid when present, else faded user-only color.
  const legendItems = [];
  const legendSeen = new Set();
  for (let index = 0; index < skills.length; index += 1) {
    const skill = skills[index];
    if (!skill || legendSeen.has(skill)) {
      continue;
    }
    if (userTotals[index] === 0 && agentTotals[index] === 0) {
      continue;
    }
    legendSeen.add(skill);
    const base = skillColor(skill);
    const swatch =
      agentTotals[index] > 0 ? base : colorWithAlpha(base, SKILL_INVOKER_ALPHA.user);
    legendItems.push({ text: skill, fillStyle: swatch, strokeStyle: swatch });
  }
  return panelModel("doughnut", outerLabels, [outer, inner], {
    empty: userSum === 0 && agentSum === 0,
    innerLabels: [...SKILL_INVOKERS],
    legendItems,
  });
}

/**
 * Write share of classified tool calls: writes / (writes + reads).
 *
 * @param {number} writes Write tool-call count.
 * @param {number} reads Read tool-call count.
 * @returns {number} Ratio in [0, 1]. Zero-denominator buckets are ``0`` so the
 *   line stays continuous instead of gapping.
 */
export function writeShare(writes, reads) {
  const writeCount = finiteNumber(writes);
  const readCount = finiteNumber(reads);
  const total = writeCount + readCount;
  return total === 0 ? 0 : writeCount / total;
}

function ratioSeriesHasActivity(writes, reads) {
  return writes.some((writeCount, index) => writeCount + reads[index] > 0);
}

function lineDataset(label, data, color) {
  return {
    ...aggregateDataset(label, data, color),
    tension: 0.3,
    fill: false,
  };
}

/** Build the Write/Read Ratio chart model. */
export function buildWriteReadPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.labels)
    ? source.labels
    : Array.isArray(source.weeks)
      ? source.weeks
      : [];
  const length = labels.length;
  let datasets;
  let empty;
  if (mode === "compare") {
    const keys = orderedSelection(selected);
    const assigned = colors ?? harnessColors(keys);
    empty = true;
    datasets = keys.map((harness) => {
      const writes = seriesFor(source.writes, harness, length);
      const reads = seriesFor(source.reads, harness, length);
      if (ratioSeriesHasActivity(writes, reads)) {
        empty = false;
      }
      const data = writes.map((writeCount, index) => writeShare(writeCount, reads[index]));
      return lineDataset(displayHarness(harness), data, assigned[harness]);
    });
  } else {
    const writes = sumAligned(source.writes, selected, length);
    const reads = sumAligned(source.reads, selected, length);
    empty = !ratioSeriesHasActivity(writes, reads);
    const data = writes.map((writeCount, index) => writeShare(writeCount, reads[index]));
    datasets = [lineDataset("Write share", data, AGGREGATE_COLOR)];
  }
  return panelModel("line", labels, datasets, {
    stacked: false,
    yMax: 1,
    empty,
  });
}

/** Build the Session Efficiency chart model. */
export function buildEfficiencyPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.buckets) ? source.buckets.map(displayHarness) : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, labels, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, labels.length))];
  return panelModel("bar", labels, datasets, { stacked: mode === "compare" });
}

function buildModelsBarPanel(
  payload,
  seriesKey,
  aggregateLabel,
  selected,
  mode,
  colors,
  modelColors,
) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.models) ? source.models : [];
  const palette = modelColors instanceof Map ? modelColors : assignModelColors(labels);
  let datasets;
  if (mode === "compare") {
    datasets = selectedDatasets(source[seriesKey], selected, labels, colors);
  } else {
    const data = sumAligned(source[seriesKey], selected, labels.length);
    const barColors = labels.map((model) => colorForModel(model, palette));
    datasets = [
      {
        ...aggregateDataset(aggregateLabel, data),
        backgroundColor: barColors,
        borderColor: barColors,
      },
    ];
  }
  return panelModel("bar", labels, datasets, {
    indexAxis: "y",
    stacked: mode === "compare",
    height: chartHeight(labels.length),
  });
}

/** Build the Top Models (by conversation) horizontal bar chart model. */
export function buildModelsConversationPanel(
  payload,
  selected,
  mode,
  colors,
  modelColors,
) {
  return buildModelsBarPanel(
    payload,
    "sessions",
    "Sessions",
    selected,
    mode,
    colors,
    modelColors,
  );
}

/** Build the Top Models (by message) horizontal bar chart model. */
export function buildModelsMessagePanel(payload, selected, mode, colors, modelColors) {
  return buildModelsBarPanel(
    payload,
    "messages",
    "Messages",
    selected,
    mode,
    colors,
    modelColors,
  );
}

/** Build the Model Usage over Time stacked area chart model (message grain). */
export function buildModelTrendsPanel(
  payload,
  _selected,
  _mode,
  _colors,
  modelColors,
) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.labels) ? source.labels : [];
  const models = Array.isArray(source.models) ? source.models : [];
  const counts = safeObject(source.counts);
  const palette = modelColors instanceof Map ? modelColors : assignModelColors(models);
  const datasets = models.map((model) => {
    const color = colorForModel(model, palette);
    const values = Array.isArray(counts[model]) ? counts[model] : [];
    return {
      label: model,
      data: Array.from({ length: labels.length }, (_, index) =>
        finiteNumber(values[index]),
      ),
      backgroundColor: color,
      borderColor: color,
      borderWidth: 0,
      pointRadius: 0,
      pointHoverRadius: 0,
      pointBorderWidth: 0,
      tension: .3,
      fill: true,
    };
  });
  return panelModel("line", labels, datasets, {
    stacked: true,
    fill: true,
    omitZeroTooltip: true,
  });
}

/** Build the First-Prompt Quality chart model. */
export function buildFirstPromptPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.labels) ? source.labels.map(displayHarness) : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.avg_msgs, selected, labels, colors)
      : [
          aggregateDataset(
            "Avg messages",
            weightedSeries(source.avg_msgs, source.n, selected, labels.length),
          ),
        ];
  return panelModel("bar", labels, datasets, { stacked: false });
}

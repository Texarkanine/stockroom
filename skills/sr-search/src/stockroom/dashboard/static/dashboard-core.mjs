const PALETTE = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#f43f5e",
  "#06b6d4",
  "#8b5cf6",
  "#ec4899",
  "#84cc16",
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
    empty: !hasValues(datasets),
    ...(options.height === undefined ? {} : { height: options.height }),
  };
}

function aggregateDataset(label, data, color = PALETTE[0]) {
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

function formatShortDate(value) {
  if (typeof value !== "string" || !value) {
    return "—";
  }
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? "—" : shortDateFormatter.format(parsed);
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
 * Apply one deterministic dashboard state transition.
 *
 * @param {{harnesses: string[], selected: string[], mode: string}} state Current state.
 * @param {Record<string, unknown>} action Transition description.
 * @returns {{state: object, effect: "none"|"render"|"refetch"}} Next state and effect.
 */
export function transitionViewState(state, action) {
  const current = {
    harnesses: sortedHarnesses(state?.harnesses ?? []),
    selected: sortedHarnesses(state?.selected ?? []),
    mode: state?.mode === "compare" ? "compare" : "aggregate",
  };
  const type = action?.type;
  if (type === "discover") {
    const harnesses = sortedHarnesses(action.harnesses ?? []);
    return {
      state: { harnesses, selected: [...harnesses], mode: current.mode },
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
    previousProjects: 0,
  };
  for (const harness of orderedSelection(selected)) {
    const values = safeObject(perHarness[harness]);
    totals.sessions += finiteNumber(values.sessions);
    totals.messages += finiteNumber(values.messages);
    totals.previousSessions += finiteNumber(values.prev_sessions);
    totals.previousMessages += finiteNumber(values.prev_messages);
    totals.previousProjects += finiteNumber(values.prev_projects);
  }
  const projects = finiteNumber(payload.distinct_projects);
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
      delta: formatDelta(projects, totals.previousProjects),
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
    },
    {
      key: "peak",
      label: "Peak Hour",
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

/** Build the Daily Activity chart model. */
export function buildDailyPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.days) ? source.days : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, labels, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, labels.length))];
  return panelModel("bar", labels, datasets, { stacked: mode === "compare" });
}

/** Build the Sessions by Project chart model. */
export function buildProjectsPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.projects) ? source.projects : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, labels, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, labels.length))];
  return panelModel("bar", labels, datasets, {
    indexAxis: "y",
    stacked: mode === "compare",
    height: chartHeight(labels.length),
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
  return panelModel("doughnut", labels, [dataset]);
}

/** Build the Write/Read Ratio chart model. */
export function buildWriteReadPanel(payload, selected, mode) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.weeks) ? source.weeks : [];
  const writes = aggregateDataset(
    "Writes",
    sumAligned(source.writes, selected, labels.length),
    PALETTE[0],
  );
  const reads = aggregateDataset(
    "Reads",
    sumAligned(source.reads, selected, labels.length),
    PALETTE[2],
  );
  writes.backgroundColor = `${PALETTE[0]}33`;
  reads.backgroundColor = `${PALETTE[2]}33`;
  writes.fill = true;
  reads.fill = true;
  writes.tension = 0.3;
  reads.tension = 0.3;
  return panelModel("line", labels, [writes, reads], { stacked: false });
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

/** Build the Model Distribution chart model. */
export function buildModelsPanel(payload, selected, mode, colors) {
  const source = safeObject(payload);
  const labels = Array.isArray(source.models) ? source.models : [];
  const datasets =
    mode === "compare"
      ? selectedDatasets(source.sessions, selected, labels, colors)
      : [aggregateDataset("Sessions", sumAligned(source.sessions, selected, labels.length))];
  return panelModel("bar", labels, datasets, {
    indexAxis: "y",
    stacked: mode === "compare",
    height: chartHeight(labels.length),
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

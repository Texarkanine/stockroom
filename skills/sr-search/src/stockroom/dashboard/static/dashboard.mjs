import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsPanel,
  buildProjectsPanel,
  buildToolsPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  deriveHarnessBreakdown,
  deriveOverviewCards,
  displayHarness,
  harnessColors,
  summarizeChartPanel,
  transitionViewState,
} from "./dashboard-core.mjs";
import {
  DashboardRequestError,
  createRequestGate,
  fetchSnapshot,
} from "./dashboard-data.mjs";

const elements = {
  dashboard: document.querySelector("#dashboard"),
  selector: document.querySelector("#harness-selector"),
  harnessSummary: document.querySelector("#harness-summary"),
  harnessOptions: document.querySelector("#harness-options"),
  modeSelector: document.querySelector("#mode-selector"),
  status: document.querySelector("#status"),
  error: document.querySelector("#error"),
  lastSync: document.querySelector("#last-sync"),
  sessionRows: document.querySelector("#session-rows"),
  wrappedGrid: document.querySelector("#wrapped-grid"),
};

const requestGate = createRequestGate();
const chartRegistry = new Map();
const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
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
let state = {
  harnesses: [],
  selected: [],
  mode: "aggregate",
  snapshot: null,
};

function setStatus(message) {
  elements.status.textContent = message;
}

function clearError() {
  elements.error.textContent = "";
  elements.error.hidden = true;
}

function showError(error) {
  const message =
    error instanceof DashboardRequestError
      ? error.message
      : "Dashboard request failed";
  elements.error.textContent = error?.action
    ? `${message}. ${error.action}.`
    : `${message}.`;
  elements.error.hidden = false;
}

function setBusy(busy) {
  elements.dashboard.setAttribute("aria-busy", String(busy));
  for (const input of elements.modeSelector.querySelectorAll("input")) {
    input.disabled = busy;
  }
}

function appendHarnessRow({ harness, label, color, checked, disabled, onChange }) {
  const row = document.createElement("label");
  row.className = "check-row";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.value = harness;
  input.checked = checked;
  input.disabled = disabled;
  input.addEventListener("change", onChange);
  const dot = document.createElement("span");
  dot.className = "harness-dot";
  dot.setAttribute("aria-hidden", "true");
  dot.style.setProperty("--harness-color", color);
  row.append(input, dot, document.createTextNode(label));
  elements.harnessOptions.append(row);
}

function renderHarnessControls() {
  elements.harnessOptions.replaceChildren();
  const colors = harnessColors(state.harnesses);
  if (state.harnesses.length === 0) {
    elements.harnessSummary.textContent = "No harnesses";
    const empty = document.createElement("span");
    empty.textContent = "No harness data yet";
    elements.harnessOptions.append(empty);
    return;
  }

  if (state.selected.length === state.harnesses.length) {
    elements.harnessSummary.textContent = "All harnesses";
  } else if (state.selected.length === 1) {
    elements.harnessSummary.textContent = displayHarness(state.selected[0]);
  } else {
    elements.harnessSummary.textContent = `${state.selected.length} harnesses`;
  }

  appendHarnessRow({
    harness: "__all__",
    label: "All harnesses",
    color: "var(--accent)",
    checked: state.selected.length === state.harnesses.length,
    disabled: state.selected.length === state.harnesses.length,
    onChange: (event) => {
      applyTransition({
        type: "all",
        selected: event.currentTarget.checked,
      });
    },
  });
  for (const harness of state.harnesses) {
    const checked = state.selected.includes(harness);
    appendHarnessRow({
      harness,
      label: displayHarness(harness),
      color: colors[harness],
      checked,
      disabled: checked && state.selected.length === 1,
      onChange: () => applyTransition({ type: "toggle", harness }),
    });
  }
}

function parseDisplayDate(value, dateOnly = false) {
  if (typeof value !== "string" || !value) {
    return null;
  }
  const parsed = new Date(dateOnly ? `${value}T00:00:00` : value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(value, dateOnly = false) {
  const parsed = parseDisplayDate(value, dateOnly);
  return parsed ? (dateOnly ? dateFormatter : dateTimeFormatter).format(parsed) : "—";
}

function renderBreakdown(container, rows, colors) {
  container.replaceChildren();
  for (const row of rows) {
    const item = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "metric-bar-heading";
    const label = document.createElement("span");
    label.textContent = row.label;
    const value = document.createElement("span");
    value.textContent = numberFormatter.format(row.value);
    heading.append(label, value);
    const track = document.createElement("div");
    track.className = "metric-bar-track";
    track.setAttribute("aria-hidden", "true");
    const fill = document.createElement("div");
    fill.className = "metric-bar-fill";
    fill.style.setProperty("--share", `${Math.max(0, Math.min(100, row.share))}%`);
    fill.style.setProperty("--harness-color", colors[row.harness]);
    track.append(fill);
    item.append(heading, track);
    container.append(item);
  }
}

function renderOverview(overview) {
  const colors = harnessColors(state.harnesses);
  for (const card of deriveOverviewCards(overview, state.selected)) {
    const element = document.querySelector(`#kpi-${card.key}`);
    element.querySelector("[data-value]").textContent = numberFormatter.format(card.value);
    const delta = element.querySelector("[data-delta]");
    delta.textContent = card.delta.text;
    delta.dataset.trend = card.delta.trend;
    renderBreakdown(
      element.querySelector("[data-breakdown]"),
      deriveHarnessBreakdown(overview, state.selected, card.key),
      colors,
    );
  }
}

function chartLabels(name, labels) {
  return name === "daily" || name === "write-read"
    ? labels.map((label) => formatDate(label, true))
    : labels;
}

function chartOptions(model) {
  const styles = getComputedStyle(document.documentElement);
  const text = styles.getPropertyValue("--text").trim();
  const muted = styles.getPropertyValue("--muted").trim();
  const border = styles.getPropertyValue("--border").trim();
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: model.indexAxis,
    animation: false,
    plugins: {
      legend: {
        display:
          model.kind === "doughnut" ||
          model.datasets.length > 1 ||
          state.mode === "compare",
        labels: {
          color: text,
          usePointStyle: true,
          boxWidth: 10,
        },
      },
      tooltip: {
        mode: "index",
        intersect: false,
      },
    },
  };
  if (model.kind !== "doughnut") {
    options.scales = {
      x: {
        stacked: model.stacked,
        ticks: { color: muted },
        grid: { color: border },
      },
      y: {
        stacked: model.stacked,
        beginAtZero: true,
        ticks: { color: muted },
        grid: { color: border },
      },
    };
  }
  return options;
}

function renderChart(name, title, model) {
  const canvas = document.querySelector(`#${name}-chart`);
  const wrapper = document.querySelector(`#${name}-chart-wrap`);
  const empty = document.querySelector(`#${name}-empty`);
  chartRegistry.get(name)?.destroy();
  chartRegistry.delete(name);
  wrapper.style.height = `${model.height ?? 280}px`;
  canvas.hidden = model.empty;
  empty.hidden = !model.empty;
  const summary = summarizeChartPanel(title, state.mode, model);
  canvas.setAttribute("aria-label", summary);
  canvas.textContent = summary;
  if (model.empty) {
    return;
  }
  if (typeof window.Chart !== "function") {
    canvas.hidden = true;
    empty.textContent = "Chart runtime unavailable.";
    empty.hidden = false;
    return;
  }
  const chart = new window.Chart(canvas, {
    type: model.kind,
    data: {
      labels: chartLabels(name, model.labels),
      datasets: model.datasets.map((dataset) => ({ ...dataset })),
    },
    options: chartOptions(model),
  });
  chartRegistry.set(name, chart);
}

function appendCell(row, value, className) {
  const cell = document.createElement("td");
  if (className) {
    cell.className = className;
  }
  cell.textContent = value ?? "—";
  row.append(cell);
  return cell;
}

function renderSessions(sessions) {
  elements.sessionRows.replaceChildren();
  if (!Array.isArray(sessions) || sessions.length === 0) {
    const row = document.createElement("tr");
    const cell = appendCell(row, "No recent sessions for this selection.");
    cell.colSpan = 6;
    elements.sessionRows.append(row);
    return;
  }
  const colors = harnessColors(state.harnesses);
  for (const session of sessions) {
    const row = document.createElement("tr");
    const started = appendCell(row, formatDate(session.started));
    if (session.started) {
      started.title = session.started;
    }
    const harnessCell = document.createElement("td");
    const harnessLabel = document.createElement("span");
    harnessLabel.className = "harness-label";
    const dot = document.createElement("span");
    dot.className = "harness-dot";
    dot.setAttribute("aria-hidden", "true");
    dot.style.setProperty("--harness-color", colors[session.harness] ?? "var(--accent)");
    harnessLabel.append(dot, document.createTextNode(displayHarness(session.harness)));
    harnessCell.append(harnessLabel);
    row.append(harnessCell);
    appendCell(row, session.project_name || "—");
    appendCell(row, numberFormatter.format(Number(session.msgs) || 0));
    appendCell(row, session.model || "—");
    appendCell(row, session.prompt || "—", "prompt-cell");
    elements.sessionRows.append(row);
  }
}

function renderWrapped(wrapped) {
  elements.wrappedGrid.replaceChildren();
  for (const cell of buildWrappedPanel(wrapped)) {
    const article = document.createElement("article");
    article.className = "wrapped-cell";
    const label = document.createElement("p");
    label.className = "wrapped-label";
    label.textContent = cell.label;
    const value = document.createElement("p");
    value.className = "wrapped-value";
    value.textContent = cell.value;
    const subtitle = document.createElement("p");
    subtitle.className = "wrapped-subtitle";
    subtitle.textContent = cell.subtitle;
    article.append(label, value, subtitle);
    elements.wrappedGrid.append(article);
  }
}

function renderDashboard() {
  if (!state.snapshot) {
    return;
  }
  const { snapshot } = state;
  const colors = harnessColors(state.harnesses);
  const lastSync = snapshot.overview?.last_sync;
  elements.lastSync.textContent = formatDate(lastSync);
  if (lastSync) {
    elements.lastSync.title = lastSync;
  } else {
    elements.lastSync.removeAttribute("title");
  }
  renderOverview(snapshot.overview);
  renderChart(
    "daily",
    "Daily session activity",
    buildDailyPanel(snapshot.trends?.daily, state.selected, state.mode, colors),
  );
  renderChart(
    "projects",
    "Sessions by project",
    buildProjectsPanel(snapshot.projects, state.selected, state.mode, colors),
  );
  renderChart(
    "tools",
    "Tool distribution",
    buildToolsPanel(snapshot.tools, state.selected, state.mode, colors),
  );
  renderChart(
    "write-read",
    "Weekly write and read tool calls",
    buildWriteReadPanel(snapshot.trends?.weekly, state.selected, state.mode),
  );
  renderChart(
    "efficiency",
    "Session efficiency",
    buildEfficiencyPanel(snapshot.efficiency, state.selected, state.mode, colors),
  );
  renderChart(
    "models",
    "Model distribution",
    buildModelsPanel(snapshot.models, state.selected, state.mode, colors),
  );
  renderChart(
    "first-prompt",
    "First-prompt quality",
    buildFirstPromptPanel(
      snapshot.efficiency?.first_prompt,
      state.selected,
      state.mode,
      colors,
    ),
  );
  renderSessions(snapshot.sessions);
  renderWrapped(snapshot.wrapped);
}

function applyTransition(action) {
  const transition = transitionViewState(state, action);
  state = { ...state, ...transition.state };
  renderHarnessControls();
  if (transition.effect === "refetch") {
    void refreshDashboard();
  } else if (transition.effect === "render" && state.snapshot) {
    renderDashboard();
  } else if (action.type === "toggle") {
    setStatus("At least one harness must remain selected.");
  }
}

async function refreshDashboard(initial = false) {
  const request = requestGate.begin();
  setBusy(true);
  clearError();
  setStatus(initial || !state.snapshot ? "Loading dashboard…" : "Refreshing dashboard…");
  try {
    const snapshot = await fetchSnapshot(
      window.fetch.bind(window),
      state.selected,
      { signal: request.signal },
    );
    request.commit(() => {
      if (state.harnesses.length === 0) {
        const discovered = transitionViewState(state, {
          type: "discover",
          harnesses: Object.keys(snapshot.overview?.per_harness ?? {}),
        });
        state = { ...state, ...discovered.state };
      }
      state.snapshot = snapshot;
      renderHarnessControls();
      renderDashboard();
      clearError();
      setStatus(
        state.harnesses.length === 0
          ? "Dashboard loaded. No harness data is available yet."
          : `Dashboard loaded for ${state.selected.length} selected harness${state.selected.length === 1 ? "" : "es"}.`,
      );
    });
  } catch (error) {
    if (error?.name !== "AbortError" && request.isCurrent()) {
      showError(error);
      setStatus(
        state.snapshot
          ? "Refresh failed. Showing the previous successful snapshot."
          : "Dashboard could not be loaded.",
      );
    }
  } finally {
    if (request.isCurrent()) {
      setBusy(false);
    }
  }
}

elements.modeSelector.addEventListener("change", (event) => {
  if (event.target instanceof HTMLInputElement && event.target.name === "mode") {
    applyTransition({ type: "mode", mode: event.target.value });
  }
});

document.addEventListener("click", (event) => {
  if (elements.selector.open && !elements.selector.contains(event.target)) {
    elements.selector.open = false;
  }
});

elements.selector.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    elements.selector.open = false;
    elements.selector.querySelector("summary").focus();
  }
});

window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => renderDashboard());

renderHarnessControls();
void refreshDashboard(true);

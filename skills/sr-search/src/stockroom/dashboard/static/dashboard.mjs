import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsPanel,
  buildProjectsPanel,
  buildToolsPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  closePanelHelp,
  deriveHarnessBreakdown,
  deriveOverviewCards,
  displayHarness,
  formatDate,
  harnessColors,
  PANEL_HELP,
  panelRangeLabels,
  projectHoverTitle,
  chartInteraction,
  summarizeChartPanel,
  togglePanelHelp,
  tooltipTitleFromLabelTitles,
  transitionViewState,
} from "./dashboard-core.mjs";
import {
  DashboardRequestError,
  createRequestGate,
  fetchSessionDetail,
  fetchSnapshot,
} from "./dashboard-data.mjs";
import {
  buildSessionDeepLink,
  buildSessionViewSearchParams,
  formatSessionJsonExport,
  formatSessionMarkdownExport,
  isActiveSessionView,
  parseSessionViewParams,
  renderSessionMessageHtml,
  shouldUseHistoryBackForSessionClose,
} from "./dashboard-session.mjs";

// Richer markdown → use export. Do not add markdown-it plugins.
const markdown = window.markdownit({
  html: false,
  linkify: false,
  typographer: false,
});

const elements = {
  dashboard: document.querySelector("#dashboard"),
  metricsPane: document.querySelector("#metrics-pane"),
  sessionPane: document.querySelector("#session-pane"),
  sessionBack: document.querySelector("#session-back"),
  sessionCopyLink: document.querySelector("#session-copy-link"),
  sessionExportMd: document.querySelector("#session-export-md"),
  sessionExportJson: document.querySelector("#session-export-json"),
  sessionTitle: document.querySelector("#session-title"),
  sessionMeta: document.querySelector("#session-meta"),
  sessionError: document.querySelector("#session-error"),
  sessionTurns: document.querySelector("#session-turns"),
  selector: document.querySelector("#harness-selector"),
  harnessSummary: document.querySelector("#harness-summary"),
  harnessOptions: document.querySelector("#harness-options"),
  dateRangeSelector: document.querySelector("#date-range-selector"),
  modeSelector: document.querySelector("#mode-selector"),
  kpiGrid: document.querySelector("#kpi-grid"),
  status: document.querySelector("#status"),
  error: document.querySelector("#error"),
  lastSync: document.querySelector("#last-sync"),
  sessionRows: document.querySelector("#session-rows"),
  wrappedGrid: document.querySelector("#wrapped-grid"),
};

const requestGate = createRequestGate();
const sessionRequestGate = createRequestGate();
const chartRegistry = new Map();
const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
});
let state = {
  harnesses: [],
  selected: [],
  mode: "aggregate",
  dateRange: "default",
  window: null,
  snapshot: null,
};
let openHelpId = null;
let sessionDetail = null;
let sessionView = null;

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

function clearSessionError() {
  elements.sessionError.textContent = "";
  elements.sessionError.hidden = true;
}

function showSessionError(error) {
  const message =
    error instanceof DashboardRequestError
      ? error.message
      : "Session request failed";
  elements.sessionError.textContent = error?.action
    ? `${message}. ${error.action}.`
    : `${message}.`;
  elements.sessionError.hidden = false;
}

function setBusy(busy) {
  elements.dashboard.setAttribute("aria-busy", String(busy));
  for (const input of elements.dateRangeSelector.querySelectorAll("input")) {
    input.disabled = busy;
  }
  for (const input of elements.modeSelector.querySelectorAll("input")) {
    input.disabled = busy;
  }
}

function showMetricsView() {
  document.documentElement.dataset.view = "metrics";
  elements.metricsPane.hidden = false;
  elements.sessionPane.hidden = true;
}

function showSessionView() {
  document.documentElement.dataset.view = "session";
  elements.metricsPane.hidden = true;
  elements.sessionPane.hidden = false;
}

function downloadText(filename, text, mimeType) {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
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
    interaction: chartInteraction(model.indexAxis),
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
        callbacks: {
          title(items) {
            const item = items?.[0];
            if (!item) {
              return "";
            }
            return tooltipTitleFromLabelTitles(
              model.labelTitles,
              item.dataIndex,
              item.label ?? "",
            );
          },
        },
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
        ...(model.yMax === undefined ? {} : { max: model.yMax }),
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
    row.className = "session-row";
    row.tabIndex = 0;
    row.dataset.harness = session.harness ?? "";
    row.dataset.sessionId = session.session_id ?? "";
    row.setAttribute(
      "aria-label",
      `Open session ${session.session_id ?? ""} from ${displayHarness(session.harness)}`,
    );
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
    const projectCell = appendCell(row, session.project_name || "—");
    const projectTitle = projectHoverTitle(session.project_name, session.project_id);
    if (projectTitle) {
      projectCell.title = projectTitle;
    }
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
    if (cell.subtitleTitle) {
      subtitle.title = cell.subtitleTitle;
    }
    article.append(label, value, subtitle);
    elements.wrappedGrid.append(article);
  }
}

function applyPanelRangeLabels() {
  const labels = panelRangeLabels(state.dateRange);
  elements.kpiGrid.setAttribute("aria-label", labels.overviewAria);
  const mapping = [
    ["#daily-panel .panel-range", labels.daily],
    ["#projects-panel .panel-range", labels.projects],
    ["#tools-panel .panel-range", labels.tools],
    ["#write-read-panel .panel-range", labels.writeRead],
    ["#efficiency-panel .panel-range", labels.efficiency],
    ["#models-panel .panel-range", labels.models],
    ["#first-prompt-panel .panel-range", labels.firstPrompt],
  ];
  for (const [selector, text] of mapping) {
    const element = document.querySelector(selector);
    if (element) {
      element.textContent = text;
    }
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
  applyPanelRangeLabels();
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
    "Weekly write share",
    buildWriteReadPanel(snapshot.trends?.weekly, state.selected, state.mode, colors),
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
      { signal: request.signal, window: state.window },
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
      if (!sessionView) {
        setStatus(
          state.harnesses.length === 0
            ? "Dashboard loaded. No harness data is available yet."
            : `Dashboard loaded for ${state.selected.length} selected harness${state.selected.length === 1 ? "" : "es"}.`,
        );
      }
    });
  } catch (error) {
    if (error?.name !== "AbortError" && request.isCurrent()) {
      if (!sessionView) {
        showError(error);
        setStatus(
          state.snapshot
            ? "Refresh failed. Showing the previous successful snapshot."
            : "Dashboard could not be loaded.",
        );
      }
    }
  } finally {
    if (request.isCurrent() && !sessionView) {
      setBusy(false);
    }
  }
}

elements.dateRangeSelector.addEventListener("change", (event) => {
  if (event.target instanceof HTMLInputElement && event.target.name === "date-range") {
    applyTransition({ type: "daterange", preset: event.target.value });
  }
});

elements.modeSelector.addEventListener("change", (event) => {
  if (event.target instanceof HTMLInputElement && event.target.name === "mode") {
    applyTransition({ type: "mode", mode: event.target.value });
  }
});

document.addEventListener("click", (event) => {
  if (elements.selector.open && !elements.selector.contains(event.target)) {
    elements.selector.open = false;
  }
  const infoButton =
    event.target instanceof Element ? event.target.closest(".panel-info") : null;
  if (infoButton instanceof HTMLButtonElement) {
    event.stopPropagation();
    applyHelpOpen(togglePanelHelp(openHelpId, infoButton.dataset.helpId));
    return;
  }
  if (
    openHelpId &&
    event.target instanceof Element &&
    !event.target.closest(".panel-help") &&
    !event.target.closest(".panel-info")
  ) {
    applyHelpOpen(closePanelHelp());
  }
});

elements.selector.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    elements.selector.open = false;
    elements.selector.querySelector("summary").focus();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && openHelpId) {
    applyHelpOpen(closePanelHelp());
  }
});

function applyHelpOpen(nextId) {
  openHelpId = nextId;
  for (const button of document.querySelectorAll(".panel-info")) {
    const helpId = button.dataset.helpId;
    const expanded = helpId === openHelpId;
    button.setAttribute("aria-expanded", expanded ? "true" : "false");
    const panel = document.getElementById(button.getAttribute("aria-controls"));
    if (panel) {
      panel.hidden = !expanded;
    }
  }
}

function initPanelHelpCopy() {
  for (const button of document.querySelectorAll(".panel-info")) {
    const helpId = button.dataset.helpId;
    const panel = document.getElementById(button.getAttribute("aria-controls"));
    const copy = PANEL_HELP[helpId];
    if (panel && copy) {
      panel.textContent = copy;
    }
  }
}

window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => renderDashboard());

initPanelHelpCopy();
renderHarnessControls();

function renderSessionDetail(detail) {
  sessionDetail = detail;
  const harness = detail?.harness ?? sessionView?.harness ?? "";
  const sessionId = detail?.session_id ?? sessionView?.sessionId ?? "";
  elements.sessionTitle.textContent = `${displayHarness(harness)} / ${sessionId}`;
  const project = detail?.project_name || detail?.project_id || "—";
  const started = detail?.started ? formatDate(detail.started) : "—";
  elements.sessionMeta.innerHTML = "";
  const metaBits = [
    ["Harness", displayHarness(harness)],
    ["Project", project],
    ["Started", started],
    ["Session", sessionId],
  ];
  if (detail?.is_subagent) {
    metaBits.push(["Subagent of", detail.parent_session_id || "—"]);
  }
  elements.sessionMeta.append(
    ...metaBits.flatMap(([label, value], index) => {
      const nodes = [];
      if (index > 0) {
        nodes.push(document.createTextNode(" · "));
      }
      const strong = document.createElement("strong");
      strong.textContent = `${label}: `;
      nodes.push(strong, document.createTextNode(String(value)));
      return nodes;
    }),
  );

  elements.sessionTurns.replaceChildren();
  for (const message of detail?.messages ?? []) {
    const turn = document.createElement("article");
    const roleName = message.role || "unknown";
    const sideClass =
      roleName === "user"
        ? "session-turn-user"
        : roleName === "assistant"
          ? "session-turn-assistant"
          : "";
    turn.className = ["session-turn", sideClass].filter(Boolean).join(" ");
    const role = document.createElement("p");
    role.className = "session-turn-role";
    role.textContent = roleName;
    const body = document.createElement("div");
    body.className = "session-turn-body";
    body.innerHTML = renderSessionMessageHtml(message.text || "", (value) =>
      markdown.render(value),
    );
    turn.append(role, body);
    for (const tool of message.tool_calls ?? []) {
      const detailsEl = document.createElement("details");
      detailsEl.className = "session-tool";
      const summary = document.createElement("summary");
      summary.textContent = tool.tool_name || "tool";
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(tool.tool_input ?? {}, null, 2);
      detailsEl.append(summary, pre);
      turn.append(detailsEl);
    }
    elements.sessionTurns.append(turn);
  }
}

async function openSessionView(harness, sessionId, { push = true } = {}) {
  sessionView = { harness, sessionId };
  sessionDetail = null;
  clearSessionError();
  showSessionView();
  elements.sessionTurns.replaceChildren();
  elements.sessionTitle.textContent = `${displayHarness(harness)} / ${sessionId}`;
  elements.sessionMeta.textContent = "Loading session…";
  if (push) {
    const params = buildSessionViewSearchParams(harness, sessionId);
    const next = `${window.location.pathname}?${params.toString()}`;
    window.history.pushState({ view: "session", harness, sessionId }, "", next);
  }
  const request = sessionRequestGate.begin();
  setStatus("Loading session…");
  try {
    const detail = await fetchSessionDetail(
      window.fetch.bind(window),
      harness,
      sessionId,
      { signal: request.signal },
    );
    request.commit(() => {
      if (!isActiveSessionView(sessionView, harness, sessionId)) {
        return;
      }
      renderSessionDetail(detail);
      setStatus(`Loaded session ${sessionId}.`);
    });
  } catch (error) {
    if (
      error?.name !== "AbortError" &&
      request.isCurrent() &&
      isActiveSessionView(sessionView, harness, sessionId)
    ) {
      showSessionError(error);
      elements.sessionMeta.textContent = "Session could not be loaded.";
      setStatus(
        error?.status === 404
          ? "Session not found."
          : "Session could not be loaded.",
      );
    }
  }
}

function closeSessionView({ push = true } = {}) {
  // Abort any in-flight session fetch and invalidate its commit generation.
  sessionRequestGate.begin();
  sessionView = null;
  sessionDetail = null;
  clearSessionError();
  showMetricsView();
  if (push) {
    if (shouldUseHistoryBackForSessionClose(window.history.state)) {
      window.history.back();
      return;
    }
    window.history.replaceState(
      { view: "metrics" },
      "",
      window.location.pathname,
    );
  }
  if (!state.snapshot) {
    void refreshDashboard(true);
    return;
  }
  setStatus(
    `Dashboard loaded for ${state.selected.length} selected harness${state.selected.length === 1 ? "" : "es"}.`,
  );
}

function syncViewFromLocation() {
  const params = parseSessionViewParams(new URLSearchParams(window.location.search));
  if (params) {
    void openSessionView(params.harness, params.sessionId, { push: false });
    return;
  }
  closeSessionView({ push: false });
}

elements.sessionRows.addEventListener("click", (event) => {
  const row =
    event.target instanceof Element ? event.target.closest("tr.session-row") : null;
  if (!(row instanceof HTMLTableRowElement)) {
    return;
  }
  const harness = row.dataset.harness;
  const sessionId = row.dataset.sessionId;
  if (harness && sessionId) {
    void openSessionView(harness, sessionId);
  }
});

elements.sessionRows.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }
  const row = event.target;
  if (!(row instanceof HTMLTableRowElement) || !row.classList.contains("session-row")) {
    return;
  }
  event.preventDefault();
  const harness = row.dataset.harness;
  const sessionId = row.dataset.sessionId;
  if (harness && sessionId) {
    void openSessionView(harness, sessionId);
  }
});

elements.sessionBack.addEventListener("click", () => {
  closeSessionView();
});

elements.sessionCopyLink.addEventListener("click", async () => {
  if (!sessionView) {
    return;
  }
  const link = buildSessionDeepLink(
    window.location.origin + window.location.pathname,
    sessionView.harness,
    sessionView.sessionId,
  );
  try {
    await navigator.clipboard.writeText(link);
    setStatus("Deep-link copied to clipboard.");
  } catch {
    setStatus(link);
  }
});

elements.sessionExportMd.addEventListener("click", () => {
  if (!sessionDetail) {
    return;
  }
  const name = `${sessionDetail.harness}-${sessionDetail.session_id}.md`;
  downloadText(name, formatSessionMarkdownExport(sessionDetail), "text/markdown");
});

elements.sessionExportJson.addEventListener("click", () => {
  if (!sessionDetail) {
    return;
  }
  const name = `${sessionDetail.harness}-${sessionDetail.session_id}.json`;
  downloadText(name, formatSessionJsonExport(sessionDetail), "application/json");
});

window.addEventListener("popstate", () => {
  syncViewFromLocation();
});

const bootParams = parseSessionViewParams(new URLSearchParams(window.location.search));
if (bootParams) {
  void openSessionView(bootParams.harness, bootParams.sessionId, { push: false });
} else {
  showMetricsView();
}
void refreshDashboard(true);


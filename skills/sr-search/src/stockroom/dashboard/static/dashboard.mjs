import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsPanel,
  buildProjectsPanel,
  buildToolsPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  deriveOverviewCards,
  displayHarness,
  harnessColors,
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
};

const requestGate = createRequestGate();
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

function renderDashboard() {
  // Measured content is rendered after the state and request effects are wired.
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

renderHarnessControls();
void refreshDashboard(true);

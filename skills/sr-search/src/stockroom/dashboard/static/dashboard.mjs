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

// Browser effects are wired only after the core and data contracts are green.

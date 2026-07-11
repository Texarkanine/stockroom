const ENDPOINTS = [
  "overview",
  "trends",
  "projects",
  "tools",
  "models",
  "efficiency",
  "sessions",
  "wrapped",
];

function selectedKeys(harnesses) {
  const values =
    harnesses && typeof harnesses[Symbol.iterator] === "function" ? harnesses : [];
  return [...new Set([...values].filter((value) => typeof value === "string" && value.trim()))]
    .map((value) => value.trim())
    .sort((left, right) => left.localeCompare(right));
}

function safeText(value) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

/**
 * Error raised for a non-success dashboard API response.
 */
export class DashboardRequestError extends Error {
  /**
   * @param {string} message Sanitized API error.
   * @param {{action?: string, status?: number, endpoint?: string}} [details] Safe metadata.
   */
  constructor(message, details = {}) {
    super(message);
    this.name = "DashboardRequestError";
    this.action = details.action;
    this.status = details.status;
    this.endpoint = details.endpoint;
  }
}

/**
 * Normalize optional window bounds for request planning.
 *
 * @param {{since?: string, until?: string} | null | undefined} windowBounds
 * @returns {{since: string, until: string} | null}
 */
function normalizeWindowBounds(windowBounds) {
  if (!windowBounds || typeof windowBounds !== "object") {
    return null;
  }
  const since = safeText(windowBounds.since);
  const until = safeText(windowBounds.until);
  if (!since || !until) {
    return null;
  }
  return { since, until };
}

/**
 * Build the complete same-origin request plan for one selected harness set.
 *
 * @param {Iterable<string>} selectedHarnesses Selected harness keys.
 * @param {{since?: string, until?: string} | null} [windowBounds] Optional since/until window.
 * @returns {{name: string, url: string}[]} Ordered endpoint plan.
 */
export function buildRequestPlan(selectedHarnesses, windowBounds = null) {
  const filters = selectedKeys(selectedHarnesses)
    .map((harness) => `harness=${encodeURIComponent(harness)}`)
    .join("&");
  const bounds = normalizeWindowBounds(windowBounds);
  const windowParams = bounds
    ? [
        `since=${encodeURIComponent(bounds.since)}`,
        `until=${encodeURIComponent(bounds.until)}`,
      ].join("&")
    : "";
  return ENDPOINTS.map((name) => {
    if (name === "wrapped") {
      return { name, url: "/api/wrapped" };
    }
    const parameters = [filters, name === "sessions" ? "limit=50" : "", windowParams]
      .filter(Boolean)
      .join("&");
    return {
      name,
      url: `/api/${name}${parameters ? `?${parameters}` : ""}`,
    };
  });
}

/**
 * Fetch all dashboard endpoints in parallel and return one atomic snapshot.
 *
 * @param {typeof fetch} fetchImpl Injectable fetch implementation.
 * @param {Iterable<string>} selectedHarnesses Selected harness keys.
 * @param {{signal?: AbortSignal, window?: {since?: string, until?: string} | null}} [options] Request options.
 * @returns {Promise<Record<string, unknown>>} Complete named snapshot.
 */
export async function fetchSnapshot(fetchImpl, selectedHarnesses, options = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("fetchImpl must be a function");
  }
  const plan = buildRequestPlan(selectedHarnesses, options.window);
  const entries = await Promise.all(
    plan.map(async ({ name, url }) => {
      let response;
      try {
        response = await fetchImpl(url, { signal: options.signal });
      } catch (error) {
        if (error?.name === "AbortError") {
          throw error;
        }
        throw new DashboardRequestError("Dashboard request failed", { endpoint: name });
      }

      let payload;
      try {
        payload = await response.json();
      } catch {
        throw new DashboardRequestError(
          response.ok ? "Invalid dashboard response" : "Dashboard request failed",
          { endpoint: name, status: response.status },
        );
      }

      if (!response.ok) {
        const details = payload && typeof payload === "object" ? payload : {};
        throw new DashboardRequestError(
          safeText(details.error) ?? "Dashboard request failed",
          {
            action: safeText(details.action),
            endpoint: name,
            status: response.status,
          },
        );
      }
      return [name, payload];
    }),
  );
  return Object.fromEntries(entries);
}

/**
 * Fetch one session reconstruction payload.
 *
 * @param {typeof fetch} fetchImpl Injectable fetch implementation.
 * @param {string} harness Harness identity.
 * @param {string} sessionId Session identity.
 * @param {{signal?: AbortSignal}} [options] Request options.
 * @returns {Promise<object>} Session detail payload.
 */
export async function fetchSessionDetail(fetchImpl, harness, sessionId, options = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("fetchImpl must be a function");
  }
  const url =
    `/api/session?harness=${encodeURIComponent(harness)}` +
    `&session=${encodeURIComponent(sessionId)}`;
  let response;
  try {
    response = await fetchImpl(url, { signal: options.signal });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new DashboardRequestError("Dashboard request failed", { endpoint: "session" });
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new DashboardRequestError(
      response.ok ? "Invalid dashboard response" : "Dashboard request failed",
      { endpoint: "session", status: response.status },
    );
  }

  if (!response.ok) {
    const details = payload && typeof payload === "object" ? payload : {};
    throw new DashboardRequestError(
      safeText(details.error) ?? "Dashboard request failed",
      {
        action: safeText(details.action),
        endpoint: "session",
        status: response.status,
      },
    );
  }
  return payload;
}

/**
 * Create a generation/abort gate for overlapping dashboard refreshes.
 *
 * @returns {object} Request gate.
 */
export function createRequestGate() {
  let generation = 0;
  let controller = null;
  return {
    begin() {
      generation += 1;
      controller?.abort();
      controller = new AbortController();
      const token = generation;
      return {
        signal: controller.signal,
        isCurrent() {
          return token === generation;
        },
        commit(callback) {
          if (token !== generation) {
            return false;
          }
          callback();
          return true;
        },
      };
    },
  };
}

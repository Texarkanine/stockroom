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
 * Build the complete same-origin request plan for one selected harness set.
 *
 * @param {Iterable<string>} selectedHarnesses Selected harness keys.
 * @returns {{name: string, url: string}[]} Ordered endpoint plan.
 */
export function buildRequestPlan(selectedHarnesses) {
  throw new Error("not implemented");
}

/**
 * Fetch all dashboard endpoints in parallel and return one atomic snapshot.
 *
 * @param {typeof fetch} fetchImpl Injectable fetch implementation.
 * @param {Iterable<string>} selectedHarnesses Selected harness keys.
 * @param {{signal?: AbortSignal}} [options] Request options.
 * @returns {Promise<Record<string, unknown>>} Complete named snapshot.
 */
export async function fetchSnapshot(fetchImpl, selectedHarnesses, options = {}) {
  throw new Error("not implemented");
}

/**
 * Create a generation/abort gate for overlapping dashboard refreshes.
 *
 * @returns {object} Request gate.
 */
export function createRequestGate() {
  throw new Error("not implemented");
}

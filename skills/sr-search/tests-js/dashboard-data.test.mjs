import test from "node:test";
import assert from "node:assert/strict";

import {
  DashboardRequestError,
  buildRequestPlan,
  buildSessionsListRequestUrl,
  createRequestGate,
  fetchSessionsPage,
  fetchSnapshot,
} from "../src/stockroom/dashboard/static/dashboard-data.mjs";

const endpointNames = [
  "overview",
  "trends",
  "projects",
  "tools",
  "skills",
  "models",
  "model_trends",
  "efficiency",
  "sessions_ends",
  "wrapped",
];

function response(payload, options = {}) {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    async json() {
      if (options.jsonError) {
        throw new SyntaxError("bad JSON");
      }
      return payload;
    },
  };
}

test("builds ten same-origin request URLs with correct filtering", () => {
  const plan = buildRequestPlan(["cursor pro", "claude/cli"]);
  assert.deepEqual(plan.map((item) => item.name), endpointNames);
  assert.equal(
    plan.find((item) => item.name === "model_trends").url,
    "/api/model_trends?harness=claude%2Fcli&harness=cursor%20pro",
  );
  for (const item of plan.slice(0, -1)) {
    assert.match(item.url, /^\/api\//);
    assert.match(item.url, /harness=claude%2Fcli&harness=cursor%20pro/);
  }
  assert.equal(
    plan.find((item) => item.name === "sessions_ends").url,
    "/api/sessions_ends?harness=claude%2Fcli&harness=cursor%20pro",
  );
  assert.doesNotMatch(
    plan.find((item) => item.name === "sessions_ends").url,
    /limit=/,
  );
  assert.equal(plan.at(-1).url, "/api/wrapped");
});

test("fetchSessionsPage requests the list URL and returns the envelope", async () => {
  const urls = [];
  const payload = { total: 2, sessions: [{ session_id: "a" }] };
  const result = await fetchSessionsPage(
    async (url) => {
      urls.push(url);
      return response(payload);
    },
    { harnesses: ["cursor"], page: 2, perPage: 25 },
  );
  assert.equal(urls[0], "/api/sessions?harness=cursor&limit=25&offset=25&order=desc");
  assert.deepEqual(result, payload);
});

test("buildSessionsListRequestUrl maps page/per_page to offset/limit and show-all", () => {
  assert.equal(
    buildSessionsListRequestUrl({
      harnesses: ["cursor"],
      page: 1,
      perPage: 50,
    }),
    "/api/sessions?harness=cursor&limit=50&offset=0&order=desc",
  );
  assert.equal(
    buildSessionsListRequestUrl({
      harnesses: ["claude/cli"],
      since: "2026-01-01T00:00:00Z",
      until: "2026-02-01T00:00:00Z",
      page: 3,
      perPage: 25,
    }),
    "/api/sessions?harness=claude%2Fcli&limit=25&offset=50&order=desc" +
      "&since=2026-01-01T00%3A00%3A00Z&until=2026-02-01T00%3A00%3A00Z",
  );
  assert.equal(
    buildSessionsListRequestUrl({
      harnesses: [],
      page: 1,
      perPage: "all",
    }),
    "/api/sessions?limit=0&offset=0&order=desc",
  );
});

test("fetches and names one complete parallel snapshot", async () => {
  const pending = [];
  const fetchImpl = (url) =>
    new Promise((resolve) => {
      pending.push({ url, resolve });
    });
  const snapshotPromise = fetchSnapshot(fetchImpl, ["cursor"]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(pending.length, 10);
  assert.deepEqual(
    pending.map((item) => item.url.split("?")[0]),
    endpointNames.map((name) => `/api/${name}`),
  );
  pending.reverse().forEach((item, index) => {
    item.resolve(response({ url: item.url, completion: index }));
  });
  const snapshot = await snapshotPromise;
  assert.deepEqual(Object.keys(snapshot), endpointNames);
  assert.match(snapshot.overview.url, /\/api\/overview/);
  assert.match(snapshot.wrapped.url, /\/api\/wrapped/);
});

test("rejects atomically with sanitized actionable API errors", async () => {
  const fetchImpl = async (url) => {
    if (url.startsWith("/api/tools")) {
      return response(
        {
          error: "warehouse schema is behind",
          action: "run `stockroom migrate`",
          private: "must not escape",
        },
        { ok: false, status: 503 },
      );
    }
    return response({ partial: url });
  };
  await assert.rejects(
    fetchSnapshot(fetchImpl, ["cursor"]),
    (error) => {
      assert.ok(error instanceof DashboardRequestError);
      assert.equal(error.message, "warehouse schema is behind");
      assert.equal(error.action, "run `stockroom migrate`");
      assert.equal(error.status, 503);
      assert.equal(error.endpoint, "tools");
      assert.doesNotMatch(String(error), /private|must not escape/);
      return true;
    },
  );
  await assert.rejects(
    fetchSnapshot(
      async () =>
        response("<html>private proxy failure</html>", {
          ok: false,
          status: 500,
        }),
      ["cursor"],
    ),
    (error) => {
      assert.equal(error.message, "Dashboard request failed");
      assert.doesNotMatch(String(error), /private proxy/);
      return true;
    },
  );
});

test("forwards abort signals to every request", async () => {
  const controller = new AbortController();
  const signals = [];
  await fetchSnapshot(
    async (_url, options) => {
      signals.push(options.signal);
      return response({});
    },
    ["cursor"],
    { signal: controller.signal },
  );
  assert.equal(signals.length, 10);
  assert.ok(signals.every((signal) => signal === controller.signal));
});

test("allows only the latest request generation to commit", () => {
  const gate = createRequestGate();
  const committed = [];
  const first = gate.begin();
  const second = gate.begin();
  assert.equal(first.signal.aborted, true);
  assert.equal(second.signal.aborted, false);
  assert.equal(first.commit(() => committed.push("first")), false);
  assert.equal(second.commit(() => committed.push("second")), true);
  assert.deepEqual(committed, ["second"]);
  assert.equal(first.isCurrent(), false);
  assert.equal(second.isCurrent(), true);
});

test("null or omitted window bounds match today's unwindowed URLs", () => {
  const baseline = buildRequestPlan(["cursor"]);
  assert.deepEqual(buildRequestPlan(["cursor"], null), baseline);
  assert.deepEqual(buildRequestPlan(["cursor"], undefined), baseline);
  assert.deepEqual(buildRequestPlan(["cursor"], {}), baseline);
});

test("window bounds append encoded since and until to all endpoints except wrapped", () => {
  const since = "2026-01-01T00:00:00+00:00";
  const until = "2026-01-08T12:30:00+00:00";
  const plan = buildRequestPlan(["cursor pro"], { since, until });
  const encodedSince = encodeURIComponent(since);
  const encodedUntil = encodeURIComponent(until);
  for (const item of plan) {
    if (item.name === "wrapped") {
      assert.equal(item.url, "/api/wrapped");
      assert.doesNotMatch(item.url, /since=|until=/);
      continue;
    }
    assert.match(item.url, new RegExp(`since=${encodedSince}`));
    assert.match(item.url, new RegExp(`until=${encodedUntil}`));
    assert.match(item.url, /harness=cursor%20pro/);
  }
  assert.equal(
    plan.find((item) => item.name === "sessions_ends").url,
    `/api/sessions_ends?harness=cursor%20pro&since=${encodedSince}&until=${encodedUntil}`,
  );
});

test("fetchSnapshot forwards options.window into every non-wrapped pending URL", async () => {
  const since = "2026-06-01T00:00:00Z";
  const until = "2026-07-01T00:00:00Z";
  const pending = [];
  const fetchImpl = (url) =>
    new Promise((resolve) => {
      pending.push({ url, resolve });
    });
  const snapshotPromise = fetchSnapshot(fetchImpl, ["cursor"], {
    window: { since, until },
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(pending.length, 10);
  const encodedSince = encodeURIComponent(since);
  const encodedUntil = encodeURIComponent(until);
  for (const item of pending) {
    if (item.url.startsWith("/api/wrapped")) {
      assert.equal(item.url, "/api/wrapped");
      assert.doesNotMatch(item.url, /since=|until=/);
      continue;
    }
    assert.match(item.url, new RegExp(`since=${encodedSince}`));
    assert.match(item.url, new RegExp(`until=${encodedUntil}`));
  }
  pending.forEach((item) => item.resolve(response({ ok: true })));
  await snapshotPromise;
});

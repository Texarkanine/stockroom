import test from "node:test";
import assert from "node:assert/strict";

import {
  ansiToHtml,
  buildSessionDeepLink,
  buildSessionViewSearchParams,
  buildSessionsListSearchParams,
  clampSessionsListPage,
  documentTitleForView,
  formatSessionJsonExport,
  formatSessionMarkdownExport,
  isActiveSessionView,
  normalizePerPage,
  parseSessionViewParams,
  parseSessionsListParams,
  perPageToLimit,
  renderSessionMessageHtml,
} from "../src/stockroom/dashboard/static/dashboard-session.mjs";

test("buildSessionViewSearchParams encodes the canonical session view", () => {
  const params = buildSessionViewSearchParams("cursor", "abc/def+1");
  assert.equal(params.get("view"), "session");
  assert.equal(params.get("harness"), "cursor");
  assert.equal(params.get("session"), "abc/def+1");
  assert.equal(
    params.toString(),
    "view=session&harness=cursor&session=abc%2Fdef%2B1",
  );
});

test("parseSessionViewParams requires view=session plus both ids", () => {
  assert.deepEqual(
    parseSessionViewParams(
      new URLSearchParams("view=session&harness=claude&session=s1"),
    ),
    { harness: "claude", sessionId: "s1" },
  );
  assert.equal(
    parseSessionViewParams(new URLSearchParams("harness=claude&session=s1")),
    null,
  );
  assert.equal(
    parseSessionViewParams(new URLSearchParams("view=session&harness=claude")),
    null,
  );
  assert.equal(
    parseSessionViewParams(new URLSearchParams("view=session&session=s1")),
    null,
  );
  assert.equal(parseSessionViewParams(new URLSearchParams("")), null);
});

test("buildSessionDeepLink appends encoded query to a base URL", () => {
  assert.equal(
    buildSessionDeepLink("http://127.0.0.1:58008/", "cursor", "s1"),
    "http://127.0.0.1:58008/?view=session&harness=cursor&session=s1",
  );
  assert.equal(
    buildSessionDeepLink("http://127.0.0.1:58008", "cursor", "a/b"),
    "http://127.0.0.1:58008/?view=session&harness=cursor&session=a%2Fb",
  );
});

test("formatSessionMarkdownExport builds title, turns, and fenced tools", () => {
  const markdown = formatSessionMarkdownExport({
    harness: "cursor",
    session_id: "s1",
    project_name: "stockroom",
    project_id: "p1",
    messages: [
      {
        role: "user",
        text: "hello **world**",
        tool_calls: [],
      },
      {
        role: "assistant",
        text: "ok",
        tool_calls: [
          { tool_name: "Read", tool_input: { path: "a.py" } },
          { tool_name: "Shell", tool_input: { command: "ls" } },
        ],
      },
    ],
  });
  assert.match(markdown, /^# cursor \/ s1/);
  assert.match(markdown, /project: stockroom/);
  assert.match(markdown, /## user\n\nhello \*\*world\*\*/);
  assert.match(markdown, /## assistant\n\nok/);
  assert.match(markdown, /### Read\n\n```json\n\{\n {2}"path": "a\.py"\n\}\n```/);
  assert.match(markdown, /### Shell\n\n```json\n\{\n {2}"command": "ls"\n\}\n```/);
});

test("formatSessionJsonExport pretty-prints the detail payload identity", () => {
  const detail = {
    harness: "claude",
    session_id: "x",
    messages: [{ role: "user", text: "hi", tool_calls: [] }],
  };
  assert.equal(formatSessionJsonExport(detail), `${JSON.stringify(detail, null, 2)}\n`);
});

test("ansiToHtml renders bold SGR and escapes HTML", () => {
  const input =
    "<local-command-stdout>Set model to \u001b[1mSonnet 5\u001b[22m and saved</local-command-stdout>";
  const html = ansiToHtml(input);
  assert.match(html, /&lt;local-command-stdout&gt;/);
  assert.match(html, /<strong>Sonnet 5<\/strong>/);
  assert.doesNotMatch(html, /\u001b/);
  assert.doesNotMatch(html, /\[1m/);
});

test("ansiToHtml supports colors reset and newlines", () => {
  const html = ansiToHtml("plain\u001b[31mred\u001b[0m\nok");
  assert.match(html, /style="color:#c00"/);
  assert.match(html, /red/);
  assert.match(html, /<br>/);
  assert.match(html, /ok$/);
});

test("renderSessionMessageHtml uses ANSI path when CSI present else markdown", () => {
  const md = (text) => `<p>${text}</p>`;
  assert.equal(
    renderSessionMessageHtml("hello **x**", md),
    "<p>hello **x**</p>",
  );
  const ansiHtml = renderSessionMessageHtml("a\u001b[1mb\u001b[0m", md);
  assert.match(ansiHtml, /<strong>b<\/strong>/);
  assert.doesNotMatch(ansiHtml, /<p>/);
});

test("isActiveSessionView requires matching harness and session id", () => {
  assert.equal(isActiveSessionView({ harness: "c", sessionId: "1" }, "c", "1"), true);
  assert.equal(isActiveSessionView({ harness: "c", sessionId: "1" }, "c", "2"), false);
  assert.equal(isActiveSessionView(null, "c", "1"), false);
});

test("documentTitleForView names metrics, conversations list, and conversation", () => {
  assert.equal(documentTitleForView("metrics"), "stockroom dashboard");
  assert.equal(documentTitleForView("sessions"), "stockroom conversations");
  assert.equal(documentTitleForView("session"), "stockroom conversation");
  assert.equal(documentTitleForView("nope"), "stockroom dashboard");
});

test("normalizePerPage accepts presets and defaults invalid values to 50", () => {
  assert.equal(normalizePerPage("25"), 25);
  assert.equal(normalizePerPage("50"), 50);
  assert.equal(normalizePerPage("100"), 100);
  assert.equal(normalizePerPage("all"), "all");
  assert.equal(normalizePerPage(null), 50);
  assert.equal(normalizePerPage("40"), 50);
  assert.equal(normalizePerPage(""), 50);
});

test("perPageToLimit maps all to 0 and numeric presets to themselves", () => {
  assert.equal(perPageToLimit("all"), 0);
  assert.equal(perPageToLimit(25), 25);
  assert.equal(perPageToLimit(50), 50);
  assert.equal(perPageToLimit(100), 100);
});

test("parseSessionsListParams reads view=sessions filters with defaults", () => {
  assert.equal(parseSessionsListParams(new URLSearchParams("")), null);
  assert.equal(
    parseSessionsListParams(new URLSearchParams("view=session&harness=c&session=s")),
    null,
  );
  assert.deepEqual(
    parseSessionsListParams(
      new URLSearchParams(
        "view=sessions&harness=cursor&harness=claude&since=2026-01-01T00:00:00Z&until=2026-02-01T00:00:00Z&page=3&per_page=25",
      ),
    ),
    {
      harnesses: ["cursor", "claude"],
      since: "2026-01-01T00:00:00Z",
      until: "2026-02-01T00:00:00Z",
      page: 3,
      perPage: 25,
    },
  );
  assert.deepEqual(
    parseSessionsListParams(new URLSearchParams("view=sessions&per_page=all&page=nope")),
    {
      harnesses: [],
      since: null,
      until: null,
      page: 1,
      perPage: "all",
    },
  );
});

test("buildSessionsListSearchParams omits default page and default-range bounds", () => {
  const params = buildSessionsListSearchParams({
    harnesses: ["cursor", "claude/cli"],
    since: null,
    until: null,
    page: 1,
    perPage: 50,
  });
  assert.equal(params.get("view"), "sessions");
  assert.deepEqual(params.getAll("harness"), ["cursor", "claude/cli"]);
  assert.equal(params.get("since"), null);
  assert.equal(params.get("until"), null);
  assert.equal(params.get("page"), null);
  assert.equal(params.get("per_page"), "50");

  const paged = buildSessionsListSearchParams({
    harnesses: ["cursor"],
    since: "2026-01-01T00:00:00Z",
    until: "2026-02-01T00:00:00Z",
    page: 2,
    perPage: "all",
  });
  assert.equal(paged.get("page"), "2");
  assert.equal(paged.get("per_page"), "all");
  assert.equal(paged.get("since"), "2026-01-01T00:00:00Z");
  assert.equal(paged.get("until"), "2026-02-01T00:00:00Z");
});

test("clampSessionsListPage clamps beyond last non-empty page", () => {
  assert.equal(clampSessionsListPage(1, 0, 50), 1);
  assert.equal(clampSessionsListPage(99, 0, 50), 1);
  assert.equal(clampSessionsListPage(3, 100, 50), 2);
  assert.equal(clampSessionsListPage(1, 100, 50), 1);
  assert.equal(clampSessionsListPage(2, 100, "all"), 1);
});

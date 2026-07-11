import test from "node:test";
import assert from "node:assert/strict";

import {
  ansiToHtml,
  buildSessionDeepLink,
  buildSessionViewSearchParams,
  formatSessionJsonExport,
  formatSessionMarkdownExport,
  isActiveSessionView,
  parseSessionViewParams,
  renderSessionMessageHtml,
  shouldUseHistoryBackForSessionClose,
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

test("shouldUseHistoryBackForSessionClose only when history state is session", () => {
  assert.equal(shouldUseHistoryBackForSessionClose({ view: "session" }), true);
  assert.equal(shouldUseHistoryBackForSessionClose({ view: "metrics" }), false);
  assert.equal(shouldUseHistoryBackForSessionClose(null), false);
});

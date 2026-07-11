import test from "node:test";
import assert from "node:assert/strict";

import {
  buildSessionDeepLink,
  buildSessionViewSearchParams,
  formatSessionJsonExport,
  formatSessionMarkdownExport,
  parseSessionViewParams,
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

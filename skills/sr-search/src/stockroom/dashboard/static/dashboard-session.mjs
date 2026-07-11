/**
 * Pure helpers for dashboard session inspection (URL + export).
 *
 * No DOM. Richer markdown rendering belongs in export / external tools —
 * do not add markdown-it plugins here.
 */

/**
 * @param {string} harness
 * @param {string} sessionId
 * @returns {URLSearchParams}
 */
export function buildSessionViewSearchParams(harness, sessionId) {
  const params = new URLSearchParams();
  params.set("view", "session");
  params.set("harness", harness);
  params.set("session", sessionId);
  return params;
}

/**
 * @param {URLSearchParams} searchParams
 * @returns {{ harness: string, sessionId: string } | null}
 */
export function parseSessionViewParams(searchParams) {
  if (searchParams.get("view") !== "session") {
    return null;
  }
  const harness = searchParams.get("harness");
  const sessionId = searchParams.get("session");
  if (!harness || !sessionId) {
    return null;
  }
  return { harness, sessionId };
}

/**
 * @param {string} baseUrl
 * @param {string} harness
 * @param {string} sessionId
 * @returns {string}
 */
export function buildSessionDeepLink(baseUrl, harness, sessionId) {
  const url = new URL(baseUrl, "http://127.0.0.1");
  url.search = "";
  url.hash = "";
  const params = buildSessionViewSearchParams(harness, sessionId);
  return `${url.origin}${url.pathname}?${params.toString()}`;
}

/**
 * @param {object} detail
 * @returns {string}
 */
export function formatSessionMarkdownExport(detail) {
  const harness = detail?.harness ?? "";
  const sessionId = detail?.session_id ?? "";
  const project =
    detail?.project_name || detail?.project_id || "—";
  const lines = [
    `# ${harness} / ${sessionId}`,
    "",
    `project: ${project}`,
    "",
  ];
  for (const message of detail?.messages ?? []) {
    lines.push(`## ${message.role ?? "unknown"}`, "", message.text ?? "", "");
    for (const tool of message.tool_calls ?? []) {
      lines.push(
        `### ${tool.tool_name ?? "tool"}`,
        "",
        "```json",
        JSON.stringify(tool.tool_input ?? {}, null, 2),
        "```",
        "",
      );
    }
  }
  return `${lines.join("\n").trimEnd()}\n`;
}

/**
 * @param {object} detail
 * @returns {string}
 */
export function formatSessionJsonExport(detail) {
  return `${JSON.stringify(detail, null, 2)}\n`;
}

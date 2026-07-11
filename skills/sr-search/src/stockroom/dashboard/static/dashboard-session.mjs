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

const ANSI_CSI_SGR = /\u001b\[([0-9;]*)m/g;
const ANSI_CSI_OTHER = /\u001b\[[0-9;?]*[A-Za-z]/g;
const ANSI_OSC = /\u001b\][^\u0007]*(?:\u0007|\u001b\\)/g;

const ANSI_FG = {
  30: "#000",
  31: "#c00",
  32: "#0a0",
  33: "#a80",
  34: "#00c",
  35: "#a0a",
  36: "#0aa",
  37: "#aaa",
  90: "#555",
  91: "#f55",
  92: "#5f5",
  93: "#ff5",
  94: "#55f",
  95: "#f5f",
  96: "#5ff",
  97: "#fff",
};

const ANSI_BG = {
  40: "#000",
  41: "#c00",
  42: "#0a0",
  43: "#a80",
  44: "#00c",
  45: "#a0a",
  46: "#0aa",
  47: "#aaa",
  100: "#555",
  101: "#f55",
  102: "#5f5",
  103: "#ff5",
  104: "#55f",
  105: "#f5f",
  106: "#5ff",
  107: "#fff",
};

/**
 * @param {string} value
 * @returns {string}
 */
function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * @param {string} text
 * @param {{bold: boolean, italic: boolean, underline: boolean, fg: string | null, bg: string | null}} state
 * @returns {string}
 */
function wrapAnsiSegment(text, state) {
  if (!text) {
    return "";
  }
  let html = escapeHtml(text).replaceAll("\n", "<br>");
  if (state.bold) {
    html = `<strong>${html}</strong>`;
  }
  if (state.italic) {
    html = `<em>${html}</em>`;
  }
  if (state.underline) {
    html = `<u>${html}</u>`;
  }
  const styles = [];
  if (state.fg) {
    styles.push(`color:${state.fg}`);
  }
  if (state.bg) {
    styles.push(`background-color:${state.bg}`);
  }
  if (styles.length > 0) {
    html = `<span style="${styles.join(";")}">${html}</span>`;
  }
  return html;
}

/**
 * Convert a text blob with ANSI SGR escapes into safe HTML.
 *
 * Supports bold/italic/underline, basic 16-color fg/bg, and reset. Unknown CSI
 * / OSC sequences are stripped. No external dependency.
 *
 * @param {string} text
 * @returns {string}
 */
export function ansiToHtml(text) {
  const source = String(text ?? "")
    .replace(ANSI_OSC, "")
    .replace(ANSI_CSI_OTHER, (match) => (match.endsWith("m") ? match : ""));
  const state = {
    bold: false,
    italic: false,
    underline: false,
    fg: null,
    bg: null,
  };
  let html = "";
  let lastIndex = 0;
  ANSI_CSI_SGR.lastIndex = 0;
  for (const match of source.matchAll(ANSI_CSI_SGR)) {
    html += wrapAnsiSegment(source.slice(lastIndex, match.index), state);
    const codes = match[1] === "" ? ["0"] : match[1].split(";");
    for (const raw of codes) {
      const code = Number.parseInt(raw || "0", 10);
      if (code === 0) {
        state.bold = false;
        state.italic = false;
        state.underline = false;
        state.fg = null;
        state.bg = null;
      } else if (code === 1) {
        state.bold = true;
      } else if (code === 3) {
        state.italic = true;
      } else if (code === 4) {
        state.underline = true;
      } else if (code === 22) {
        state.bold = false;
      } else if (code === 23) {
        state.italic = false;
      } else if (code === 24) {
        state.underline = false;
      } else if (code === 39) {
        state.fg = null;
      } else if (code === 49) {
        state.bg = null;
      } else if (ANSI_FG[code]) {
        state.fg = ANSI_FG[code];
      } else if (ANSI_BG[code]) {
        state.bg = ANSI_BG[code];
      }
    }
    lastIndex = match.index + match[0].length;
  }
  html += wrapAnsiSegment(source.slice(lastIndex), state);
  return html;
}

/**
 * Choose markdown rendering or ANSI→HTML for a session message body.
 *
 * @param {string} text
 * @param {(value: string) => string} markdownRender
 * @returns {string}
 */
export function renderSessionMessageHtml(text, markdownRender) {
  const value = text ?? "";
  if (/\u001b\[/.test(value)) {
    return ansiToHtml(value);
  }
  return markdownRender(value);
}

/**
 * True when ``sessionView`` still addresses the given identity.
 *
 * @param {{harness: string, sessionId: string} | null | undefined} sessionView
 * @param {string} harness
 * @param {string} sessionId
 * @returns {boolean}
 */
export function isActiveSessionView(sessionView, harness, sessionId) {
  return (
    !!sessionView &&
    sessionView.harness === harness &&
    sessionView.sessionId === sessionId
  );
}

/**
 * Whether closing the session pane should call ``history.back()``.
 *
 * Only when the current history entry was pushed as a session view (click-through).
 * Deep-link boots never push, so Back should ``replaceState`` instead.
 *
 * @param {{view?: string} | null | undefined} historyState
 * @returns {boolean}
 */
export function shouldUseHistoryBackForSessionClose(historyState) {
  return historyState?.view === "session";
}

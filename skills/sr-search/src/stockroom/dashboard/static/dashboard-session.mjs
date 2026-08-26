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
 * Whether boot should fan out the metrics snapshot (``fetchSnapshot``).
 *
 * Conversation deep-links only need ``/api/session``. Metrics home and the
 * sessions list still refresh metrics (list harness controls discover from
 * overview).
 *
 * @param {URLSearchParams} searchParams
 * @returns {boolean}
 */
export function shouldRefreshMetricsOnBoot(searchParams) {
  return parseSessionViewParams(searchParams) === null;
}

/**
 * Document / heading title for a dashboard SPA view.
 *
 * @param {"metrics" | "sessions" | "session" | string} view
 * @returns {string}
 */
export function documentTitleForView(view) {
  if (view === "sessions") {
    return "stockroom conversations";
  }
  if (view === "session") {
    return "stockroom conversation";
  }
  return "stockroom dashboard";
}

/**
 * DOM id / hash fragment (without ``#``) for a message ordinal.
 *
 * @param {unknown} ordinal Message ordinal from session detail.
 * @returns {string | null}
 */
export function messageAnchorId(ordinal) {
  const n = Number(ordinal);
  if (!Number.isInteger(n) || n < 0) {
    return null;
  }
  return `msg-${n}`;
}

/**
 * Parse ``#msg-N`` from a location hash; null when malformed.
 *
 * @param {unknown} hash ``location.hash`` or equivalent.
 * @returns {number | null}
 */
export function parseMessageHash(hash) {
  const match = String(hash ?? "").match(/^#msg-(\d+)$/);
  return match ? Number(match[1]) : null;
}

/**
 * DOM id / hash fragment (without ``#``) for a spawn pill.
 *
 * @param {unknown} ordinal Launch message ordinal.
 * @param {unknown} spawnIndex 1-based index among children of that turn.
 * @returns {string | null}
 */
export function subagentAnchorId(ordinal, spawnIndex) {
  const n = Number(ordinal);
  const m = Number(spawnIndex);
  if (!Number.isInteger(n) || n < 0 || !Number.isInteger(m) || m < 1) {
    return null;
  }
  return `msg-${n}-sa-${m}`;
}

/**
 * Parse ``#msg-N-sa-M`` from a location hash; null when malformed.
 * ``M`` must be an integer ``>= 1``. Ordinal ``0`` is valid.
 *
 * @param {unknown} hash
 * @returns {{ ordinal: number, spawnIndex: number } | null}
 */
export function parseSubagentHash(hash) {
  const match = String(hash ?? "").match(/^#msg-(\d+)-sa-(\d+)$/);
  if (!match) {
    return null;
  }
  const spawnIndex = Number(match[2]);
  if (spawnIndex < 1) {
    return null;
  }
  return { ordinal: Number(match[1]), spawnIndex };
}

/**
 * Accept ``#msg-N`` or ``#msg-N-sa-M``; null when neither matches.
 *
 * @param {unknown} hash
 * @returns {{ ordinal: number, spawnIndex?: number } | null}
 */
export function parseSessionFragment(hash) {
  const spawn = parseSubagentHash(hash);
  if (spawn) {
    return spawn;
  }
  const ordinal = parseMessageHash(hash);
  return ordinal === null ? null : { ordinal };
}

/**
 * Resolve a ``#msg-N`` or ``#msg-N-sa-M`` element under ``root``.
 *
 * @param {{ querySelector: (selector: string) => Element | null } | null | undefined} root
 * @param {unknown} hash
 * @returns {Element | null}
 */
export function resolveMessageAnchorElement(root, hash) {
  const fragment = parseSessionFragment(hash);
  if (fragment === null || root == null) {
    return null;
  }
  const id =
    fragment.spawnIndex == null
      ? messageAnchorId(fragment.ordinal)
      : subagentAnchorId(fragment.ordinal, fragment.spawnIndex);
  return id ? root.querySelector(`#${id}`) : null;
}

/**
 * @param {string} baseUrl
 * @param {string} harness
 * @param {string} sessionId
 * @param {{ ordinal?: number, spawnIndex?: number } | undefined} [options]
 * @returns {string}
 */
export function buildSessionDeepLink(baseUrl, harness, sessionId, options) {
  const url = new URL(baseUrl, "http://127.0.0.1");
  url.search = "";
  url.hash = "";
  const params = buildSessionViewSearchParams(harness, sessionId);
  const spawn = subagentAnchorId(options?.ordinal, options?.spawnIndex);
  const anchor = spawn ?? messageAnchorId(options?.ordinal);
  if (anchor) {
    url.hash = anchor;
  }
  return `${url.origin}${url.pathname}?${params.toString()}${url.hash}`;
}

/**
 * Parent-line href: spawn hash when ``parentSpawn`` is present, else the parent session.
 *
 * @param {string} baseUrl
 * @param {string} harness
 * @param {string} parentSessionId
 * @param {{ session_id?: string, message_ordinal?: number, spawn_index?: number } | null | undefined} parentSpawn
 * @returns {string}
 */
export function buildParentLineHref(baseUrl, harness, parentSessionId, parentSpawn) {
  if (parentSpawn && parentSpawn.spawn_index != null) {
    return buildSessionDeepLink(baseUrl, harness, parentSessionId, {
      ordinal: parentSpawn.message_ordinal,
      spawnIndex: parentSpawn.spawn_index,
    });
  }
  return buildSessionDeepLink(baseUrl, harness, parentSessionId);
}

/** @typedef {25 | 50 | 100 | "all"} PerPage */

const PER_PAGE_PRESETS = new Set(["25", "50", "100", "all"]);

/**
 * Normalize a ``per_page`` URL token to a preset; invalid → 50.
 *
 * @param {string | null | undefined} raw
 * @returns {PerPage}
 */
export function normalizePerPage(raw) {
  if (raw == null || raw === "") {
    return 50;
  }
  const token = String(raw).toLowerCase();
  if (!PER_PAGE_PRESETS.has(token)) {
    return 50;
  }
  return token === "all" ? "all" : Number(token);
}

/**
 * Map a per-page preset to the sessions API ``limit`` (0 = show-all).
 *
 * @param {PerPage} perPage
 * @returns {number}
 */
export function perPageToLimit(perPage) {
  return perPage === "all" ? 0 : perPage;
}

/**
 * Clamp ``page`` to the last non-empty page (or 1 when total is 0 / show-all).
 *
 * @param {number} page
 * @param {number} total
 * @param {PerPage} perPage
 * @returns {number}
 */
export function clampSessionsListPage(page, total, perPage) {
  const requested = Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1;
  if (perPage === "all" || total <= 0) {
    return 1;
  }
  const lastPage = Math.max(1, Math.ceil(total / perPage));
  return Math.min(requested, lastPage);
}

/**
 * @typedef {{
 *   harnesses: string[],
 *   since: string | null,
 *   until: string | null,
 *   page: number,
 *   perPage: PerPage,
 * }} SessionsListParams
 */

/**
 * Parse ``view=sessions`` list URL params; null when not the list view.
 *
 * @param {URLSearchParams} searchParams
 * @returns {SessionsListParams | null}
 */
export function parseSessionsListParams(searchParams) {
  if (searchParams.get("view") !== "sessions") {
    return null;
  }
  const harnesses = searchParams.getAll("harness").filter(Boolean);
  const since = searchParams.get("since") || null;
  const until = searchParams.get("until") || null;
  const rawPage = Number.parseInt(searchParams.get("page") ?? "1", 10);
  const page = Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1;
  const perPage = normalizePerPage(searchParams.get("per_page"));
  return { harnesses, since, until, page, perPage };
}

/**
 * Build query params for the sessions-list SPA view.
 *
 * Omits ``page`` when 1; omits since/until when null (default/unwindowed range).
 *
 * @param {SessionsListParams} params
 * @returns {URLSearchParams}
 */
export function buildSessionsListSearchParams(params) {
  const out = new URLSearchParams();
  out.set("view", "sessions");
  for (const harness of params.harnesses ?? []) {
    if (harness) {
      out.append("harness", harness);
    }
  }
  if (params.since) {
    out.set("since", params.since);
  }
  if (params.until) {
    out.set("until", params.until);
  }
  const perPage = normalizePerPage(
    params.perPage === "all" ? "all" : String(params.perPage ?? 50),
  );
  out.set("per_page", String(perPage));
  const page = Number.isFinite(params.page) && params.page > 1 ? Math.floor(params.page) : 1;
  if (page > 1) {
    out.set("page", String(page));
  }
  return out;
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
  const heading = sessionMessagesHeading({
    title: detail?.title,
    harnessLabel: harness,
    sessionId,
  });
  const lines = [
    `# ${heading}`,
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
 * True when the requested session is already loaded in memory (no refetch).
 *
 * @param {{harness: string, sessionId: string} | null | undefined} sessionView
 * @param {{harness?: string, session_id?: string} | null | undefined} sessionDetail
 * @param {string} harness
 * @param {string} sessionId
 * @returns {boolean}
 */
export function canReuseLoadedSession(sessionView, sessionDetail, harness, sessionId) {
  return (
    isActiveSessionView(sessionView, harness, sessionId) &&
    !!sessionDetail &&
    sessionDetail.harness === harness &&
    sessionDetail.session_id === sessionId
  );
}

/**
 * Build a same-document location preserving path/query and setting ``#msg-N``.
 *
 * @param {string} pathname
 * @param {string | URLSearchParams} search Query string (leading ``?`` optional).
 * @param {unknown} ordinal
 * @returns {string}
 */
export function sessionLocationWithMessageHash(pathname, search, ordinal) {
  const params =
    search instanceof URLSearchParams ? search : new URLSearchParams(search);
  const query = params.toString();
  const base = query ? `${pathname}?${query}` : pathname;
  const anchor = messageAnchorId(ordinal);
  return anchor ? `${base}#${anchor}` : base;
}

/**
 * Overview-pill meta for session view (F-a): harness, model, tokens, started.
 *
 * @param {{
 *   harnessLabel: string,
 *   started: string,
 *   model?: string | null,
 *   tokens?: unknown,
 * }} fields
 * @returns {Array<{ kind: "text", label: string, text: string } | { kind: "tokens", label: string, tokens: unknown }>}
 */
export function buildSessionMetaEntries(fields) {
  return [
    { kind: "text", label: "Harness", text: fields.harnessLabel },
    { kind: "text", label: "Model", text: fields.model || "—" },
    { kind: "tokens", label: "Tokens", tokens: fields.tokens ?? null },
    { kind: "text", label: "Started", text: fields.started },
  ];
}

/**
 * Messages-pill heading: warehouse title when present, else harness / session id.
 *
 * @param {{ title?: string | null, harnessLabel: string, sessionId: string }} fields
 * @returns {string}
 */
export function sessionMessagesHeading(fields) {
  const title = typeof fields.title === "string" ? fields.title.trim() : "";
  if (title) {
    return title;
  }
  return `${fields.harnessLabel} / ${fields.sessionId}`;
}

/**
 * Flatten session messages into turn items with sibling subagent items after each launch turn.
 *
 * @param {object | null | undefined} detail
 * @param {{ baseUrl?: string } | undefined} [options]
 * @returns {Array<
 *   | { kind: "turn", ordinal: number, message: object }
 *   | { kind: "subagent", ordinal: number, spawnIndex: number, anchorId: string, href: string, roleLabel: string, ordinalLabel: string, label: string, sessionId: string }
 * >}
 */
export function sessionTranscriptItems(detail, options) {
  const baseUrl = options?.baseUrl ?? "";
  const harness = detail?.harness ?? "";
  const items = [];
  for (const message of detail?.messages ?? []) {
    items.push({ kind: "turn", ordinal: message.ordinal, message });
    for (const child of message.subagents ?? []) {
      const spawnIndex = child.spawn_index;
      const sessionId = child.session_id;
      const anchorId = subagentAnchorId(message.ordinal, spawnIndex);
      if (!anchorId || !sessionId) {
        continue;
      }
      items.push({
        kind: "subagent",
        ordinal: message.ordinal,
        spawnIndex,
        anchorId,
        href: buildSessionDeepLink(baseUrl, harness, sessionId),
        roleLabel: "sub-agent",
        ordinalLabel: `#${message.ordinal}-sa-${spawnIndex}`,
        label: child.label || "Subagent",
        sessionId,
      });
    }
  }
  return items;
}

/**
 * Parent-line model for a subagent view; null when the opened session is not a child.
 *
 * @param {object | null | undefined} detail
 * @param {{ baseUrl?: string } | undefined} [options]
 * @returns {{ href: string, sessionId: string } | null}
 */
export function sessionParentLine(detail, options) {
  if (!detail?.is_subagent || !detail.parent_session_id) {
    return null;
  }
  return {
    href: buildParentLineHref(
      options?.baseUrl ?? "",
      detail.harness ?? "",
      detail.parent_session_id,
      detail.parent_spawn,
    ),
    sessionId: detail.parent_session_id,
  };
}


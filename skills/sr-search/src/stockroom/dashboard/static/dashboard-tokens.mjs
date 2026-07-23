/** Compact token counts and shared hover breakdown for dashboard session UI. */

const EM_DASH = "—";

const BREAKDOWN_FIELDS = [
  { key: "input", label: "Input" },
  { key: "output", label: "Output" },
  { key: "cache_creation", label: "Cache write" },
  { key: "cache_read", label: "Cache read" },
];

/**
 * @param {unknown} tokens
 * @returns {tokens is {input: number, output: number, cache_creation: number, cache_read: number}}
 */
export function hasTokenData(tokens) {
  return tokens != null && typeof tokens === "object" && !Array.isArray(tokens);
}

/**
 * @param {unknown} tokens
 * @returns {number | null}
 */
export function tokenTotal(tokens) {
  if (!hasTokenData(tokens)) {
    return null;
  }
  return (
    Number(tokens.input || 0) +
    Number(tokens.output || 0) +
    Number(tokens.cache_creation || 0) +
    Number(tokens.cache_read || 0)
  );
}

/**
 * Cursor-style truncated big-counter (K / M / B).
 * @param {number} value
 * @returns {string}
 */
export function formatTokenCompact(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    return EM_DASH;
  }
  const abs = Math.abs(n);
  const units = [
    [1_000_000_000, "B"],
    [1_000_000, "M"],
    [1_000, "K"],
  ];
  for (const [div, suffix] of units) {
    if (abs >= div) {
      const scaled = n / div;
      const rounded = Math.round(scaled * 10) / 10;
      const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
      return `${text}${suffix}`;
    }
  }
  return String(Math.trunc(n));
}

/**
 * @param {unknown} tokens
 * @returns {{label: string, value: number}[]}
 */
export function tokenBreakdownRows(tokens) {
  if (!hasTokenData(tokens)) {
    return [];
  }
  return BREAKDOWN_FIELDS.map(({ key, label }) => ({
    label,
    value: Number(tokens[key] || 0),
  }));
}

/**
 * Rows plus summed total for the breakdown popover footer.
 *
 * @param {unknown} tokens
 * @returns {{ rows: {label: string, value: number}[], total: number } | null}
 */
export function tokenBreakdownModel(tokens) {
  if (!hasTokenData(tokens)) {
    return null;
  }
  return {
    rows: tokenBreakdownRows(tokens),
    total: tokenTotal(tokens) ?? 0,
  };
}

/**
 * @param {ParentNode} popover
 * @param {{label: string, value: number}} row
 * @param {string} [extraClass]
 */
function appendBreakdownRow(popover, row, extraClass) {
  const line = document.createElement("span");
  line.className = extraClass
    ? `token-breakdown-row ${extraClass}`
    : "token-breakdown-row";
  const name = document.createElement("span");
  name.className = "token-breakdown-label";
  name.textContent = row.label;
  const amount = document.createElement("span");
  amount.className = "token-breakdown-value";
  amount.textContent = formatTokenCompact(row.value);
  line.append(name, amount);
  popover.append(line);
}

/**
 * Mount compact token display into ``container``.
 *
 * When ``tokens`` is null/absent: emdash text only (no hover).
 * When present: compact total + ``?`` affordance with hover/focus breakdown.
 *
 * @param {ParentNode} container
 * @param {unknown} tokens
 * @param {{ labeled?: boolean }} [options]
 */
export function mountTokenDisplay(container, tokens, options = {}) {
  container.replaceChildren();
  if (!hasTokenData(tokens)) {
    if (options.labeled) {
      const label = document.createElement("strong");
      label.textContent = "Tokens: ";
      container.append(label, document.createTextNode(EM_DASH));
    } else {
      container.append(document.createTextNode(EM_DASH));
    }
    return;
  }

  const total = tokenTotal(tokens);
  const compact = formatTokenCompact(total ?? 0);
  const wrap = document.createElement("span");
  wrap.className = "token-display";
  wrap.tabIndex = 0;

  const value = document.createElement("span");
  value.className = "token-display-value";
  if (options.labeled) {
    const label = document.createElement("strong");
    label.textContent = "Tokens: ";
    value.append(label, document.createTextNode(compact));
  } else {
    value.textContent = compact;
  }

  const hint = document.createElement("span");
  hint.className = "token-display-hint";
  hint.setAttribute("aria-hidden", "true");
  hint.textContent = "?";

  const model = tokenBreakdownModel(tokens);
  const popover = document.createElement("span");
  popover.className = "token-breakdown";
  popover.setAttribute("role", "tooltip");
  for (const row of model?.rows ?? []) {
    appendBreakdownRow(popover, row);
  }
  const rule = document.createElement("hr");
  rule.className = "token-breakdown-rule";
  popover.append(rule);
  appendBreakdownRow(
    popover,
    { label: "Total", value: model?.total ?? 0 },
    "token-breakdown-total",
  );

  wrap.append(value, hint, popover);
  wrap.setAttribute(
    "aria-label",
    `Tokens ${compact}: ${(model?.rows ?? [])
      .map((row) => `${row.label} ${row.value}`)
      .join(", ")}, Total ${model?.total ?? 0}`,
  );
  container.append(wrap);
}

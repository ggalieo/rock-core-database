export async function api(path, opts = {}) {
  const options = { headers: { "Content-Type": "application/json" }, ...opts };
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

export async function post(path, body) {
  return api(path, { method: "POST", body: JSON.stringify(body) });
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function esc(v) {
  return String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export function fmt(n, d = 2) {
  if (n == null || n === "" || isNaN(Number(n))) return "—";
  return Number(n).toFixed(d);
}

export function fmtInt(n) {
  if (n == null || n === "" || isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-US");
}

export function shortDate(s) {
  if (!s) return "—";
  return String(s).replace(/:\d{2}$/, "").replace(/-/g, ".");
}

export function toast(msg, type = "info") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = "toast show " + (type === "error" ? "err" : type === "ok" ? "ok" : "");
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = "toast"; }, 2600);
}

export function go(hash) {
  if (location.hash === hash) return;
  location.hash = hash;
}

export function qsFromHash() {
  const raw = (location.hash || "").replace(/^#/, "");
  const [path, query = ""] = raw.split("?");
  return { path, params: new URLSearchParams(query) };
}

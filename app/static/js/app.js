import { qsFromHash, esc, toast } from "./api.js";
import * as pages from "./pages.js";
import { imageViewer } from "./viewer.js";

const view = () => document.getElementById("view");

const META = {
  home: ["总览", "CORE OPERATIONS"],
  map: ["井位导航", "WELL MAP"],
  wells: ["井档案", "WELL ARCHIVE"],
  search: ["影像检索", "IMAGE SEARCH"],
  inventory: ["库存管理", "INVENTORY"],
  stats: ["分析", "ANALYTICS"],
  admin: ["设置", "SETTINGS"],
  help: ["帮助", "HELP"],
  well: ["井档案", "WELL DOSSIER"],
  image: ["影像浏览", "IMAGE VIEWER"],
};

function setActive(key) {
  const navKey = key === "well" ? "wells" : key === "image" ? "search" : key;
  document.querySelectorAll("#railNav a, .rail-foot a").forEach((a) => {
    a.classList.toggle("active", a.dataset.nav === navKey);
  });
}

function setMeta(key) {
  const [title, sub] = META[key] || META.home;
  const t = document.getElementById("pageTitle");
  const s = document.getElementById("pageSub");
  if (t) t.textContent = title;
  if (s) s.textContent = sub;
}

async function route() {
  const { path } = qsFromHash();
  const clean = path.replace(/\/+$/, "") || "/home";
  const el = view();
  const modal = document.getElementById("modalRoot");
  if (modal) modal.innerHTML = "";
  let active = "home";
  try {
    if (clean === "/home" || clean === "/") { active = "home"; await pages.home(); }
    else if (clean === "/map") { active = "map"; await pages.mapPage(); }
    else if (clean === "/wells") { active = "wells"; await pages.wells(); }
    else if (clean.startsWith("/well/")) { active = "well"; await pages.well(parseInt(clean.split("/")[2], 10)); }
    else if (clean.startsWith("/image/")) { active = "image"; await imageViewer(parseInt(clean.split("/")[2], 10)); }
    else if (clean === "/search") { active = "search"; await pages.search(); }
    else if (clean === "/inventory") { active = "inventory"; await pages.inventory(); }
    else if (clean === "/stats") { active = "stats"; await pages.stats(); }
    else if (clean === "/admin") { active = "admin"; await pages.admin(); }
    else if (clean === "/help") { active = "help"; await pages.help(); }
    else { active = "home"; location.hash = "#/home"; return; }
  } catch (e) {
    console.error(e);
    el.innerHTML = `<div class="empty" style="margin-top:60px">
      <div style="font-size:16px;color:#dc4c64;margin-bottom:8px">页面加载失败</div>
      <div>${esc(e.message || e)}</div>
      <div style="margin-top:14px"><button class="btn" onclick="location.reload()">重新加载</button></div>
    </div>`;
  }
  setActive(active);
  setMeta(active);
  window.scrollTo(0, 0);
}

function clock() {
  const el = document.getElementById("clock");
  if (!el) return;
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  el.textContent = `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function bindSearch() {
  const form = document.getElementById("globalSearch");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = document.getElementById("globalQ").value.trim();
    if (!q) return;
    location.hash = `#/search?q=${encodeURIComponent(q)}`;
  });
}

function init() {
  clock();
  setInterval(clock, 1000 * 30);
  bindSearch();
  window.addEventListener("hashchange", route);
  if (!location.hash) location.hash = "#/home";
  route();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

window.coreDemo = { go: (h) => location.hash = h, toast };

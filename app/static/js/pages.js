import { api, esc, fmt, fmtInt, shortDate, toast, go, qsFromHash } from "./api.js";
import { barChart, donutChart } from "./charts.js";
import { renderChinaMap } from "./map.js";

const root = () => document.getElementById("view");

const loading = (text = "正在加载数据") =>
  `<div class="loading"><i></i>${text}…</div>`;

const empty = (text = "暂无数据") => `<div class="empty">${text}</div>`;

const IMAGE_TYPE_LABELS = {
  SURFACE: "外表皮", ROLLED: "展开图", FLUORESCENCE: "荧光", BOX: "岩心箱", THIN_SECTION: "薄片",
};
const imageTypeLabel = (t) => IMAGE_TYPE_LABELS[t] || t || "—";

function productCell(status) {
  return status === "done"
    ? `<span class="status-dot cell ok" title="已生成">✓</span>`
    : `<span class="status-dot cell no" title="未生成">—</span>`;
}

function statusBadge(status) {
  const cls = status === "已扫描" ? "badge-green" : status === "部分扫描" ? "badge-warn" : "badge-soft";
  return `<span class="badge-soft ${cls}">${esc(status)}</span>`;
}

// ============================================================ home
export async function home() {
  const el = root();
  el.innerHTML = loading("正在加载总览");
  const d = await api("/api/overview");
  const k = d.kpi;
  const latest = d.latest || [];
  const todos = d.todos || {};
  const topRegions = (d.inventory_by_region || []).slice(0, 4);

  const dayOf = (s) => {
    const t = String(s || "");
    return { day: t.slice(8, 10) || "—", month: (t.slice(5, 7) || "") + "月" };
  };
  const latestHtml = latest.length ? latest.map((s) => {
    const dt = dayOf(s.scanned_at);
    return `<div class="inbox-item" data-image="${s.image_id || ""}">
      <div class="ii-date"><b>${dt.day}</b>${dt.month}</div>
      <div class="ii-main"><b>${esc(s.code)} ${esc(s.name)}</b><span>${fmt(s.top_md, 2)}—${fmt(s.bottom_md, 2)}m · ${s.images_count} 张影像</span></div>
      <div class="ii-tag">查看</div>
    </div>`;
  }).join("") : `<div class="inbox-empty">暂无扫描记录</div>`;

  const todoHtml = [
    ["待扫描井", "尚未安排扫描任务", todos.pending || 0],
    ["部分扫描", "需要补扫或补录", todos.partial || 0],
    ["无影像井", "库存有岩心但没有图", todos.missing || 0],
    ["测量标注", "累计保存的标注", todos.annotations || 0],
  ].map(([name, sub, n]) => `<div class="inbox-item" data-go="wells">
    <div class="ii-date"><b>${n}</b>项</div>
    <div class="ii-main"><b>${name}</b><span>${sub}</span></div>
    <div class="ii-tag">处理</div>
  </div>`).join("");

  el.innerHTML = `
    <div class="overview">
      <div class="pulse-band">
        <div class="pulse-item accent">
          <div class="pulse-label">库存岩心</div>
          <div class="pulse-value">${fmt(k.inventory_m, 2)}<em>m</em></div>
          <div class="pulse-meta">当前库 <b>${k.total_wells}</b> 口井</div>
          <svg class="pulse-spark" viewBox="0 0 76 26"><polyline points="0,21 12,18 24,19 36,12 48,14 60,7 76,9" fill="none" stroke="#0e7490" stroke-width="1.5"></polyline></svg>
        </div>
        <div class="pulse-item">
          <div class="pulse-label">库存岩屑</div>
          <div class="pulse-value">${fmtInt(k.cuttings_bags)}<em>包</em></div>
          <div class="pulse-meta">按区块汇总</div>
        </div>
        <div class="pulse-item">
          <div class="pulse-label">库存井壁</div>
          <div class="pulse-value">${fmtInt(k.sidewall_pcs)}<em>颗</em></div>
          <div class="pulse-meta">已编目井壁取心</div>
        </div>
        <div class="pulse-item">
          <div class="pulse-label">扫描覆盖率</div>
          <div class="pulse-value">${fmt(k.coverage, 0)}<em>%</em></div>
          <div class="pulse-meta">累计 <b>${fmt(k.scanned_m, 0)} m</b> · 待扫描 <b>${todos.pending || 0}</b> 口</div>
        </div>
      </div>

      <div class="overview-grid">
        <section class="panel map-card">
          <div class="panel-hd"><span class="bar"></span><h3>井位与扫描覆盖</h3><span class="hd-sub">WELL MAP</span></div>
          <div class="panel-bd">
            <div class="map-wrap"></div>
            <div class="map-overlay"><span class="chip on">全国</span><span class="chip">覆盖率着色</span></div>
            <div class="map-stat"><b>${fmt(k.coverage, 0)}%</b><span>平均覆盖</span></div>
            <div class="map-side">
              <div class="ms-title">库存 TOP 4 / REGION</div>
              ${topRegions.map(([n, v]) => `<div class="ms-row"><span>${esc(n)}</span><b>${fmt(v, 0)}</b></div>`).join("")}
            </div>
          </div>
        </section>

        <section class="panel inbox">
          <div class="panel-hd"><span class="bar"></span><h3>工作台</h3><span class="hd-sub">INBOX</span></div>
          <div class="inbox-tabs" id="inboxTabs">
            <button class="active" data-tab="live">最新入库</button>
            <button data-tab="todo">待办事项</button>
          </div>
          <div class="inbox-body" id="inboxBody">${latestHtml}</div>
        </section>
      </div>

      <div class="insight-row">
        <section class="panel">
          <div class="panel-hd"><span class="bar"></span><h3>井扫描进度</h3><span class="hd-sub">BY WELL (m)</span></div>
          <div class="panel-bd chart"><div id="scanChart" class="chart"></div></div>
        </section>
        <section class="panel">
          <div class="panel-hd"><span class="bar"></span><h3>岩屑库存分布</h3><span class="hd-sub">BY REGION (包)</span></div>
          <div class="panel-bd chart"><div id="cutChart" class="chart"></div></div>
        </section>
        <section class="panel">
          <div class="panel-hd"><span class="bar"></span><h3>岩心库存分布</h3><span class="hd-sub">BY REGION (m)</span></div>
          <div class="panel-bd chart"><div id="invChart" class="chart"></div></div>
        </section>
      </div>
    </div>`;

  barChart(document.getElementById("scanChart"), d.scan_by_well.map((x) => [x.code, x.value]), { height: 200, horizontal: true, suffix: "m", labelWidth: 62 });
  barChart(document.getElementById("cutChart"), d.cuttings_by_region, { height: 200, horizontal: true, suffix: "", color: "#0f9f6e", color2: "#0f766e", labelWidth: 70 });
  barChart(document.getElementById("invChart"), d.inventory_by_region, { height: 200, horizontal: true, suffix: "m", color: "#2563eb", color2: "#0e7490", labelWidth: 70 });

  renderChinaMap(document.querySelector(".map-wrap"), d.map_points, (id) => go(`#/well/${id}`));

  const body = document.getElementById("inboxBody");
  document.querySelectorAll("#inboxTabs button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("#inboxTabs button").forEach((x) => x.classList.toggle("active", x === b));
    body.innerHTML = b.dataset.tab === "live" ? latestHtml : todoHtml;
  }));
  body.addEventListener("click", (e) => {
    const item = e.target.closest(".inbox-item");
    if (!item) return;
    if (item.dataset.image) go(`#/image/${item.dataset.image}`);
    else if (item.dataset.go) go("#/wells");
  });

  document.getElementById("updatedAt").textContent = k.updated_at || "—";
}

// ============================================================ wells
export async function wells() {
  const el = root();
  const { params } = qsFromHash();
  let page = parseInt(params.get("page") || "1", 10) || 1;
  let q = params.get("q") || "";
  let region = params.get("region") || "";
  let year = params.get("year") || "";
  let tectonic = params.get("tectonic") || "";
  let mode = qsFromHash().params.get("view") === "table" ? "table" : "cards";
  let lastData = null;
  let filtersPainted = false;

  el.innerHTML = `
    <div class="section-head">
      <div>
        
        <div class="sh-sub">按地区、构造带、年份定位井；卡片上直接看库存与成果完成度</div>
      </div>
      <div class="sh-actions">
        <button class="btn ghost" id="exportWells">导出清单</button>
      </div>
    </div>
    <div class="explorer">
      <aside class="panel facet-rail">
        <h3>筛选</h3>
        <input class="input facet-search" id="wQuery" placeholder="井号 / 井名 / 地区" value="${esc(q)}">
        <div class="facet-group"><h4>地区</h4><div class="facet-chips" id="fRegion"></div></div>
        <div class="facet-group"><h4>构造带</h4><div class="facet-chips" id="fTectonic"></div></div>
        <div class="facet-group"><h4>年份</h4><div class="facet-chips" id="fYear"></div></div>
        <button class="btn ghost facet-reset" id="wReset">重置筛选</button>
      </aside>
      <section class="results">
        <div class="results-head">
          <div class="rh-main"><b id="wTotal">—</b> 口井 <span style="color:#64748b">/ 当前条件</span></div>
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:10px;color:#64748b" id="wPageInfo"></span>
            <div class="view-toggle" id="viewToggle">
              <button data-mode="cards" class="active">卡片</button>
              <button data-mode="table">表格</button>
            </div>
          </div>
        </div>
        <div id="wellResults"></div>
        <div class="pager" id="pager"></div>
      </section>
    </div>`;

  const facetHtml = (key, items, current) =>
    `<button class="facet-chip ${!current ? "active" : ""}" data-facet="${key}" data-value="">全部</button>` +
    items.map((v) => `<button class="facet-chip ${String(v) === String(current) ? "active" : ""}" data-facet="${key}" data-value="${esc(v)}">${esc(v)}</button>`).join("");

  function paintFacets(filters) {
    document.getElementById("fRegion").innerHTML = facetHtml("region", filters.regions, region);
    document.getElementById("fTectonic").innerHTML = facetHtml("tectonic", filters.tectonics, tectonic);
    document.getElementById("fYear").innerHTML = facetHtml("year", filters.years, year);
    filtersPainted = true;
  }

  function syncFacetActive() {
    document.querySelectorAll(".facet-chip").forEach((chip) => {
      const key = chip.dataset.facet;
      const cur = key === "region" ? region : key === "year" ? year : tectonic;
      chip.classList.toggle("active", String(chip.dataset.value) === String(cur || ""));
    });
  }

  const REPORT_SHORT = {
    CORE_BASIC: "基本图", CORE_COMPOSITE: "综合图", FLUORESCENCE: "荧光",
    CUTTINGS_COMPOSITE: "岩屑", MULTI_WELL: "多井", BOREHOLE_COLUMN: "柱状",
    CORE_LAYER: "层模板",
  };
  const reportAction = (wellId, r) => {
    if (r.file_url) return [r.file_url, "打开成果图"];
    const map = {
      CORE_BASIC: [`#/well/${wellId}?tab=column`, "打开综合柱状图"],
      CORE_COMPOSITE: [`#/well/${wellId}?tab=column`, "打开综合柱状图"],
      BOREHOLE_COLUMN: [`#/well/${wellId}?tab=column`, "打开钻孔柱状图"],
      FLUORESCENCE: [`#/well/${wellId}?tab=images&type=FLUORESCENCE`, "查看荧光影像"],
      CUTTINGS_COMPOSITE: [`#/well/${wellId}?tab=ledger`, "查看取心记录"],
      MULTI_WELL: ["#/reports", "打开多井对比"],
      CORE_LAYER: [`#/well/${wellId}?tab=core`, "查看岩心层段"],
    };
    return map[r.code] || [`#/well/${wellId}?tab=charts&template=${r.template_id}`, "查看成果"];
  };
  const reportHref = (wellId, r) => reportAction(wellId, r)[0];

  const cardHtml = (w) => {
    const ringColor = w.coverage >= 70 ? "#0f9f6e" : w.coverage > 0 ? "#b7791f" : "#dc4c64";
    const reps = w.reports || [];
    const done = reps.filter((r) => r.status === "已生成").length;
    const chips = reps.slice(0, 4).map((r) => `<span class="chip ${r.status === "已生成" ? "on" : "off"}">${REPORT_SHORT[r.code] || r.name}</span>`).join("") +
      (reps.length > 4 ? `<span class="chip off">+${reps.length - 4}</span>` : "");
    const reportLine = reps.length ? `成果图 ${done}/${reps.length}` : "暂无成果图";
    return `<div class="well-card" data-id="${w.id}">
      <div class="wc-top">
        <div>
          <div class="wc-code">${esc(w.code)}</div>
          <div class="wc-name">${esc(w.name)}</div>
          <div class="wc-region">${esc(w.region)} · ${esc(w.tectonic)} · ${esc(w.type)}</div>
        </div>
        <div class="wc-ring" style="--p:${w.coverage};--ring:${ringColor}"><span>${w.coverage}%</span></div>
      </div>
      <div class="wc-metrics">
        <div class="wc-metric"><b>${fmt(w.inventory, 2)}</b><span>库存岩心 m</span></div>
        <div class="wc-metric"><b>${fmtInt(w.cuttings)}</b><span>岩屑 包</span></div>
        <div class="wc-metric"><b>${w.year}</b><span>完钻年份</span></div>
      </div>
      <div class="wc-chips">${chips}</div>
      <div class="wc-hint">${reportLine} · 打开档案 →</div>
    </div>`;
  };

  const tableHtml = (items) => `<div class="well-table-wrap"><div class="table-wrap"><table class="grid well-table">
    <thead><tr>
      <th class="left">井号 / 井名</th><th class="left">地区 / 构造带</th><th>年份 / 井别</th>
      <th>坐标</th><th>海拔</th><th>完钻 / 库存</th><th>岩屑 / 井壁</th>
      <th>覆盖 / 扫描</th><th>状态</th><th class="left">更新时间</th><th>成果图</th><th style="width:64px">操作</th>
    </tr></thead>
    <tbody>${items.map((w) => `<tr class="well-row" data-id="${w.id}">
      <td class="left"><span class="well-link">${esc(w.code)}</span><br><span class="sub">${esc(w.name)}</span></td>
      <td class="left">${esc(w.region)}<br><span class="sub">${esc(w.tectonic)}</span></td>
      <td>${w.year}<br><span class="sub">${esc(w.type)}</span></td>
      <td class="num" title="经度 ${fmt(w.lon,3)} / 纬度 ${fmt(w.lat,3)}">${fmt(w.lon, 3)}<br><span class="sub">${fmt(w.lat, 3)}</span></td>
      <td class="num" title="补心 ${fmt(w.kb,2)} / 地面 ${fmt(w.ground,2)}">${fmt(w.kb, 2)}<br><span class="sub">${fmt(w.ground, 2)}</span></td>
      <td class="num" title="完钻井深 ${fmt(w.final_depth,2)} / 库存 ${fmt(w.inventory,2)}">${fmt(w.final_depth, 2)}<br><span class="sub">${fmt(w.inventory, 2)} m</span></td>
      <td class="num" title="岩屑 ${fmtInt(w.cuttings)} 包 / 井壁 ${fmtInt(w.sidewall)} 颗">${fmtInt(w.cuttings)}<br><span class="sub">${fmtInt(w.sidewall)} 颗</span></td>
      <td><span style="color:${w.coverage >= 70 ? "#0f9f6e" : w.coverage > 0 ? "#b7791f" : "#dc4c64"};font-family:Bahnschrift">${w.coverage}%</span><br><span class="sub">${fmt(w.scanned,1)} m</span></td>
      <td>${statusBadge(w.status)}</td>
      <td class="left">${esc(w.updated_at)}</td>
      <td><div class="report-mini">${(w.reports || []).map((r) => `<a class="report-mini-item ${r.status === "已生成" ? "on" : ""}" href="${reportHref(w.id, r)}" data-report="1" title="${esc(r.name)} ${esc(r.version)} · ${esc(r.status)}">${REPORT_SHORT[r.code] || esc(r.name)}</a>`).join("") || '<span class="sub">—</span>'}</div></td>
      <td><button class="btn small ghost" data-id="${w.id}">档案</button></td>
    </tr>`).join("")}</tbody>
  </table></div></div>`;

  function renderResults(items) {
    document.getElementById("wellResults").innerHTML = items.length
      ? (mode === "cards" ? `<div class="well-grid">${items.map(cardHtml).join("")}</div>` : tableHtml(items))
      : empty("没有匹配的井，试试放宽筛选条件");
  }

  async function load(p = 1) {
    const query = new URLSearchParams();
    if (q) query.set("q", q);
    if (region) query.set("region", region);
    if (year) query.set("year", year);
    if (tectonic) query.set("tectonic", tectonic);
    query.set("page", p);
    query.set("page_size", "50");
    const data = await api("/api/wells?" + query.toString());
    lastData = data;
    if (!filtersPainted) paintFacets(data.filters);
    document.getElementById("wTotal").textContent = data.total;
    document.getElementById("wPageInfo").textContent = `第 ${data.page} / ${Math.max(1, Math.ceil(data.total / data.page_size))} 页`;
    renderResults(data.items);
    if (filtersPainted) syncFacetActive();
    renderPager(data.page, Math.ceil(data.total / data.page_size));
    page = data.page;
  }

  function renderPager(cur, total) {
    const box = document.getElementById("pager");
    if (!total || total <= 1) { box.innerHTML = ""; return; }
    let html = `<button class="page-btn" data-p="${Math.max(1, cur - 1)}">上一页</button>`;
    const start = Math.max(1, cur - 2), end = Math.min(total, start + 4);
    for (let i = start; i <= end; i++) html += `<button class="page-btn ${i === cur ? "active" : ""}" data-p="${i}">${i}</button>`;
    html += `<button class="page-btn" data-p="${Math.min(total, cur + 1)}">下一页</button>`;
    box.innerHTML = html;
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => load(parseInt(b.dataset.p, 10))));
  }

  let timer = null;
  document.getElementById("wQuery").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { q = e.target.value.trim(); load(1); }, 260);
  });
  document.getElementById("fRegion").addEventListener("click", (e) => {
    const b = e.target.closest("[data-facet]");
    if (!b) return;
    region = b.dataset.value; load(1);
  });
  document.getElementById("fTectonic").addEventListener("click", (e) => {
    const b = e.target.closest("[data-facet]");
    if (!b) return;
    tectonic = b.dataset.value; load(1);
  });
  document.getElementById("fYear").addEventListener("click", (e) => {
    const b = e.target.closest("[data-facet]");
    if (!b) return;
    year = b.dataset.value; load(1);
  });
  document.getElementById("wReset").addEventListener("click", () => {
    q = region = year = tectonic = "";
    document.getElementById("wQuery").value = "";
    load(1);
  });
  document.querySelectorAll("#viewToggle button").forEach((x) => x.classList.toggle("active", x.dataset.mode === mode));
  document.getElementById("viewToggle").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-mode]");
    if (!b) return;
    mode = b.dataset.mode;
    document.querySelectorAll("#viewToggle button").forEach((x) => x.classList.toggle("active", x === b));
    if (lastData) renderResults(lastData.items);
  });
  document.getElementById("wellResults").addEventListener("click", (e) => {
    if (e.target.closest("[data-report]")) return;
    const t = e.target.closest("[data-id]");
    if (t) go(`#/well/${t.dataset.id}`);
  });
  document.getElementById("exportWells").addEventListener("click", () => {
    const items = (lastData && lastData.items) || [];
    if (!items.length) { toast("暂无可导出的井", "error"); return; }
    const head = ["井号", "井名", "区块", "构造带", "年份", "井别", "经度", "纬度", "补心海拔", "地面海拔", "完钻井深", "库存(m)", "岩屑(包)", "井壁(颗)", "覆盖率(%)", "扫描(m)", "扫描状态", "更新时间"];
    const escCsv = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
    const lines = [head.join(","), ...items.map((x) => [x.code, x.name, x.region, x.tectonic, x.year, x.type, x.lon, x.lat, x.kb, x.ground, x.final_depth, x.inventory, x.cuttings, x.sidewall, x.coverage, x.scanned, x.status, x.updated_at].map(escCsv).join(","))];
    const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "well_list.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });
  await load(page);
}

// ============================================================ well detail
export async function well(id) {
  const el = root();
  el.innerHTML = loading("正在加载单井数据");
  const d = await api(`/api/wells/${id}`);
  const me = await api("/api/auth/me").catch(() => ({ user: null }));
  const canWrite = !!(me.user && ["admin", "editor"].includes(me.user.role_key));
  const w = d.well;
  const runs = d.runs || [];
  const totalRuns = runs.length;
  const totalCore = runs.reduce((s, r) => s + (r.core_length || 0), 0);
  const core = d.core || {};
  const coreCount = ["descriptions", "fractures", "vugs", "sidewalls", "samples", "analyses", "batches", "plans"]
    .reduce((n, k) => n + ((core[k] || []).length), 0);
  const reports = d.reports || [];
  const reportDone = reports.filter((x) => x.status === "已生成").length;
  const reportViewHref = (r) => {
    if (r.file_url) return r.file_url;
    const map = {
      CORE_BASIC: `#/well/${id}?tab=column`, CORE_COMPOSITE: `#/well/${id}?tab=column`,
      BOREHOLE_COLUMN: `#/well/${id}?tab=column`,
      FLUORESCENCE: `#/well/${id}?tab=images&type=FLUORESCENCE`,
      CUTTINGS_COMPOSITE: `#/well/${id}?tab=ledger`,
      MULTI_WELL: "#/reports",
      CORE_LAYER: `#/well/${id}?tab=core`,
    };
    return map[r.code] || `#/well/${id}?tab=charts&template=${r.template_id}`;
  };
  const imageType = qsFromHash().params.get("type");
  const visibleImages = imageType ? d.images.filter((x) => x.type === imageType) : d.images;

  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div>
        
        <div class="sh-sub">井档案 / ${esc(w.code)} · ${esc(w.region)} · ${esc(w.tectonic)} · ${esc(w.type)}</div>
      </div>
      <div class="sh-actions">
        <button class="btn ghost" id="backWells">返回井库</button>
        <button class="btn primary" id="printCol">导出图件</button>
      </div>
    </div>

    <div class="dossier">
      <aside class="panel dossier-rail">
        <div class="dr-kicker">WELL DOSSIER</div>
        <h1>${esc(w.name)}</h1>
        <div class="dr-code">${esc(w.code)}</div>
        <div class="dr-tags"><span class="badge-soft">${esc(w.type)}</span>${statusBadge(w.status)}<span class="badge-soft">${w.year}</span></div>
        <div class="dossier-stats">
          <div class="dossier-stat"><b>${totalRuns}</b><span>取心筒次</span></div>
          <div class="dossier-stat"><b>${fmt(totalCore, 2)}</b><span>累计心长 m</span></div>
          <div class="dossier-stat"><b>${fmt(w.inventory, 2)}</b><span>库存岩心 m</span></div>
          <div class="dossier-stat"><b>${w.coverage}%</b><span>扫描覆盖率</span></div>
        </div>
        <div class="dossier-nav" id="dossierNav">
          <button class="active" data-tab="column">综合柱状图 <em>${runs.length}</em></button>
          <button data-tab="ledger">取心记录 <em>${runs.length}</em></button>
          <button data-tab="images">岩心影像 <em>${d.images.length}</em></button>
          <button data-tab="exp">实验分析 <em>${d.experiments.length}</em></button>
          <button data-tab="core">岩心数据 <em>${coreCount}</em></button>
          <button data-tab="charts">成果输出 <em>${reportDone}/${reports.length}</em></button>
          <button data-tab="stock">库存 <em>${d.inventory.length}</em></button>
        </div>
        <div style="margin-top:16px;padding-top:14px;border-top:1px solid #e8eff5;font-size:10px;color:#7b8fa3;line-height:1.8">
          完钻井深 ${fmt(w.final_depth, 2)} m<br>
          岩屑 ${fmtInt(w.cuttings)} 包 · 井壁 ${w.sidewall} 颗<br>
          更新于 ${esc(w.updated_at)}
        </div>
      </aside>

      <div class="dossier-main">
        <div class="tab-panel active" id="tab-column"></div>
        <div class="tab-panel" id="tab-ledger"></div>
        <div class="tab-panel" id="tab-images"></div>
        <div class="tab-panel" id="tab-exp"></div>
        <div class="tab-panel" id="tab-core"></div>
        <div class="tab-panel" id="tab-charts"></div>
        <div class="tab-panel" id="tab-stock"></div>
      </div>
    </div>`;

  const renderColumnTab = (runIndex = 0) => {
    const run = runs[runIndex];
    if (!run) { document.getElementById("tab-column").innerHTML = empty("该井暂无取心数据"); return; }
    document.getElementById("tab-column").innerHTML = `
      <div class="col-toolbar no-print">
        <span style="font-size:11px;color:#64748b">选择筒次</span>
        <div class="run-btns">${runs.map((r, i) => `<button class="btn small ${i === runIndex ? "active" : ""}" data-run="${i}">第${r.run_no}筒</button>`).join("")}</div>
        <div class="spacer"></div>
        <span style="font-size:10px;color:#64748b">模板 COLUMN_STD v1.0 · 深度单位 m</span>
        <button class="btn small ghost" id="printCol2">打印 / 导出 PDF</button>
      </div>
      <div class="column-paper" id="columnPaper">${columnHtml(w, run)}</div>`;
    document.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", () => renderColumnTab(parseInt(b.dataset.run, 10))));
    const p = document.getElementById("printCol2");
    if (p) p.addEventListener("click", () => window.print());
  };

  document.getElementById("tab-ledger").innerHTML = `
    <section class="panel">
      <div class="table-wrap"><table class="grid">
        <thead><tr><th>筒次</th><th>取心井段</th><th>进尺(m)</th><th>心长(m)</th><th>收获率</th><th>层位</th><th>岩性</th><th>取心日期</th><th>操作</th></tr></thead>
        <tbody>${runs.map((r) => `<tr>
          <td>第${r.run_no}筒</td><td class="num">${fmt(r.top_md, 2)}—${fmt(r.bottom_md, 2)}</td>
          <td class="num">${fmt(r.footage, 2)}</td><td class="num">${fmt(r.core_length, 2)}</td>
          <td><span style="color:${r.recovery >= 0.85 ? "#0f9f6e" : "#b7791f"}">${(r.recovery * 100).toFixed(1)}%</span></td>
          <td>${esc(r.layer)}</td><td>${esc(r.lithology)}</td><td>${esc(r.drilled_at)}</td>
          <td><button class="btn small ghost goto-run" data-run="${r.run_no}">看柱状图</button></td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>`;

  document.getElementById("tab-images").innerHTML = visibleImages.length ? `
    ${imageType ? `<div class="image-filter-bar">筛选：${imageTypeName(imageType)} · <a href="#/well/${id}?tab=images">查看全部影像</a></div>` : ""}
    <div class="result-list" style="grid-template-columns:repeat(auto-fill,minmax(230px,1fr))">
      ${visibleImages.map((img) => `<div class="result-card image-card" data-id="${img.id}">
        <img src="${img.thumb_url}" alt="">
        <div class="rc-main"><b>${imageTypeName(img.type)}</b><span>${esc(img.section_no || "")} · ${fmt(img.top_md, 2)}—${fmt(img.bottom_md, 2)}m</span><span>${esc(img.captured_at || "")}</span></div>
      </div>`).join("")}
    </div>` : empty(imageType ? "暂无该类型影像" : "暂无影像");

  document.getElementById("tab-exp").innerHTML = d.experiments.length ? `
    <section class="panel"><div class="table-wrap"><table class="grid">
      <thead><tr><th>样品号</th><th>类型</th><th>井段(m)</th><th>实验项目</th><th>参数</th><th>值</th><th>单位</th><th>实验室</th><th>日期</th></tr></thead>
      <tbody>${d.experiments.map((x) => `<tr>
        <td>${esc(x.sample_code)}</td><td>${esc(x.sample_type)}</td>
        <td class="num">${fmt(x.top_md, 2)}—${fmt(x.bottom_md, 2)}</td>
        <td>${esc(x.test_type)}</td><td>${esc(x.param)}</td>
        <td class="num" style="color:#b7791f">${x.value}</td><td>${esc(x.unit)}</td>
        <td class="left">${esc(x.lab)}</td><td>${esc(x.test_date)}</td>
      </tr>`).join("")}</tbody>
    </table></div></section>` : empty("暂无实验数据");

  const tbl = (title, rows, head, cells, entity) => `
    <section class="panel" style="margin-bottom:12px">
      <div class="panel-hd"><span class="bar"></span><h3>${title}</h3><span class="hd-sub">${rows.length} 条</span></div>
      ${rows.length ? `<div class="table-wrap"><table class="grid">
        <thead><tr>${head}<th>操作</th></tr></thead>
        <tbody>${rows.map((x) => `<tr>${cells(x)}<td><a class="btn small ghost" href="#/entry?entity=${entity}&id=${x.id}">编辑</a></td></tr>`).join("")}</tbody>
      </table></div>` : empty("暂无记录")}
    </section>`;

  document.getElementById("tab-core").innerHTML = `
    <div class="entry-import-msg" style="margin-bottom:12px">
      岩心观察、裂缝、孔洞、井壁取心、样品和取心设计；点“编辑”进入统一录入页。
      2017 岩心 13 项已覆盖：观察 ${ (core.observations || []).length } 段。
    </div>
    ${tbl("岩心描述（按区间/版本）", core.descriptions || [],
      "<th>段号</th><th>描述区间</th><th>类型</th><th>版本</th><th>当前</th><th>收获率</th><th>岩性</th><th>结构</th><th>构造</th><th>接触</th><th>化石</th><th>倾角</th><th>荧光</th><th>含油</th><th>含气</th><th>破碎/磨损</th>",
      (x) => `<td>${esc(x.section_no)}</td><td class="num">${fmt(x.interval_top_md,2)}—${fmt(x.interval_bottom_md,2)}</td>
        <td>${esc(x.description_type || "综合观察")}</td><td>v${x.version || 1}</td><td>${x.is_current ? "是" : "否"}</td>
        <td class="num">${x.recovery == null ? "—" : (x.recovery * 100).toFixed(1) + "%"}</td><td>${esc(x.lithology)}</td>
        <td>${esc(x.structure_name || x.structure_code)}</td><td>${esc(x.sedimentary_structure_name || x.sedimentary_structure_code)}</td>
        <td>${esc(x.contact_relation_name || x.contact_relation_code)}</td><td title="${esc(x.fossil_desc)}">${esc((x.fossil_name || x.fossil_desc || "—").slice(0, 12))}</td>
        <td class="num">${fmt(x.dip_angle,1)}</td><td>${esc(x.fluorescence)}</td><td>${esc(x.oil_show)}</td>
        <td>${esc(x.gas_show_name || x.gas_show_code)}</td><td>${esc(x.breakage_wear_name || x.breakage_wear_code)}</td>`, "description")}
    ${tbl("裂缝", core.fractures || [],
      "<th>段号</th><th>编号</th><th>类型</th><th>倾角</th><th>走向</th><th>长度(mm)</th><th>宽度(mm)</th><th>充填</th>",
      (x) => `<td>${esc(x.section_no)}</td><td>${esc(x.fracture_no)}</td><td>${esc(x.type_name || x.type_code)}</td>
        <td class="num">${fmt(x.dip_angle,1)}</td><td class="num">${fmt(x.strike_angle,1)}</td>
        <td class="num">${fmt(x.length_mm,1)}</td><td class="num">${fmt(x.width_mm,2)}</td><td>${esc(x.fill_name || x.fill_code)}</td>`, "fracture")}
    ${tbl("孔洞", core.vugs || [],
      "<th>段号</th><th>编号</th><th>类型</th><th>尺寸(mm)</th><th>面积(mm²)</th><th>面孔率%</th><th>充填</th>",
      (x) => `<td>${esc(x.section_no)}</td><td>${esc(x.vug_no)}</td><td>${esc(x.type_name || x.type_code)}</td>
        <td class="num">${fmt(x.size_mm,2)}</td><td class="num">${fmt(x.area_mm2,2)}</td>
        <td class="num">${fmt(x.area_pct,2)}</td><td>${esc(x.fill_name || x.fill_code)}</td>`, "vug")}
    ${tbl("井壁取心", core.sidewalls || [],
      "<th>样品号</th><th>深度(m)</th><th>岩性</th><th>含油</th><th>荧光</th><th>分析摘要</th>",
      (x) => `<td>${esc(x.sample_no)}</td><td class="num">${fmt(x.depth_md,2)}</td><td>${esc(x.lithology)}</td>
        <td>${esc(x.oil_show)}</td><td>${esc(x.fluorescence)}</td><td class="left">${esc(x.analysis_summary)}</td>`, "sidewall")}
    ${tbl("样品", core.samples || [],
      "<th>样品号</th><th>段号</th><th>母样</th><th>类型</th><th>顶深</th><th>底深</th><th>状态</th>",
      (x) => `<td>${esc(x.sample_no)}</td><td>${esc(x.section_no)}</td><td>${esc(x.parent_sample_no || "—")}</td><td>${esc(x.sample_type)}</td>
        <td class="num">${fmt(x.top_md,2)}</td><td class="num">${fmt(x.bottom_md,2)}</td><td>${esc(x.status)}</td>`, "sample")}
    ${tbl("取心设计", core.plans || [],
      "<th>回次</th><th>设计顶深</th><th>设计底深</th><th>设计进尺</th><th>设计心长</th><th>审批</th>",
      (x) => `<td>第${x.run_no}筒</td><td class="num">${fmt(x.design_top_md,2)}</td><td class="num">${fmt(x.design_bottom_md,2)}</td>
        <td class="num">${fmt(x.design_footage,2)}</td><td class="num">${fmt(x.design_core_length,2)}</td><td>${esc(x.approved_by)}</td>`, "coring_plan")}
    ${tbl("分析数据集", core.analyses || [],
      "<th>名称</th><th>版本</th><th>当前</th><th>实验室</th><th>分析日期</th><th>深度校正</th>",
      (x) => `<td>${esc(x.name)}</td><td>v${x.version}</td><td>${x.is_current ? "是" : "否"}</td>
        <td>${esc(x.lab)}</td><td>${esc(x.analysis_date)}</td><td class="num">${fmt(x.depth_shift_m,2)}</td>`, "core_analysis")}
    ${tbl("实验批次", core.batches || [],
      "<th>批次号</th><th>数据集</th><th>实验室</th><th>方法</th><th>日期</th><th>质控</th>",
      (x) => `<td>${esc(x.batch_no)}</td><td>${esc(x.analysis_name)}</td><td>${esc(x.lab)}</td>
        <td>${esc(x.method)}</td><td>${esc(x.analysis_date)}</td><td>${esc(x.qc_status)}</td>`, "analysis_batch")}`;

  const focusTid = parseInt(qsFromHash().params.get("template") || "0", 10);
  const focusReport = reports.find((x) => x.id === focusTid);
  document.getElementById("tab-charts").innerHTML = `
    ${focusReport ? `<section class="panel report-focus-card">
      <div class="rf-kicker">当前成果</div>
      <div class="rf-title">${esc(focusReport.name)} <span>${esc(focusReport.version || "")}${focusReport.project ? " · " + esc(focusReport.project) : ""}</span></div>
      <div class="rf-meta"><span>${esc(focusReport.category_name)}</span><span>${esc(focusReport.output_type)}</span><span>${esc(focusReport.status || "未生成")}</span><span>${esc(focusReport.generated_at || "尚未生成")}</span></div>
      <div class="rf-actions">
        <a class="btn small primary" href="${reportHref(id, focusReport)}">${reportAction(id, focusReport)[1]}</a>
        <button class="btn small ghost" id="clearReportFocus">返回成果列表</button>
      </div>
    </section>` : ""}
    <section class="panel">
      <div class="panel-hd"><span class="bar"></span><h3>成果输出</h3><span class="hd-sub">REPORT OUTPUTS</span></div>
      <div class="table-wrap"><table class="grid">
        <thead><tr><th>分类</th><th>模板</th><th>版本</th><th>项目</th><th>输出</th><th>状态</th><th>生成时间</th><th>操作</th></tr></thead>
        <tbody>${reports.length ? reports.map((x) => `<tr id="report-row-${x.id}" class="${focusTid === x.id ? "report-focus-row" : ""}">
          <td>${esc(x.category_name)}</td><td class="left">${esc(x.name)}</td>
          <td>${esc(x.version || "—")}</td><td>${esc(x.project || "通用")}</td><td>${esc(x.output_type)}</td>
          <td>${x.status === "已生成" ? '<span class="badge-soft badge-green">已生成</span>' : `<span class="badge-soft">${esc(x.status || "未生成")}</span>`}</td>
          <td>${esc(x.generated_at || "—")}${x.data_version ? `<br><span class="sub">数据 ${esc(x.data_version)}</span>` : ""}</td>
          <td>
            <a class="btn small ghost" href="${reportViewHref(x)}" ${x.file_url ? 'target="_blank" rel="noopener"' : ""}>${x.file_url ? "打开" : "查看"}</a>
            ${canWrite && ["CORE_BASIC", "CORE_COMPOSITE"].includes(x.code)
              ? `<button class="btn small primary report-generate" data-tid="${x.id}">${x.file_url ? "重新生成" : "生成"}</button>` : ""}
          </td>
        </tr>`).join("") : `<tr><td colspan="8">${empty("暂无成果模板")}</td></tr>`}</tbody>
      </table></div>
    </section>`;
  document.getElementById("clearReportFocus")?.addEventListener("click", () => go(`#/well/${id}?tab=charts`));
  document.querySelectorAll(".report-generate").forEach((b) => b.addEventListener("click", async () => {
    const old = b.textContent;
    b.disabled = true; b.textContent = "生成中…";
    try {
      const r = await api(`/api/reports/well/${id}/${b.dataset.tid}/generate`, { method: "POST", body: "{}" });
      toast(`成果图已生成 · 数据版本 ${r.data_version}`, "ok");
      well(id);
    } catch (e) {
      toast(e.message || "生成失败", "error");
      b.disabled = false; b.textContent = old;
    }
  }));

  document.getElementById("tab-stock").innerHTML = d.inventory.length ? `
    <section class="panel"><div class="table-wrap"><table class="grid">
      <thead><tr><th>段号</th><th>井段(m)</th><th>库位</th><th>数量</th><th>单位</th><th>状态</th><th>更新时间</th></tr></thead>
      <tbody>${d.inventory.map((x) => `<tr>
        <td>${esc(x.section_no)}</td><td class="num">${fmt(x.top_md, 2)}—${fmt(x.bottom_md, 2)}</td>
        <td class="left">${esc(x.location)}</td><td class="num">${fmt(x.quantity, 2)}</td>
        <td>${esc(x.unit)}</td><td>${x.status === "在库" ? `<span class="badge-soft badge-green">在库</span>` : `<span class="badge-soft badge-warn">${esc(x.status)}</span>`}</td>
        <td>${esc(x.updated_at)}</td>
      </tr>`).join("")}</tbody>
    </table></div></section>` : empty("暂无库存记录");

  document.getElementById("dossierNav").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-tab]");
    if (!b) return;
    document.querySelectorAll("#dossierNav button").forEach((x) => x.classList.toggle("active", x === b));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    document.getElementById("tab-" + b.dataset.tab).classList.add("active");
  });
  document.getElementById("tab-ledger").addEventListener("click", (e) => {
    const b = e.target.closest(".goto-run");
    if (!b) return;
    document.querySelector('#dossierNav button[data-tab="column"]').click();
    const idx = runs.findIndex((r) => r.run_no === parseInt(b.dataset.run, 10));
    renderColumnTab(idx < 0 ? 0 : idx);
  });
  document.getElementById("tab-images").addEventListener("click", (e) => {
    const c = e.target.closest(".image-card");
    if (c) go(`#/image/${c.dataset.id}`);
  });
  document.getElementById("backWells").addEventListener("click", () => go("#/wells"));
  document.getElementById("printCol").addEventListener("click", () => window.print());

  renderColumnTab(0);
  const initialTab = qsFromHash().params.get("tab");
  if (initialTab) {
    const btn = document.querySelector(`#dossierNav button[data-tab="${initialTab}"]`);
    if (btn) btn.click();
  }
  if (qsFromHash().params.get("template")) {
    const row = document.querySelector(".report-focus-row");
    if (row) row.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function imageTypeName(t) { return imageTypeLabel(t); }
}

function columnHtml(w, run) {
  const H = 760;
  const top = run.top_md, bottom = run.bottom_md;
  const scale = H / (bottom - top);
  const y = (d) => (d - top) * scale;
  const h = (a, b) => Math.max(2, (b - a) * scale);
  const cols = "70px 56px 64px 1.1fr 1.7fr 1.1fr 54px 54px 90px 48px 80px";
  const secs = run.sections || [];
  const strata = run.strata || [];
  const ticks = [];
  for (let d = Math.ceil(top); d <= Math.floor(bottom); d++) ticks.push(d);
  const profile = secs[0] ? secs[0].pattern : "sand";

  const secBlock = (s, inner, cls = "") =>
    `<div class="sec ${cls}" style="top:${y(s.top_md)}px;height:${h(s.top_md, s.bottom_md)}px">${inner}</div>`;

  return `
    <div class="column-title">${esc(w.name)} 岩心综合柱状图</div>
    <div class="column-sub">CORE COLUMN · ${esc(w.code)} · ${esc(w.region)}</div>
    <div class="column-meta">
      <span>第 <b>${run.run_no}</b> 筒：<b>${fmt(top, 2)}—${fmt(bottom, 2)}m</b></span>
      <span>层位：<b>${esc(run.layer)}</b></span>
      <span>进尺：<b>${fmt(run.footage, 2)}m</b></span>
      <span>心长：<b>${fmt(run.core_length, 2)}m</b></span>
      <span>收获率：<b>${(run.recovery * 100).toFixed(1)}%</b></span>
    </div>
    <div class="col-table" style="min-width:880px">
      <div class="col-groups" style="--cols:${cols}">
        <div style="grid-column:1 / 4">基础信息</div>
        <div style="grid-column:4 / 7">岩心影像</div>
        <div style="grid-column:7 / 12">地质解释</div>
      </div>
      <div class="col-head" style="--cols:${cols}">
        <div>地层<br/><span style="font-weight:400;color:#7a8b9b">界/系/统/组/段</span></div>
        <div>深度<br/><span style="font-weight:400;color:#7a8b9b">m</span></div>
        <div>岩心<br/>编号</div>
        <div>外表皮</div>
        <div>展开图</div>
        <div>荧光</div>
        <div>含油<br/>分布</div>
        <div>RQD<br/>(%)</div>
        <div>岩性定名</div>
        <div>颜色<br/>代码</div>
        <div>岩性<br/>剖面</div>
      </div>
      <div class="col-body" style="height:${H}px;--cols:${cols}">
        <div class="track stratum">
          ${strata.map((s) => `<div class="sec" style="top:${y(s.top_md)}px;height:${h(s.top_md, s.bottom_md)}px;background:${s.color}22;border-left:2px solid ${s.color}">
            <div class="txt" style="writing-mode:vertical-rl;height:100%;display:flex;align-items:center;justify-content:center;color:#1b2a3a;font-size:10px">${esc(s.name)}</div>
          </div>`).join("")}
        </div>
        <div class="track depth">
          ${ticks.map((d) => `<div class="tick" style="top:${y(d)}px">${d % 2 === 0 ? `<span>${d}</span>` : ""}</div>`).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, `<div class="txt" style="padding-top:3px;text-align:center">${esc(s.section_no)}</div>`)).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, s.strip_url ? `<img src="${s.strip_url}" alt="">` : `<div class="txt">无图</div>`)).join("")}
        </div>
        <div class="track">
          ${run.rolled ? `<img src="${run.rolled.vertical || run.rolled.url}" style="width:100%;height:100%;object-fit:fill;display:block" alt="">` : `<div class="txt">无展开图</div>`}
        </div>
        <div class="track">
          ${run.fluorescence ? `<img src="${run.fluorescence.vertical || run.fluorescence.url}" style="width:100%;height:100%;object-fit:fill;display:block" alt="">` : `<div class="txt">无荧光</div>`}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, `<div class="txt" style="padding-top:3px;text-align:center">${esc(s.oil_show || "")}</div>`, "oil-" + (s.oil_show || "不含油"))).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, `<div class="rqd-bar"><i style="width:${s.rqd}%"></i></div><div class="rqd-val">${Math.round(s.rqd)}</div>`)).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, `<div class="lith" style="padding-top:3px">${esc(s.lithology)}</div>`)).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, `<div class="color-box" style="background:${s.color}"></div>`)).join("")}
        </div>
        <div class="track">
          ${secs.map((s) => secBlock(s, "", "pat-" + (s.pattern || profile))).join("")}
        </div>
      </div>
    </div>
    <div class="column-foot">
      <span>制图：admin · ${new Date().toLocaleDateString("zh-CN")} · 模板 COLUMN_STD v1.0 · 比例尺 1:100</span>
      <span>岩心数字化平台 · 数据来源：取心台账 / 扫描记录 / 岩心描述</span>
    </div>
    <div class="column-legend">
      <span><i style="background:rgba(230,170,30,.45)"></i>油斑</span>
      <span><i style="background:rgba(210,110,20,.5)"></i>油浸</span>
      <span><i style="background:#e8dcc0"></i>砂岩</span>
      <span><i style="background:#8a9691"></i>泥岩</span>
      <span><i style="background:#cfc9b4"></i>灰岩/白云岩</span>
    </div>`;
}

// ============================================================ search
export async function search() {
  const el = root();
  const { params } = qsFromHash();
  const q = (params.get("q") || "").trim();
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">按井号、岩性、描述、图像类型检索；支持全文关键词</div>
    </div>
    <section class="panel" style="margin-bottom:14px">
      <div class="filter-bar">
        <div class="field search-inline" style="flex:1">
          <input class="input" id="searchQ" style="width:100%" placeholder="输入井号、岩性、描述关键词，例如：板东16 / 细砂岩 / 油斑" value="${esc(q)}">
        </div>
        <button class="btn primary" id="btnSearch2">搜索</button>
        <button class="btn ghost" id="btnClear">清空</button>
      </div>
      <div class="panel-bd" style="padding-top:0;display:flex;gap:8px;flex-wrap:wrap">
        ${["板东16", "细砂岩", "油斑", "荧光", "砂砾岩", "岳104"].map((t) => `<span class="badge-soft" style="cursor:pointer" data-hot="${t}">${t}</span>`).join("")}
      </div>
    </section>
    <div id="searchResult">${q ? loading("正在检索") : `<div class="empty">输入关键词开始检索；支持井号、岩性、描述、图像类型</div>`}</div>`;

  const runSearch = (value) => {
    if (!value.trim()) return;
    go(`#/search?q=${encodeURIComponent(value.trim())}`);
  };
  document.getElementById("btnSearch2").addEventListener("click", () => runSearch(document.getElementById("searchQ").value));
  document.getElementById("searchQ").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(e.target.value); });
  document.getElementById("btnClear").addEventListener("click", () => { document.getElementById("searchQ").value = ""; go("#/search"); });
  el.querySelectorAll("[data-hot]").forEach((b) => b.addEventListener("click", () => runSearch(b.dataset.hot)));

  if (!q) return;
  const d = await api("/api/search?q=" + encodeURIComponent(q));
  const box = document.getElementById("searchResult");
  if (!d.wells.length && !d.sections.length && !d.images.length) {
    box.innerHTML = empty(`没有找到与“${esc(q)}”相关的内容`);
    return;
  }
  box.innerHTML = `
    ${d.wells.length ? `<div class="result-group"><h3>井 <span style="color:#64748b">${d.wells.length}</span></h3>
      <div class="result-list">${d.wells.map((w) => `<div class="result-card" data-well="${w.id}">
        <div class="rc-main"><b>${esc(w.code)} ${esc(w.name)}</b><span>${esc(w.region)} · ${esc(w.tectonic)} · ${esc(w.type)}</span><span>库存 ${fmt(w.inventory, 2)}m · 覆盖 ${w.coverage}%</span></div>
      </div>`).join("")}</div></div>` : ""}
    ${d.sections.length ? `<div class="result-group"><h3>岩心段 <span style="color:#64748b">${d.sections.length}</span></h3>
      <div class="result-list">${d.sections.map((s) => `<div class="result-card" data-well="${s.well_id}">
        ${s.thumb ? `<img src="/${s.thumb}" alt="">` : ""}
        <div class="rc-main"><b>${esc(s.code)} · ${esc(s.section_no)}</b><span>${fmt(s.top_md, 2)}—${fmt(s.bottom_md, 2)}m · ${esc(s.lithology)} · ${esc(s.oil_show)}</span><span>${esc((s.description || "").slice(0, 42))}…</span></div>
      </div>`).join("")}</div></div>` : ""}
    ${d.images.length ? `<div class="result-group"><h3>影像 <span style="color:#64748b">${d.images.length}</span></h3>
      <div class="result-list">${d.images.map((im) => `<div class="result-card" data-image="${im.id}">
        <img src="${im.thumb_url}" alt=""><div class="rc-main"><b>${esc(im.code)} · ${esc(im.type)}</b><span>${fmt(im.top_md, 2)}—${fmt(im.bottom_md, 2)}m</span><span>${esc(im.captured_at || "")}</span></div>
      </div>`).join("")}</div></div>` : ""}`;
  box.querySelectorAll("[data-well]").forEach((c) => c.addEventListener("click", () => go(`#/well/${c.dataset.well}`)));
  box.querySelectorAll("[data-image]").forEach((c) => c.addEventListener("click", () => go(`#/image/${c.dataset.image}`)));
}

// ============================================================ map page
export async function mapPage() {
  const el = root();
  el.innerHTML = loading("正在加载 GIS 数据");
  const d = await api("/api/overview");
  const pts = d.map_points || [];
  const regions = {};
  pts.forEach((p) => { regions[p.region] = (regions[p.region] || 0) + 1; });
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">全国井位与扫描覆盖；点击井位进入井档案</div>
      <div class="sh-actions"><span class="badge-soft">共 ${pts.length} 口井</span></div>
    </div>
    <div style="display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:14px">
      <section class="panel map-panel" style="height:720px">
        <div class="panel-hd"><span class="bar"></span><h3>全国岩心井分布</h3><span class="hd-sub">点击井位进入单井</span></div>
        <div class="panel-bd"><div class="map-wrap"></div></div>
      </section>
      <section class="panel" style="height:720px;display:flex;flex-direction:column">
        <div class="panel-hd"><span class="bar"></span><h3>井位列表</h3><span class="hd-sub">${pts.length}</span></div>
        <div style="overflow:auto;flex:1">
          ${pts.map((p) => `<div class="latest-item" data-id="${p.id}">
            <div class="li-main"><b>${esc(p.code)} ${esc(p.name)}</b><span>${esc(p.region)} · 库存 ${fmt(p.inventory, 2)}m</span></div>
            <div class="li-meta"><em>${p.coverage}%</em><br>覆盖</div>
          </div>`).join("")}
        </div>
        <div class="panel-bd" style="border-top:1px solid #e8eff5;font-size:11px;color:#64748b">
          ${Object.entries(regions).map(([k, v]) => `<div style="display:flex;justify-content:space-between;padding:3px 0"><span>${esc(k)}</span><span style="color:#0e7490">${v} 口</span></div>`).join("")}
        </div>
      </section>
    </div>`;
  renderChinaMap(document.querySelector(".map-wrap"), pts, (id) => go(`#/well/${id}`));
  el.querySelectorAll(".latest-item[data-id]").forEach((x) => x.addEventListener("click", () => go(`#/well/${x.dataset.id}`)));
}

// ============================================================ inventory
export async function inventory() {
  const el = root();
  el.innerHTML = loading("正在加载库存");
  const d = await api("/api/inventory");
  const statusMap = {};
  (d.summary || []).forEach((s) => statusMap[s.status] = s);
  const totalQ = (d.summary || []).reduce((s, x) => s + (x.q || 0), 0);
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">库存台账 · 按状态筛选 / 登记流转；库位编码：库房-排-架-箱-格</div>
      <div class="sh-actions"><button class="btn primary" id="btnTxn">＋ 登记流转</button></div>
    </div>
    <div class="inv-cards">
      <div class="inv-card"><b>${fmt(totalQ, 1)}</b><span>在库岩心（m）</span></div>
      <div class="inv-card"><b>${statusMap["在库"]?.c || 0}</b><span>在库段数</span></div>
      <div class="inv-card"><b>${statusMap["借出"]?.c || 0}</b><span>借出段数</span></div>
      <div class="inv-card"><b>${statusMap["损耗"]?.c || 0}</b><span>损耗段数</span></div>
    </div>
    <section class="panel">
      <div class="filter-bar">
        <div class="field"><label>状态</label><select class="select" id="invStatus"><option value="">全部</option><option>在库</option><option>借出</option><option>损耗</option></select></div>
        <div class="spacer"></div>
        <span style="font-size:11px;color:#64748b">库位编码：库房-排-架-箱-格</span>
      </div>
      <div class="table-wrap"><table class="grid">
        <thead><tr><th>序号</th><th class="left">井号</th><th>段号</th><th>井段(m)</th><th class="left">库位</th><th>数量</th><th>单位</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody id="invBody">${invRows(d.items)}</tbody>
      </table></div>
    </section>`;
  document.getElementById("invStatus").addEventListener("change", async (e) => {
    const q = e.target.value ? "?status=" + encodeURIComponent(e.target.value) : "";
    const nd = await api("/api/inventory" + q);
    document.getElementById("invBody").innerHTML = invRows(nd.items);
  });
  document.getElementById("btnTxn").addEventListener("click", () => openTxnModal(d.items));
}

function invRows(items) {
  if (!items.length) return `<tr><td colspan="10">${empty()}</td></tr>`;
  return items.map((x, i) => `<tr>
    <td class="num">${i + 1}</td><td class="left">${esc(x.code)} ${esc(x.name)}</td>
    <td>${esc(x.section_no || "")}</td><td class="num">${fmt(x.top_md, 2)}—${fmt(x.bottom_md, 2)}</td>
    <td class="left">${esc(x.location)}</td><td class="num">${fmt(x.quantity, 2)}</td><td>${esc(x.unit)}</td>
    <td>${x.status === "在库" ? `<span class="badge-soft badge-green">在库</span>` : `<span class="badge-soft badge-warn">${esc(x.status)}</span>`}</td>
    <td>${esc(x.updated_at)}</td><td><button class="btn small ghost txn-row" data-id="${x.section_id}">流转</button></td>
  </tr>`).join("");
}

function openTxnModal(items) {
  const opts = items.slice(0, 80).map((x) => `<option value="${x.section_id}" data-qty="${x.quantity}">${esc(x.code)} · ${esc(x.section_no)} · ${fmt(x.top_md, 2)}—${fmt(x.bottom_md, 2)}m（${esc(x.location)}）</option>`).join("");
  document.getElementById("modalRoot").innerHTML = `
    <div class="modal-mask"><div class="modal">
      <div class="modal-hd">登记库存流转<button class="close" id="mClose">×</button></div>
      <div class="modal-bd">
        <div class="form-row"><label>岩心段</label><select class="select" id="txnSection">${opts}</select></div>
        <div class="form-row"><label>流转类型</label><select class="select" id="txnType"><option>入库</option><option>出库</option><option>借阅</option><option>归还</option><option>取样</option><option>损耗</option></select></div>
        <div class="form-row"><label>数量（m）</label><input class="input" id="txnQty" type="number" step="0.01"></div>
        <div class="form-row"><label>原因 / 备注</label><input class="input" id="txnReason" placeholder="例如：薄片取样 / 库房调整"></div>
      </div>
      <div class="modal-ft"><button class="btn ghost" id="mCancel">取消</button><button class="btn primary" id="mSave">提交</button></div>
    </div></div>`;
  const sel = document.getElementById("txnSection");
  const qty = document.getElementById("txnQty");
  qty.value = sel.selectedOptions[0]?.dataset.qty || "";
  sel.addEventListener("change", () => { qty.value = sel.selectedOptions[0]?.dataset.qty || ""; });
  const close = () => document.getElementById("modalRoot").innerHTML = "";
  document.getElementById("mClose").addEventListener("click", close);
  document.getElementById("mCancel").addEventListener("click", close);
  document.getElementById("mSave").addEventListener("click", async () => {
    try {
      await api("/api/inventory/txn", { method: "POST", body: JSON.stringify({
        section_id: parseInt(sel.value, 10), txn_type: document.getElementById("txnType").value,
        quantity: parseFloat(qty.value), reason: document.getElementById("txnReason").value
      }) });
      close(); toast("库存流转已登记", "ok"); inventory();
    } catch (e) { toast("登记失败：" + e.message, "error"); }
  });
}

// ============================================================ stats
export async function stats() {
  const el = root();
  el.innerHTML = loading("正在统计");
  const d = await api("/api/stats");
  const totalWells = d.region.reduce((s, x) => s + x.wells, 0);
  const totalInv = d.region.reduce((s, x) => s + (x.inventory || 0), 0);
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">区域覆盖率 / 岩性分布 / 实验类型 / 库存状态</div>
    </div>
    <div class="inv-cards">
      <div class="inv-card"><b>${totalWells}</b><span>井数</span></div>
      <div class="inv-card"><b>${fmt(totalInv, 1)}</b><span>库存岩心（m）</span></div>
      <div class="inv-card"><b>${d.exp.reduce((s, x) => s + x.c, 0)}</b><span>实验项次</span></div>
      <div class="inv-card"><b>${d.lith.length}</b><span>岩性类型</span></div>
    </div>
    <div class="stat-grid">
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>区域扫描覆盖率（%）</h3><span class="hd-sub">BY REGION</span></div><div class="panel-bd chart"><div id="stRegion"></div></div></section>
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>岩性分布</h3><span class="hd-sub">LITHOLOGY</span></div><div class="panel-bd"><div id="stLith"></div></div></section>
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>实验类型分布</h3><span class="hd-sub">EXPERIMENTS</span></div><div class="panel-bd"><div id="stExp"></div></div></section>
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>库存状态</h3><span class="hd-sub">INVENTORY</span></div><div class="panel-bd"><div id="stInv"></div></div></section>
    </div>`;
  barChart(document.getElementById("stRegion"), d.region.map((x) => [x.region, x.coverage]), { height: 250, horizontal: true, suffix: "%", labelWidth: 108 });
  donutChart(document.getElementById("stLith"), d.lith.map((x) => [x.lithology, x.c]), { centerLabel: "段" });
  barChart(document.getElementById("stExp"), d.exp.map((x) => [x.test_type, x.c]), { height: 250, horizontal: true, color: "#7c3aed", color2: "#2563eb", labelWidth: 108 });
  donutChart(document.getElementById("stInv"), d.inv.map((x) => [x.status, x.c]), { centerLabel: "段" });
}

// ============================================================ auth
export async function login() {
  const el = root();
  const { params } = qsFromHash();
  const next = (params.get("next") || "#/entry").startsWith("#/") ? (params.get("next") || "#/entry") : "#/entry";
  const me = await api("/api/auth/me").catch(() => ({ user: null }));
  if (me.user) {
    el.innerHTML = `<div class="login-wrap"><div class="login-card">
      <div class="login-kicker">SIGNED IN</div>
      <h2>${esc(me.user.name)}</h2>
      <p>${esc(me.user.account)} · ${esc(me.user.role_key === "admin" ? "管理员" : me.user.role_key === "editor" ? "录入/编辑" : "只读")}</p>
      <div class="entry-actions"><a class="btn" href="${esc(next)}">继续</a><a class="btn ghost" href="#/logout">退出登录</a></div>
    </div></div>`;
    return;
  }
  el.innerHTML = `<div class="login-wrap"><div class="login-card">
    <div class="login-kicker">CORE LAB / SIGN IN</div>
    <h2>登录岩心平台</h2>
    <p>写入、编辑、删除和 Excel 导入需要登录。只读浏览可继续使用。</p>
    <form id="loginForm" novalidate>
      <div class="form-row"><label>账号</label><input class="input" id="loginAccount" autocomplete="username" placeholder="admin"></div>
      <div class="form-row"><label>密码</label><input class="input" id="loginPassword" type="password" autocomplete="current-password" placeholder="••••••"></div>
      <div class="entry-actions"><button class="btn" type="submit" id="loginBtn">登录</button><a class="btn ghost" href="#/home">返回总览</a></div>
      <div class="entry-msg err" id="loginMsg"></div>
    </form>
  </div></div>`;
  const form = document.getElementById("loginForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = document.getElementById("loginMsg");
    const btn = document.getElementById("loginBtn");
    msg.textContent = ""; btn.disabled = true; btn.textContent = "登录中…";
    try {
      const r = await api("/api/auth/login", { method: "POST", body: JSON.stringify({
        account: document.getElementById("loginAccount").value.trim(),
        password: document.getElementById("loginPassword").value,
      }) });
      toast(`欢迎，${r.user.name}`, "ok");
      if (window.corePlatform && window.corePlatform.refreshMe) await window.corePlatform.refreshMe();
      location.hash = next;
    } catch (err) {
      msg.textContent = err.message || "登录失败";
    } finally {
      btn.disabled = false; btn.textContent = "登录";
    }
  });
}

export async function logout() {
  try { await api("/api/auth/logout", { method: "POST", body: "{}" }); } catch (e) {}
  if (window.corePlatform && window.corePlatform.refreshMe) await window.corePlatform.refreshMe();
  toast("已退出登录", "ok");
  location.hash = "#/home";
}

// ============================================================ entry
export async function entry() {
  const el = root();
  el.innerHTML = loading("正在加载录入表单");
  const me = await api("/api/auth/me").catch(() => ({ user: null }));
  if (!me.user) {
    el.innerHTML = `<div class="login-wrap"><div class="login-card">
      <div class="login-kicker">SIGN IN REQUIRED</div>
      <h2>录入需要登录</h2>
      <p>数据写入、编辑、删除和 Excel 导入需要录入员或管理员权限。只读账号可以浏览井档案和影像。</p>
      <div class="entry-actions"><a class="btn" href="#/login?next=%23%2Fentry">去登录</a><a class="btn ghost" href="#/home">返回总览</a></div>
    </div></div>`;
    return;
  }
  if (me.user.role_key === "viewer") {
    el.innerHTML = `<div class="login-wrap"><div class="login-card">
      <div class="login-kicker">READ ONLY</div>
      <h2>只读账号</h2>
      <p>${esc(me.user.name)} 当前是只读角色，不能新增或修改数据。请使用录入员/管理员账号。</p>
      <div class="entry-actions"><a class="btn" href="#/logout">切换账号</a><a class="btn ghost" href="#/wells">返回井档案</a></div>
    </div></div>`;
    return;
  }
  const meta = await api("/api/entry/meta");
  const entities = meta.entities || [];
  if (!entities.length) { el.innerHTML = empty("没有可录入的数据对象"); return; }
  const params = qsFromHash().params;
  const wanted = params.get("entity");
  const editId = parseInt(params.get("id") || "0", 10) || 0;
  let current = entities.some((x) => x.key === wanted) ? wanted : entities[0].key;
  const state = { editingId: null, importResult: null, trash: false };

  const optList = (f) => {
    const o = f.options;
    if (Array.isArray(o)) return o.map((v) => (typeof v === "object" ? { value: v.value, label: v.label } : { value: v, label: v }));
    if (!o || !o.kind) return [];
    if (o.kind === "dict") return (meta.options.dicts || {})[o.type] || [];
    return meta.options[o.kind] || [];
  };

  const control = (f) => {
    const id = `ef_${f.name}`;
    const req = f.required ? " required" : "";
    const wide = f.wide ? " wide" : "";
    const ph = String(f.placeholder || "").startsWith("例如") ? "" : (f.placeholder || "");
    let inner = "";
    if (f.type === "select") {
      const opts = optList(f).map((o) => {
        const label = (f.name === "type" && current === "image") ? imageTypeLabel(o.value) : o.label;
        return `<option value="${esc(o.value)}">${esc(label)}</option>`;
      }).join("");
      inner = `<select class="select" id="${id}" name="${esc(f.name)}"${req}><option value="">请选择</option>${opts}</select>`;
    } else if (f.type === "textarea") {
      inner = `<textarea class="input" id="${id}" name="${esc(f.name)}" rows="3"${req} placeholder="${esc(ph)}"></textarea>`;
    } else {
      const typ = f.type === "number" || f.type === "int" ? "number" : f.type === "date" ? "date" : "text";
      const step = typ === "number" ? ' step="any"' : "";
      inner = `<input class="input" id="${id}" name="${esc(f.name)}" type="${typ}"${step}${req} placeholder="${esc(ph)}" autocomplete="off">`;
    }
    return `<div class="entry-field${wide}">
      <label for="${id}">${esc(f.label)}${f.required ? '<span class="req">*</span>' : ""}</label>
      ${inner}
    </div>`;
  };

  const refreshMeta = async () => {
    meta.options = (await api("/api/entry/meta")).options;
  };

  const fillForm = (record) => {
    const form = document.getElementById("entryForm");
    if (!form || !record) return;
    for (const f of (entities.find((x) => x.key === current)?.fields || [])) {
      const node = form.elements[f.name];
      if (!node) continue;
      let v = record[f.name];
      if (v == null) v = "";
      if (f.type === "date") v = String(v).slice(0, 10);
      node.value = v;
    }
  };

  const refLabel = (name, value) => {
    if (value == null || value === "") return "—";
    const map = { well_id: "wells", run_id: "runs", section_id: "sections", sample_id: "samples", sidewall_id: "sidewalls" };
    const list = meta.options[map[name]] || [];
    const hit = list.find((x) => String(x.id) === String(value));
    return hit ? (hit.label || hit.code || hit.sample_no || String(value)) : String(value);
  };

  const renderManager = async (key) => {
    const box = document.getElementById("entryManager");
    if (!box) return;
    const ent = entities.find((x) => x.key === key);
    box.innerHTML = `<div class="entry-manager-head"><h4>数据管理 · ${esc(ent?.label || "")}</h4><span>加载中…</span></div>`;
    try {
      const isImage = key === "image";
      const d = await api(`/api/entry/list?entity=${encodeURIComponent(key)}${state.trash ? "&deleted=1" : ""}`);
      const rows = d.items || [];
      const head = (d.fields || []).map((f) => `<th>${esc(f.label)}</th>`).join("");
      const body = rows.length ? rows.map((r) => `<tr>
        <td>${r.id}</td>
        ${(d.fields || []).filter((f) => f.name !== "id").map((f) => {
          const raw = r[f.name];
          let text = raw == null || raw === "" ? "—" : String(raw);
          if (key === "image" && f.name === "type") text = imageTypeLabel(raw);
          else if (["well_id", "run_id", "section_id", "sample_id", "sidewall_id"].includes(f.name)) text = refLabel(f.name, raw);
          return `<td title="${esc(text)}">${esc(text.length > 36 ? text.slice(0, 36) + "…" : text)}</td>`;
        }).join("")}
        <td class="entry-actions-cell">
          ${d.deleted ? `<button class="entry-act" data-restore="${r.id}">恢复</button>` : `${isImage ? "" : `<button class="entry-act" data-edit="${r.id}">编辑</button>`}<button class="entry-act danger" data-del="${r.id}">删除</button>`}
        </td>
      </tr>`).join("") : `<tr><td colspan="${(d.fields || []).length + 1}" class="empty">暂无记录</td></tr>`;

      let resultHtml = "";
      if (state.importResult) {
        const r = state.importResult;
        if (r.error) {
          resultHtml = `<div class="entry-import-msg err">${esc(r.error)}</div>`;
        } else {
          resultHtml = `<div class="entry-import-msg ${r.failed ? "warn" : "ok"}">
            ${r.dry_run ? "预检查" : "导入"} ${esc(r.label || "")}：共 ${r.total} 行，${r.dry_run ? "通过" : "成功"} ${r.created} 行，失败 ${r.failed} 行。
            ${r.errors && r.errors.length ? `<details><summary>查看错误</summary><ul>${r.errors.map((e) => `<li>第 ${e.row} 行：${esc(e.error)}</li>`).join("")}</ul></details><button class="entry-act" id="entryErrCsv">下载错误 CSV</button>` : ""}
          </div>`;
        }
      }

      box.innerHTML = `
        <div class="entry-manager-head">
          <h4>数据管理 · ${esc(d.label)} <span>共 ${d.total} 条，显示最近 ${rows.length} 条</span></h4>
          <div class="entry-manager-actions">
            <button class="btn ghost" id="entryTrash">${state.trash ? "返回正常列表" : "回收站"}</button>
            ${isImage ? "" : `<a class="btn ghost" href="/api/entry/template?entity=${encodeURIComponent(key)}">下载 Excel 模板</a>
            <label class="btn ghost entry-file">预检查<input type="file" id="entryDryRun" accept=".xlsx,.xlsm"></label>
            <label class="btn ghost entry-file">导入 Excel<input type="file" id="entryFile" accept=".xlsx,.xlsm"></label>`}
          </div>
        </div>
        ${resultHtml}
        <div class="table-wrap"><table class="grid entry-table">
          <thead><tr>${head}<th>操作</th></tr></thead>
          <tbody>${body}</tbody>
        </table></div>`;
      const errCsv = document.getElementById("entryErrCsv");
      if (errCsv && state.importResult && state.importResult.errors) {
        errCsv.addEventListener("click", () => {
          const lines = ["行号,错误原因", ...state.importResult.errors.map((e) => `${e.row},"${String(e.error).replace(/"/g, '""')}"`)];
          const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = `import_errors_${key}.csv`;
          a.click();
          URL.revokeObjectURL(a.href);
        });
      }
      const trash = document.getElementById("entryTrash");
      if (trash) trash.addEventListener("click", async () => {
        state.trash = !state.trash;
        await renderManager(key);
      });
      const sendImport = async (f, dryRun) => {
        if (!f) return;
        if (f.size > 8 * 1024 * 1024) { state.importResult = { error: "文件超过 8 MB" }; await renderManager(key); return; }
        try {
          const data = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(f);
          });
          const r = await api(`/api/entry/import/${encodeURIComponent(key)}`, {
            method: "POST", body: JSON.stringify({ filename: f.name, data, dry_run: dryRun }),
          });
          state.importResult = r;
          toast(dryRun ? `预检查完成：${r.created} 行通过` : `导入完成：成功 ${r.created} 行`, r.failed ? "error" : "ok");
          if (!dryRun) await refreshMeta();
          await renderManager(key);
        } catch (err) {
          state.importResult = { error: err.message || String(err) };
          toast(state.importResult.error, "error");
          await renderManager(key);
        }
      };
      const file = document.getElementById("entryFile");
      if (file) file.addEventListener("change", () => sendImport(file.files && file.files[0], false));
      const dry = document.getElementById("entryDryRun");
      if (dry) dry.addEventListener("change", () => sendImport(dry.files && dry.files[0], true));
      box.querySelectorAll("[data-edit]").forEach((btn) => btn.addEventListener("click", async () => {
        try {
          const d = await api(`/api/entry/${encodeURIComponent(key)}/${btn.dataset.edit}`);
          renderForm(key, d.record);
          document.getElementById("entryFormBox").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) { toast(err.message || "读取失败", "error"); }
      }));
      box.querySelectorAll("[data-del]").forEach((btn) => btn.addEventListener("click", async () => {
        if (!confirm(`确定删除 ${key} #${btn.dataset.del}？有关联子记录时会被拒绝。`)) return;
        try {
          await api(`/api/entry/${encodeURIComponent(key)}/${btn.dataset.del}`, { method: "DELETE" });
          toast("已删除", "ok");
          await refreshMeta();
          await renderManager(key);
        } catch (err) { toast(err.message || "删除失败", "error"); }
      }));
    } catch (err) {
      box.innerHTML = `<div class="entry-import-msg err">${esc(err.message || String(err))}</div>`;
    }
  };

  const renderImageForm = (ent) => {
    current = "image";
    state.editingId = null;
    document.querySelectorAll(".entry-tab").forEach((b) => b.classList.toggle("active", b.dataset.key === "image"));
    const formBox = document.getElementById("entryFormBox");
    formBox.innerHTML = `
      <div class="entry-head"><h2>${esc(ent.icon)} ${esc(ent.label)}</h2><p>${esc(ent.desc || "")}</p></div>
      <form id="entryForm" novalidate>
        <div class="entry-grid">${(ent.fields || []).map(control).join("")}</div>
        <div class="entry-field wide"><label>影像文件<span class="req">*</span></label><input class="input" type="file" id="imageFile" accept="image/jpeg,image/png,image/webp"><span class="hint">支持 JPG / PNG / WebP，最大 12 MB；自动生成缩略图并归档。</span></div>
        <div class="entry-actions">
          <button class="btn" type="submit" id="entrySave">上传影像</button>
          <button class="btn ghost" type="reset">清空</button>
        </div>
        <div class="entry-msg" id="entryMsg"></div>
      </form>
      <div class="entry-manager" id="entryManager"></div>`;
    const form = document.getElementById("entryForm");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("entryMsg");
      const btn = document.getElementById("entrySave");
      const f = document.getElementById("imageFile").files[0];
      if (!f) { msg.className = "entry-msg err"; msg.textContent = "请选择影像文件"; return; }
      if (f.size > 12 * 1024 * 1024) { msg.className = "entry-msg err"; msg.textContent = "影像超过 12 MB"; return; }
      const data = {};
      for (const field of ent.fields || []) {
        const node = form.elements[field.name];
        if (node) data[field.name] = node.value.trim();
      }
      btn.disabled = true; btn.textContent = "上传中…"; msg.textContent = "";
      try {
        const dataUrl = await new Promise((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(r.result);
          r.onerror = reject;
          r.readAsDataURL(f);
        });
        const res = await api("/api/images/upload", { method: "POST", body: JSON.stringify({ ...data, file_data: dataUrl, filename: f.name }) });
        toast(`影像已上传 #${res.id}`, "ok");
        msg.className = "entry-msg ok";
        msg.textContent = `已上传影像 #${res.id}`;
        form.reset();
        await renderManager("image");
      } catch (err) {
        msg.className = "entry-msg err";
        msg.textContent = err.message || String(err);
        toast(err.message || "上传失败", "error");
      } finally {
        btn.disabled = false; btn.textContent = "上传影像";
      }
    });
    renderManager("image");
  };

  const renderForm = (key, record = null) => {
    if (key === "image") {
      renderImageForm(entities.find((x) => x.key === "image") || { label: "影像", icon: "▧", fields: [] });
      return;
    }
    current = key;
    state.editingId = record ? record.id : null;
    const ent = entities.find((x) => x.key === key) || entities[0];
    document.querySelectorAll(".entry-tab").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
    const formBox = document.getElementById("entryFormBox");
    formBox.innerHTML = `
      <div class="entry-head"><h2>${esc(ent.icon)} ${esc(ent.label)}</h2><p>${esc(ent.desc || "")}</p></div>
      <form id="entryForm" novalidate>
        <div class="entry-grid">${(ent.fields || []).map(control).join("")}</div>
        <div class="entry-actions">
          <button class="btn" type="submit" id="entrySave">${state.editingId ? "更新记录" : "保存到数据库"}</button>
          ${state.editingId ? '<button class="btn ghost" type="button" id="entryCancel">取消编辑</button>' : '<button class="btn ghost" type="reset">清空</button>'}
          <span class="hint">带 * 为必填</span>
        </div>
        <div class="entry-msg" id="entryMsg">${state.editingId ? `正在编辑 #${state.editingId}` : ""}</div>
      </form>
      <div class="entry-manager" id="entryManager"></div>`;
    const form = document.getElementById("entryForm");
    if (record) fillForm(record);
    const cancel = document.getElementById("entryCancel");
    if (cancel) cancel.addEventListener("click", () => renderForm(key));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("entryMsg");
      const btn = document.getElementById("entrySave");
      const data = {};
      for (const f of ent.fields || []) {
        const node = form.elements[f.name];
        if (node) data[f.name] = node.value.trim();
      }
      const editing = state.editingId;
      btn.disabled = true;
      btn.textContent = editing ? "更新中…" : "写入中…";
      msg.className = "entry-msg";
      msg.textContent = "";
      try {
        const url = editing ? `/api/entry/${encodeURIComponent(key)}/${editing}` : `/api/entry/${encodeURIComponent(key)}`;
        const r = await api(url, { method: editing ? "PUT" : "POST", body: JSON.stringify(data) });
        if (editing) {
          toast(`已更新 ${r.label} #${r.id}`, "ok");
          state.editingId = null;
          await refreshMeta();
          renderForm(key);
          return;
        }
        msg.className = "entry-msg ok";
        msg.textContent = `已写入：${r.label} #${r.id}`;
        toast(`已保存${r.label}`, "ok");
        form.reset();
        await refreshMeta();
        await renderManager(key);
      } catch (err) {
        msg.className = "entry-msg err";
        msg.textContent = err.message || String(err);
        toast(err.message || "写入失败", "error");
      } finally {
        btn.disabled = false;
        btn.textContent = editing ? "更新记录" : "保存到数据库";
      }
    });
    renderManager(key);
  };

  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">数据录入与维护</div>
    </div>
    <div class="entry-layout">
      <aside class="entry-tabs">
        <div class="entry-tabs-title">录入对象 / ENTITY</div>
        ${entities.map((x) => `<button class="entry-tab" data-key="${esc(x.key)}"><span class="ico">${esc(x.icon || "·")}</span><span>${esc(x.label)}</span></button>`).join("")}
      </aside>
      <div class="entry-main"><section class="panel"><div class="panel-bd" id="entryFormBox"></div></section></div>
    </div>`;
  document.querySelectorAll(".entry-tab").forEach((b) => b.addEventListener("click", () => {
    state.importResult = null;
    state.trash = false;
    renderForm(b.dataset.key);
  }));
  if (editId) {
    try {
      const d = await api(`/api/entry/${encodeURIComponent(current)}/${editId}`);
      renderForm(current, d.record);
    } catch (e) {
      toast(e.message || "记录不存在", "error");
      renderForm(current);
    }
  } else {
    renderForm(current);
  }
}
// ============================================================ reports
export async function reports() {
  const el = root();
  el.innerHTML = loading("正在加载成果输出");
  const m = await api("/api/reports/matrix");
  const templates = m.templates || [];
  const wells = m.wells || [];
  const outputs = m.outputs || {};
  let cat = "all";
  const render = () => {
    const list = cat === "all" ? templates : templates.filter((x) => x.category_name === cat);
    const done = Object.values(outputs).filter((x) => x.status === "已生成").length;
    const cats = [...new Set(templates.map((x) => x.category_name))];
    el.innerHTML = `
      <div class="section-head" style="margin-bottom:12px">
        <div class="sh-sub">成果模板、成果状态与成果文件；与岩心数据录入分离</div>
        <div class="sh-actions"><span class="badge-soft">已生成 ${done} 项</span></div>
      </div>
      <section class="panel">
        <div class="panel-hd"><span class="bar"></span><h3>成果矩阵</h3><span class="hd-sub">REPORT OUTPUTS</span>
          <div class="hd-actions"><select class="select" id="reportCat"><option value="all">全部分类</option>${cats.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select></div>
        </div>
        <div class="table-wrap report-matrix"><table class="grid">
          <thead><tr><th>井号</th><th>井名</th>${list.map((t) => `<th title="${esc(t.name)} ${esc(t.version)} ${esc(t.project)}">${esc(t.name)}${t.version ? `<br><small>${esc(t.version)}${t.project ? " · " + esc(t.project) : ""}</small>` : ""}</th>`).join("")}</tr></thead>
          <tbody>${wells.map((w) => `<tr><td>${esc(w.code)}</td><td>${esc(w.name)}</td>${list.map((t) => {
            const o = outputs[`${w.id}:${t.id}`];
            return `<td>${o && o.status === "已生成" ? '<span class="badge-soft badge-green">已生成</span>' : '<span style="color:var(--dim)">—</span>'}</td>`;
          }).join("")}</tr>`).join("")}</tbody>
        </table></div>
      </section>`;
    const sel = document.getElementById("reportCat");
    if (sel) { sel.value = cat; sel.addEventListener("change", () => { cat = sel.value; render(); }); }
  };
  render();
}

// ============================================================ admin
export async function admin() {
  const el = root();
  el.innerHTML = loading("正在加载系统信息");
  const d = await api("/api/admin");
  const tpl = await api("/api/reports/templates?all=1").catch(() => ({ items: [], categories: [] }));
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">用户与角色 / 字典编码 / 操作审计</div>
    </div>
    <div class="inv-cards">
      <div class="inv-card"><b>${d.counts.wells}</b><span>井</span></div>
      <div class="inv-card"><b>${d.counts.images}</b><span>影像</span></div>
      <div class="inv-card"><b>${d.counts.sections}</b><span>岩心段</span></div>
      <div class="inv-card"><b>${d.counts.experiments}</b><span>实验项</span></div>
    </div>
    <div style="display:grid;grid-template-columns:1.1fr .9fr;gap:14px">
      <section class="panel">
        <div class="panel-hd"><span class="bar"></span><h3>用户与角色</h3><span class="hd-sub">RBAC</span></div>
        <div class="table-wrap"><table class="grid">
          <thead><tr><th>姓名</th><th>账号</th><th>角色</th><th class="left">单位</th><th>最近登录</th></tr></thead>
          <tbody>${d.users.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.account)}</td><td><span class="badge-soft">${esc(u.role)}</span></td><td class="left">${esc(u.org)}</td><td>${esc(u.last_login)}</td></tr>`).join("")}</tbody>
        </table></div>
      </section>
      <section class="panel">
        <div class="panel-hd"><span class="bar"></span><h3>字典与编码</h3><span class="hd-sub">DICTIONARY</span></div>
        <div class="panel-bd"><div class="dict-grid" style="grid-template-columns:1fr 1fr">
          ${d.dicts.map((x) => `<div class="dict-card"><b>${x.count}</b><span>${esc(x.type)}</span></div>`).join("")}
        </div></div>
      </section>
    </div>
    <section class="panel" style="margin-top:14px">
      <div class="panel-hd"><span class="bar"></span><h3>成果模板</h3><span class="hd-sub">REPORT TEMPLATES</span>
        <div class="hd-actions"><button class="btn small" id="addChartTemplate">＋ 新增模板</button></div>
      </div>
      <div class="table-wrap"><table class="grid">
        <thead><tr><th>分类</th><th>编码</th><th>名称</th><th>版本</th><th>项目</th><th>输出</th><th>已生成</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>${(tpl.items || []).map((x) => `<tr>
          <td>${esc(x.category_name)}</td><td>${esc(x.code)}</td><td class="left">${esc(x.name)}</td>
          <td>${esc(x.version || "—")}</td><td>${esc(x.project || "通用")}</td><td>${esc(x.output_type)}</td>
          <td class="num">${x.generated_count}</td>
          <td>${x.is_active ? '<span class="badge-soft badge-green">启用</span>' : '<span class="badge-soft">停用</span>'}</td>
          <td><button class="btn small ghost tpl-toggle" data-id="${x.id}" data-active="${x.is_active ? 1 : 0}">${x.is_active ? "停用" : "启用"}</button></td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>
    <section class="panel" style="margin-top:14px">
      <div class="panel-hd"><span class="bar"></span><h3>最近操作日志</h3><span class="hd-sub">AUDIT LOG</span></div>
      <div class="table-wrap"><table class="grid">
        <thead><tr><th>用户</th><th class="left">操作</th><th class="left">对象</th><th>时间</th></tr></thead>
        <tbody>${d.audit.map((a) => `<tr><td>${esc(a.user)}</td><td class="left">${esc(a.action)}</td><td class="left">${esc(a.target)}</td><td>${esc(a.created_at)}</td></tr>`).join("")}</tbody>
      </table></div>
    </section>`;
  document.getElementById("addChartTemplate").addEventListener("click", () => openChartTemplateModal(tpl.categories || []));
  document.querySelectorAll(".tpl-toggle").forEach((b) => b.addEventListener("click", async () => {
    try {
      await api(`/api/reports/templates/${b.dataset.id}`, { method: "PUT", body: JSON.stringify({ is_active: b.dataset.active === "1" ? 0 : 1 }) });
      toast("模板状态已更新", "ok");
      admin();
    } catch (e) { toast(e.message || "更新失败", "error"); }
  }));
}

function openChartTemplateModal(categories) {
  const opts = categories.map((c) => `<option value="${esc(c.code)}">${esc(c.name)}</option>`).join("");
  document.getElementById("modalRoot").innerHTML = `
    <div class="modal-mask"><div class="modal">
      <div class="modal-hd">新增成果模板<button class="close" id="mClose">×</button></div>
      <div class="modal-bd">
        <div class="form-row"><label>模板编码</label><input class="input" id="tplCode" placeholder="例如 CORE_COMPOSITE"></div>
        <div class="form-row"><label>模板名称</label><input class="input" id="tplName" placeholder="例如 岩心综合图"></div>
        <div class="form-row"><label>分类</label><select class="select" id="tplCat">${opts}</select></div>
        <div class="form-row"><label>版本</label><input class="input" id="tplVersion" placeholder="例如 V10"></div>
        <div class="form-row"><label>项目/客户</label><input class="input" id="tplProject" placeholder="通用则留空"></div>
        <div class="form-row"><label>输出类型</label><select class="select" id="tplOutput"><option>交互图</option><option>截图</option><option>PDF</option><option>文件</option></select></div>
      </div>
      <div class="modal-ft"><button class="btn ghost" id="mCancel">取消</button><button class="btn primary" id="mSave">保存</button></div>
    </div></div>`;
  const close = () => document.getElementById("modalRoot").innerHTML = "";
  document.getElementById("mClose").addEventListener("click", close);
  document.getElementById("mCancel").addEventListener("click", close);
  document.getElementById("mSave").addEventListener("click", async () => {
    try {
      await api("/api/reports/templates", { method: "POST", body: JSON.stringify({
        code: document.getElementById("tplCode").value.trim(),
        name: document.getElementById("tplName").value.trim(),
        category_code: document.getElementById("tplCat").value,
        version: document.getElementById("tplVersion").value.trim(),
        project: document.getElementById("tplProject").value.trim(),
        output_type: document.getElementById("tplOutput").value,
      }) });
      close(); toast("模板已新增", "ok"); admin();
    } catch (e) { toast(e.message || "新增失败", "error"); }
  });
}

// ============================================================ help
export async function help() {
  const el = root();
  el.innerHTML = `
    <div class="section-head" style="margin-bottom:12px">
      <div class="sh-sub">快速上手与使用说明</div>
    </div>
    <div style="display:grid;grid-template-columns:1.1fr .9fr;gap:14px">
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>快速上手</h3></div>
        <div class="panel-bd help-list">
          <p><b>1. 看全局</b>：首页展示当前库库存、扫描覆盖率、最新扫描和井位分布。</p>
          <p><b>2. 找井</b>：井号列表支持地区 / 构造带 / 年份 / 关键字筛选；卡片/表格切换，表格显示全部井字段，点击任意一行打开井档案。</p>
          <p><b>3. 看柱状图</b>：点击井号进入单井，切换筒次查看综合柱状图；可打印或导出 PDF。</p>
          <p><b>4. 看影像</b>：在“岩心影像”中点任意一张图进入浏览器；左侧深度标尺可跳转，工具条可缩放、测量。</p>
          <p><b>5. 做测量</b>：点“测量”，在图上点两下，得到长度（mm）；点“保存标注”写入数据库。</p>
          <p><b>6. 管库存</b>：岩心库管理支持按状态筛选；点“登记流转”可登记入库 / 借阅 / 取样 / 损耗。</p>
          <p><b>7. 录数据</b>：左侧“录入”可新增井、回次、岩心段、观察、裂缝、孔洞、井壁取心、样品、实验、取心设计和影像；下方列表可编辑、删除，支持 Excel 批量导入。</p>
        </div>
      </section>
      <section class="panel"><div class="panel-hd"><span class="bar"></span><h3>说明</h3></div>
        <div class="panel-bd help-list">
          <p><b>数据范围</b>：井、取心回次、岩心段、岩心观察、裂缝、孔洞、井壁取心、样品、实验、取心设计和影像均以当前库为准。</p>
          <p><b>账号权限</b>：写入需要录入员或管理员权限；只读账号可以浏览井档案、影像和分析结果。</p>
          <p><b>数据维护</b>：新增、修改、删除均保留审计记录；删除的记录可在“回收站”恢复。</p>
          <p><b>影像</b>：上传后自动生成缩略图，可在井档案和影像浏览中查看。</p>
          <p><b>快捷键</b>：图片浏览时滚轮缩放，拖拽平移；测量模式下单击两次完成一条测量线。</p>
        </div>
      </section>
    </div>`;
}

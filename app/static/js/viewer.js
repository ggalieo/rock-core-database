import { api, esc, fmt, toast, go } from "./api.js";

const TYPE_NAME = { SURFACE: "外表皮", ROLLED: "展开图", FLUORESCENCE: "荧光", BOX: "岩心箱", THIN_SECTION: "薄片" };
const TYPE_ORDER = ["SURFACE", "ROLLED", "FLUORESCENCE", "BOX", "THIN_SECTION"];

export async function imageViewer(id) {
  const root = document.getElementById("view");
  root.innerHTML = `<div class="loading"><i></i>正在加载影像…</div>`;
  let d;
  try { d = await api(`/api/images/${id}`); }
  catch (e) { root.innerHTML = `<div class="empty">影像加载失败：${esc(e.message)}</div>`; return; }

  const img = d.image;
  const siblings = d.siblings || [];
  const types = TYPE_ORDER.filter((t) => siblings.some((s) => s.type === t));
  const sameType = siblings.filter((s) => s.type === img.type);
  const idx = sameType.findIndex((s) => s.id === img.id);

  root.innerHTML = `
    <div class="section-head" style="margin-bottom:10px">
      <div>
        <h2>${esc(img.code)} · ${TYPE_NAME[img.type] || img.type}</h2>
        <div class="sh-sub">${esc(img.code)} / 第${img.run_no || "—"}筒 / ${esc(img.section_no || "整筒")} · ${TYPE_NAME[img.type] || img.type}</div>
      </div>
      <div class="sh-actions">
        <button class="btn ghost" id="backWell">返回井档案</button>
        <button class="btn ghost" id="prevImg" ${d.prev ? "" : "disabled"}>上一张</button>
        <button class="btn ghost" id="nextImg" ${d.next ? "" : "disabled"}>下一张</button>
      </div>
    </div>

    <div class="viewer-head">
      <div class="segmented" id="typeTabs">
        ${types.map((t) => `<button class="${t === img.type ? "active" : ""}" data-type="${t}">${TYPE_NAME[t]}</button>`).join("")}
      </div>
      <span class="vh-sub">${fmt(img.top_md, 2)}—${fmt(img.bottom_md, 2)} m · ${fmt(img.mm_per_px, 3)} mm/px</span>
      <div class="spacer"></div>
      <span style="font-size:10px;color:#64748b" id="zoomLabel">100%</span>
      <button class="btn small ghost" id="exportImg">导出原图</button>
    </div>

    <div class="viewer-shell">
      <div class="stage-wrap">
        <div class="tool-dock">
          <button id="zoomIn" title="放大">＋</button>
          <button id="zoomOut" title="缩小">−</button>
          <button id="zoomFit" title="最佳尺寸">⤢</button>
          <button id="zoomReset" title="还原">↺</button>
          <button id="measureBtn" title="测量">／</button>
          <button id="saveAnno" title="保存标注" disabled>✓</button>
        </div>
        <div class="image-stage" id="stage">
          <div class="image-wrap" id="imgWrap">
            <img id="mainImg" src="${img.url}" alt="">
            <svg class="annot-layer" id="annotLayer"></svg>
          </div>
          <div class="scalebar" id="scalebar">1 cm</div>
          <div class="image-hud">${fmt(img.width)} × ${fmt(img.height)} px · ${img.dpi || "—"} DPI</div>
        </div>
        <div class="depth-nav">
          <div class="dn-head"><span>深度导航 / DEPTH</span><span>${fmt(img.top_md, 2)} — ${fmt(img.bottom_md, 2)} m</span></div>
          <div class="depth-track" id="depthTrack"></div>
          <div class="filmstrip" id="filmstrip"></div>
        </div>
      </div>

      <aside class="inspector">
        <div class="meta-hd">
          <h3>${esc(img.code)} · ${TYPE_NAME[img.type] || img.type}</h3>
          <p>${esc(img.region)} · ${esc(img.tectonic)} · 第${img.run_no || "—"}筒</p>
        </div>
        <table class="meta-table">
          <tr><td>井号</td><td>${esc(img.code)} ${esc(img.name)}</td></tr>
          <tr><td>筒次</td><td>第 ${img.run_no || "—"} 筒</td></tr>
          <tr><td>岩心编号</td><td>${esc(img.section_no || "整筒")}</td></tr>
          <tr><td>图像类别</td><td>${TYPE_NAME[img.type] || esc(img.type)}</td></tr>
          <tr><td>起始深度</td><td>${fmt(img.top_md, 2)} m</td></tr>
          <tr><td>终止深度</td><td>${fmt(img.bottom_md, 2)} m</td></tr>
          <tr><td>深度范围</td><td>${fmt(Math.max(0, img.bottom_md - img.top_md), 2)} m</td></tr>
          <tr><td>层位</td><td>${esc(img.layer || "—")}</td></tr>
          <tr><td>岩性</td><td>${esc(img.lithology || "—")}</td></tr>
          <tr><td>比例尺</td><td>${fmt(img.mm_per_px, 3)} mm/px</td></tr>
          <tr><td>采集时间</td><td>${esc(img.captured_at || "—")}</td></tr>
          <tr><td>设备</td><td>${esc(img.device || "—")}</td></tr>
        </table>
        <div class="meta-desc">${esc(img.description || "暂无岩心描述")}</div>
        <div class="anno-block">
          <h4>测量标注 <span style="color:#64748b;font-weight:400" id="annoCount">${d.annotations.length}</span></h4>
          <div id="annoList">${annoListHtml(d.annotations)}</div>
        </div>
      </aside>
    </div>`;

  const stage = document.getElementById("stage");
  const wrap = document.getElementById("imgWrap");
  const imgEl = document.getElementById("mainImg");
  const svg = document.getElementById("annotLayer");
  const scalebar = document.getElementById("scalebar");
  const zoomLabel = document.getElementById("zoomLabel");
  const state = { scale: 1, x: 0, y: 0, fit: 1, min: 0.1, max: 8, measuring: false, p1: null, p2: null, pending: null };

  function apply() {
    wrap.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
    zoomLabel.textContent = Math.round((state.scale / state.fit) * 100) + "%";
    updateScaleBar();
  }

  function fit() {
    const sw = stage.clientWidth, sh = stage.clientHeight;
    const iw = imgEl.naturalWidth || img.width, ih = imgEl.naturalHeight || img.height;
    state.fit = Math.min(sw / iw, sh / ih) * 0.96;
    state.min = state.fit * 0.4;
    state.scale = state.fit;
    state.x = (sw - iw * state.scale) / 2;
    state.y = (sh - ih * state.scale) / 2;
    apply();
  }

  function zoomAt(factor, cx, cy) {
    const sw = stage.clientWidth, sh = stage.clientHeight;
    const px = cx == null ? sw / 2 : cx;
    const py = cy == null ? sh / 2 : cy;
    const next = Math.min(state.max, Math.max(state.min, state.scale * factor));
    const k = next / state.scale;
    state.x = px - (px - state.x) * k;
    state.y = py - (py - state.y) * k;
    state.scale = next;
    apply();
  }

  function updateScaleBar() {
    const mmPerPx = img.mm_per_px || 0.1;
    const targetMm = 10;
    let px = targetMm / mmPerPx;
    let label = "1 cm";
    if (px * state.scale > 180) { px = 5 / mmPerPx; label = "5 mm"; }
    if (px * state.scale < 30) { px = 20 / mmPerPx; label = "2 cm"; }
    scalebar.textContent = label;
    scalebar.style.width = Math.max(20, px * state.scale) + "px";
    scalebar.style.borderBottom = "2px solid #fff";
    scalebar.style.textAlign = "center";
  }

  function renderRuler() {
    const top = img.top_md, bottom = img.bottom_md;
    const range = Math.max(0.01, bottom - top);
    const step = range > 6 ? 0.5 : range > 2 ? 0.2 : 0.1;
    let html = "";
    for (let d = Math.ceil(top / step) * step; d <= bottom + 1e-6; d += step) {
      const p = ((d - top) / range) * 100;
      const major = Math.abs(d / (step * 2) - Math.round(d / (step * 2))) < 1e-6;
      html += `<div class="dtick ${major ? "major" : ""}" style="left:${p}%" data-md="${d.toFixed(2)}">${major ? `<span>${d.toFixed(1)}</span>` : ""}</div>`;
    }
    const track = document.getElementById("depthTrack");
    track.innerHTML = html;
    track.querySelectorAll(".dtick").forEach((t) => t.addEventListener("click", () => {
      const md = parseFloat(t.dataset.md);
      const target = siblings.find((s) => s.type === "SURFACE" && s.top_md <= md && s.bottom_md >= md);
      if (target) go(`#/image/${target.id}`);
    }));
    const thumbs = siblings.filter((s) => s.type === "SURFACE");
    document.getElementById("filmstrip").innerHTML = thumbs.map((s) =>
      `<img src="${s.thumb_url}" data-id="${s.id}" class="${s.id === img.id ? "active" : ""}" title="${fmt(s.top_md, 2)}m">`).join("");
    document.querySelectorAll("#filmstrip img").forEach((im) => im.addEventListener("click", () => go(`#/image/${im.dataset.id}`)));
  }

  function svgText(x, y, text) {
    return `<text x="${x}" y="${y}">${esc(text)}</text>`;
  }

  function drawAnnotations() {
    const w = imgEl.naturalWidth || img.width;
    const h = imgEl.naturalHeight || img.height;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("width", w);
    svg.setAttribute("height", h);
    let s = "";
    (d.annotations || []).forEach((a) => {
      const g = a.geometry || {};
      if (g.x1 == null) return;
      s += `<line x1="${g.x1}" y1="${g.y1}" x2="${g.x2}" y2="${g.y2}"></line>`;
      s += `<circle cx="${g.x1}" cy="${g.y1}" r="4"></circle><circle cx="${g.x2}" cy="${g.y2}" r="4"></circle>`;
      s += svgText((g.x1 + g.x2) / 2 + 6, (g.y1 + g.y2) / 2 - 6, a.label || `${a.value} ${a.unit}`);
    });
    if (state.p1) {
      s += `<circle cx="${state.p1.x}" cy="${state.p1.y}" r="5"></circle>`;
    }
    if (state.pending) {
      const p = state.pending;
      s += `<line x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}"></line>`;
      s += `<circle cx="${p.x1}" cy="${p.y1}" r="4"></circle><circle cx="${p.x2}" cy="${p.y2}" r="4"></circle>`;
      s += svgText((p.x1 + p.x2) / 2 + 6, (p.y1 + p.y2) / 2 - 6, `${p.value} ${p.unit}`);
    }
    svg.innerHTML = s;
  }

  function toImage(e) {
    const r = imgEl.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) / r.width * (imgEl.naturalWidth || img.width),
      y: (e.clientY - r.top) / r.height * (imgEl.naturalHeight || img.height)
    };
  }

  function pick(e) {
    const p = toImage(e);
    if (!state.p1) {
      state.p1 = p; state.pending = null; drawAnnotations();
      return;
    }
    const p1 = state.p1;
    const distPx = Math.hypot(p.x - p1.x, p.y - p1.y);
    const mm = distPx * (img.mm_per_px || 0.1);
    const value = mm >= 1000 ? (mm / 1000).toFixed(2) : mm.toFixed(1);
    const unit = mm >= 1000 ? "m" : "mm";
    state.pending = { x1: p1.x, y1: p1.y, x2: p.x, y2: p.y, value, unit, type: "length" };
    state.p1 = null;
    state.measuring = false;
    stage.classList.remove("measure");
    document.getElementById("measureBtn").classList.remove("active");
    document.getElementById("saveAnno").disabled = false;
    drawAnnotations();
  }

  // pan / zoom
  let drag = null;
  stage.addEventListener("pointerdown", (e) => {
    if (state.measuring) { pick(e); return; }
    drag = { x: e.clientX, y: e.clientY, ox: state.x, oy: state.y };
    stage.classList.add("dragging");
    stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    state.x = drag.ox + (e.clientX - drag.x);
    state.y = drag.oy + (e.clientY - drag.y);
    apply();
  });
  stage.addEventListener("pointerup", () => { drag = null; stage.classList.remove("dragging"); });
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAt(e.deltaY < 0 ? 1.12 : 0.89, e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  document.getElementById("zoomIn").addEventListener("click", () => zoomAt(1.25));
  document.getElementById("zoomOut").addEventListener("click", () => zoomAt(0.8));
  document.getElementById("zoomFit").addEventListener("click", fit);
  document.getElementById("zoomReset").addEventListener("click", () => { fit(); });
  document.getElementById("measureBtn").addEventListener("click", () => {
    state.measuring = !state.measuring;
    state.p1 = null; state.pending = null; drawAnnotations();
    stage.classList.toggle("measure", state.measuring);
    document.getElementById("measureBtn").classList.toggle("active", state.measuring);
  });
  document.getElementById("saveAnno").addEventListener("click", async () => {
    if (!state.pending) return;
    const p = state.pending;
    try {
      await api(`/api/images/${img.id}/annotations`, {
        method: "POST", body: JSON.stringify({
          type: "length", geometry: { x1: p.x1, y1: p.y1, x2: p.x2, y2: p.y2 },
          value: parseFloat(p.value), unit: p.unit, label: `${p.value} ${p.unit}`, author: "admin"
        })
      });
      toast("标注已保存", "ok");
      state.pending = null;
      const nd = await api(`/api/images/${img.id}`);
      d.annotations = nd.annotations;
      document.getElementById("annoList").innerHTML = annoListHtml(d.annotations);
      document.getElementById("annoCount").textContent = d.annotations.length;
      document.getElementById("saveAnno").disabled = true;
      drawAnnotations();
    } catch (e) { toast("保存失败：" + e.message, "error"); }
  });
  document.getElementById("exportImg").addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = img.url; a.download = `${img.code}_${img.type}_${img.id}.jpg`; a.click();
  });
  document.getElementById("backWell").addEventListener("click", () => go(`#/well/${img.well_id}`));
  document.getElementById("prevImg").addEventListener("click", () => d.prev && go(`#/image/${d.prev.id}`));
  document.getElementById("nextImg").addEventListener("click", () => d.next && go(`#/image/${d.next.id}`));
  document.querySelectorAll("#typeTabs [data-type]").forEach((b) => b.addEventListener("click", () => {
    const t = b.dataset.type;
    const s = siblings.find((x) => x.type === t);
    if (s) go(`#/image/${s.id}`);
  }));

  if (imgEl.complete) { fit(); drawAnnotations(); }
  else imgEl.addEventListener("load", () => { fit(); drawAnnotations(); });
  new ResizeObserver(() => { if (imgEl.complete) fit(); }).observe(stage);
  renderRuler();
  updateScaleBar();

  function annoListHtml(list) {
    if (!list.length) return `<div style="color:#64748b;font-size:11px;padding:4px 0">还没有标注；点“测量”后在图上门取两点。</div>`;
    return list.map((a) => `<div class="anno-item"><span>${a.type === "length" ? "长度" : esc(a.type)} · ${esc(a.created_at || "")}</span><b>${a.value} ${esc(a.unit)}</b></div>`).join("");
  }
}

const PALETTE = ["#0e7490", "#2563eb", "#0f9f6e", "#b7791f", "#c2410c", "#7c3aed", "#dc4c64"];
let uid = 0;

function norm(data) {
  return (data || []).map((d) => Array.isArray(d) ? { label: d[0], value: Number(d[1]) || 0 } : { label: d.label, value: Number(d.value) || 0 });
}

function niceMax(v) {
  if (v <= 0) return 1;
  const exp = Math.floor(Math.log10(v));
  const base = Math.pow(10, exp);
  const n = v / base;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * base;
}

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

export function barChart(el, data, opts = {}) {
  if (!el) return;
  const items = norm(data);
  el.innerHTML = "";
  if (!items.length) { el.innerHTML = `<div class="empty">暂无数据</div>`; return; }
  const W = Math.max(240, el.clientWidth || 360);
  const horizontal = !!opts.horizontal;
  const H = opts.height || (horizontal ? Math.max(120, items.length * 30 + 24) : 230);
  const color = opts.color || "#0e7490";
  const color2 = opts.color2 || "#2563eb";
  const suffix = opts.suffix || "";
  const gid = "g" + (++uid);
  const max = niceMax(Math.max(...items.map((d) => d.value)) * 1.08);

  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "none" });
  const defs = svgEl("defs");
  const grad = svgEl("linearGradient", { id: gid, x1: "0", y1: horizontal ? "0" : "1", x2: horizontal ? "1" : "0", y2: "0" });
  grad.appendChild(svgEl("stop", { offset: "0%", "stop-color": color, "stop-opacity": "0.95" }));
  grad.appendChild(svgEl("stop", { offset: "100%", "stop-color": color2, "stop-opacity": "0.45" }));
  defs.appendChild(grad);
  svg.appendChild(defs);

  if (horizontal) {
    const m = { l: opts.labelWidth || 80, r: 48, t: 8, b: 8 };
    const pw = W - m.l - m.r;
    const rowH = (H - m.t - m.b) / items.length;
    items.forEach((d, i) => {
      const y = m.t + i * rowH + rowH * 0.22;
      const bh = Math.max(8, rowH * 0.5);
      const bw = Math.max(1, (d.value / max) * pw);
      const label = svgEl("text", { x: m.l - 8, y: y + bh * 0.72, "text-anchor": "end", class: "lbl" });
      label.textContent = d.label; svg.appendChild(label);
      svg.appendChild(svgEl("rect", { x: m.l, y, width: pw, height: bh, fill: "rgba(15,60,90,.06)", rx: 1 }));
      const rect = svgEl("rect", { x: m.l, y, width: bw, height: bh, fill: `url(#${gid})`, rx: 1, class: "bar" });
      rect.style.cursor = opts.onClick ? "pointer" : "default";
      if (opts.onClick) rect.addEventListener("click", () => opts.onClick(d));
      svg.appendChild(rect);
      const val = svgEl("text", { x: m.l + bw + 7, y: y + bh * 0.75, class: "val" });
      val.textContent = Number(d.value).toLocaleString("en-US") + suffix;
      svg.appendChild(val);
    });
  } else {
    const m = { l: 40, r: 14, t: 16, b: 44 };
    const pw = W - m.l - m.r;
    const ph = H - m.t - m.b;
    for (let i = 0; i <= 4; i++) {
      const y = m.t + (ph / 4) * i;
      svg.appendChild(svgEl("line", { x1: m.l, y1: y, x2: W - m.r, y2: y, class: "grid-line" }));
      const t = svgEl("text", { x: m.l - 6, y: y + 3, "text-anchor": "end", class: "axis" });
      t.textContent = Math.round(max - (max / 4) * i);
      svg.appendChild(t);
    }
    const n = items.length;
    const step = pw / n;
    const bw = Math.min(38, step * 0.52);
    items.forEach((d, i) => {
      const x = m.l + step * i + (step - bw) / 2;
      const bh = Math.max(1, (d.value / max) * ph);
      const y = m.t + ph - bh;
      const rect = svgEl("rect", { x, y, width: bw, height: bh, fill: `url(#${gid})`, rx: 1, class: "bar" });
      rect.style.transformBox = "fill-box";
      rect.style.transformOrigin = "bottom";
      if (opts.onClick) rect.addEventListener("click", () => opts.onClick(d));
      svg.appendChild(rect);
      const val = svgEl("text", { x: x + bw / 2, y: y - 4, "text-anchor": "middle", class: "val" });
      val.textContent = d.value >= 1000 ? (d.value / 1000).toFixed(1) + "k" : d.value;
      svg.appendChild(val);
      const lab = svgEl("text", { x: x + bw / 2, y: m.t + ph + 14, "text-anchor": "end", class: "lbl", transform: `rotate(-28 ${x + bw / 2} ${m.t + ph + 14})` });
      lab.textContent = d.label; svg.appendChild(lab);
    });
  }
  el.appendChild(svg);
}

export function donutChart(el, data, opts = {}) {
  if (!el) return;
  const items = norm(data).filter((d) => d.value > 0);
  const total = items.reduce((s, d) => s + d.value, 0) || 1;
  const colors = opts.colors || PALETTE;
  const size = 160, r = 58, cx = size / 2, cy = size / 2, sw = 16;
  let offset = 0;
  let circles = "";
  items.forEach((d, i) => {
    const frac = d.value / total;
    const len = 2 * Math.PI * r * frac;
    circles += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${colors[i % colors.length]}" stroke-width="${sw}" stroke-dasharray="${len - 2} ${2 * Math.PI * r - len + 2}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})" opacity=".9"></circle>`;
    offset += len;
  });
  const legend = items.map((d, i) => `<div><i style="background:${colors[i % colors.length]}"></i>${d.label}<b style="margin-left:auto;color:#152535">${d.value}</b></div>`).join("");
  el.innerHTML = `<div class="donut-wrap">
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(15,60,90,.08)" stroke-width="${sw}"></circle>
      ${circles}
      <text x="${cx}" y="${cy - 2}" text-anchor="middle" fill="#0e7490" font-size="24" font-family="Bahnschrift, Consolas">${total}</text>
      <text x="${cx}" y="${cy + 16}" text-anchor="middle" fill="#64748b" font-size="10">${opts.centerLabel || "合计"}</text>
    </svg>
    <div class="donut-legend">${legend}</div>
  </div>`;
}

let geoCache = null;

const LON0 = 73, LON1 = 135, LAT0 = 3, LAT1 = 54;
const W = 760, H = 640;

function px(lon) { return ((lon - LON0) / (LON1 - LON0)) * W; }
function py(lat) { return ((LAT1 - lat) / (LAT1 - LAT0)) * H; }

function ringPath(ring) {
  if (!ring || !ring.length) return "";
  return ring.map((p, i) => `${i ? "L" : "M"}${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}`).join("") + "Z";
}

function featurePath(f) {
  const g = f.geometry;
  if (!g) return "";
  if (g.type === "Polygon") return g.coordinates.map(ringPath).join("");
  if (g.type === "MultiPolygon") return g.coordinates.map((poly) => poly.map(ringPath).join("")).join("");
  return "";
}

export async function renderChinaMap(el, points, onSelect) {
  if (!el) return;
  if (!geoCache) {
    geoCache = await fetch("/assets/china.json").then((r) => r.json()).catch(() => null);
  }
  if (!geoCache) {
    el.innerHTML = `<div class="empty">地图数据加载失败</div>`;
    return;
  }
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.innerHTML = `
    <defs>
      <filter id="mapGlow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <linearGradient id="provFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f0f7fc"/>
        <stop offset="100%" stop-color="#e2eff9"/>
      </linearGradient>
    </defs>
    <rect x="0" y="0" width="${W}" height="${H}" fill="transparent"/>
  `;
  const gProv = document.createElementNS(svgNS, "g");
  gProv.setAttribute("filter", "none");
  geoCache.features.forEach((f) => {
    const p = document.createElementNS(svgNS, "path");
    p.setAttribute("d", featurePath(f));
    p.setAttribute("fill", "url(#provFill)");
    p.setAttribute("stroke", "#9fc0d8");
    p.setAttribute("stroke-width", "0.8");
    p.setAttribute("vector-effect", "non-scaling-stroke");
    gProv.appendChild(p);
  });
  svg.appendChild(gProv);

  const labels = [
    ["准噶尔", 87.5, 45.2], ["塔里木", 83.5, 39.6], ["柴达木", 94.5, 37.3],
    ["鄂尔多斯", 108.6, 38.6], ["四川盆地", 104.6, 30.2], ["松辽", 124.5, 45.6],
    ["渤海湾", 118.2, 38.8], ["珠江口", 113.8, 22.2],
  ];
  labels.forEach(([name, lon, lat]) => {
    const t = document.createElementNS(svgNS, "text");
    t.setAttribute("x", px(lon)); t.setAttribute("y", py(lat));
    t.setAttribute("fill", "#64748b");
    t.setAttribute("font-size", "10");
    t.setAttribute("text-anchor", "middle");
    t.setAttribute("letter-spacing", "1");
    t.textContent = name;
    svg.appendChild(t);
  });

  // jitter tight clusters (Sichuan) slightly for readability
  const placed = {};
  (points || []).forEach((p, i) => {
    const key = `${Math.round(p.lon)}_${Math.round(p.lat)}`;
    const n = placed[key] || 0; placed[key] = n + 1;
    const jx = n ? ((n % 3) - 1) * 1.1 : 0;
    const jy = n ? (Math.floor(n / 3) - 0.5) * 0.9 : 0;
    const cx = px(p.lon + jx), cy = py(p.lat + jy);
    const g = document.createElementNS(svgNS, "g");
    g.setAttribute("class", "map-point");
    g.style.cursor = "pointer";
    const pulse = document.createElementNS(svgNS, "circle");
    pulse.setAttribute("cx", cx); pulse.setAttribute("cy", cy); pulse.setAttribute("r", 5);
    pulse.setAttribute("fill", "none");
    pulse.setAttribute("stroke", p.coverage > 70 ? "#0f9f6e" : p.coverage > 0 ? "#b7791f" : "#dc4c64");
    pulse.setAttribute("stroke-width", "1.2");
    pulse.setAttribute("class", "map-pulse");
    pulse.style.animationDelay = (i * 0.18) + "s";
    const dot = document.createElementNS(svgNS, "circle");
    dot.setAttribute("cx", cx); dot.setAttribute("cy", cy); dot.setAttribute("r", 4.2);
    dot.setAttribute("fill", p.coverage > 70 ? "#0f9f6e" : p.coverage > 0 ? "#b7791f" : "#dc4c64");
    dot.setAttribute("stroke", "#ffffff"); dot.setAttribute("stroke-width", "1");
    g.appendChild(pulse); g.appendChild(dot);
    g.addEventListener("mouseenter", (e) => {
      const tip = el.querySelector(".map-tip");
      if (!tip) return;
      tip.innerHTML = `<b>${p.code}</b> ${p.name}<br/>${p.region} · 库存 ${Number(p.inventory).toFixed(2)}m · 覆盖 ${p.coverage}%`;
      tip.style.display = "block";
      const r = el.getBoundingClientRect();
      tip.style.left = Math.min(e.clientX - r.left + 12, r.width - 220) + "px";
      tip.style.top = Math.max(8, e.clientY - r.top - 10) + "px";
    });
    g.addEventListener("mouseleave", () => {
      const tip = el.querySelector(".map-tip");
      if (tip) tip.style.display = "none";
    });
    g.addEventListener("click", () => onSelect && onSelect(p.id));
    svg.appendChild(g);
  });

  el.innerHTML = "";
  el.appendChild(svg);
  const tip = document.createElement("div");
  tip.className = "map-tip";
  el.appendChild(tip);
  const legend = document.createElement("div");
  legend.className = "map-legend";
  legend.innerHTML = `<span><i style="background:#0f9f6e"></i>覆盖率 &gt; 70%</span>
    <span><i style="background:#b7791f"></i>部分扫描</span>
    <span><i style="background:#dc4c64"></i>待扫描</span>
    <span style="color:#64748b">共 ${(points || []).length} 口井 / 点击查看</span>`;
  el.appendChild(legend);
}

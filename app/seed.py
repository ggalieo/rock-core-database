# -*- coding: utf-8 -*-
"""Seed the demo database and generate annotated, photo-based core images."""
import json
import math
import os
import random
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CORE = STATIC / "assets" / "core"
CORE_SRC = STATIC / "assets" / "core_source"
DATA = BASE / "data"
DB_PATH = DATA / "core.db"

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"

def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()

# ---------------------------------------------------------------- data
WELLS = [
    dict(code="BD16", name="板东16", region="克拉玛依", tectonic="克百断裂带", year=2020, type="评价井", lon=84.95, lat=45.60, kb=524.10, ground=520.35, final=4200, inventory=86.40, cuttings=350, sidewall=12, coverage=92, scanned=78.6, status="已扫描", operator="张伟"),
    dict(code="CM1", name="车煤1井", region="准噶尔盆地", tectonic="准噶尔盆地南缘", year=2021, type="探井", lon=87.10, lat=44.80, kb=610.20, ground=606.00, final=3800, inventory=225.20, cuttings=520, sidewall=0, coverage=88, scanned=198.0, status="已扫描", operator="李娜"),
    dict(code="Q11", name="浅11井", region="鄂尔多斯", tectonic="伊陕斜坡", year=2022, type="开发井", lon=108.80, lat=37.60, kb=1320.50, ground=1318.00, final=2600, inventory=21.60, cuttings=180, sidewall=6, coverage=64, scanned=13.8, status="部分扫描", operator="王强"),
    dict(code="G102B", name="广102B井", region="四川盆地", tectonic="川中古隆起", year=2019, type="评价井", lon=105.30, lat=30.40, kb=380.20, ground=376.50, final=5100, inventory=195.30, cuttings=410, sidewall=18, coverage=81, scanned=158.0, status="已扫描", operator="赵磊"),
    dict(code="AP1", name="安平1", region="四川盆地", tectonic="安岳气田", year=2023, type="开发井", lon=105.45, lat=30.15, kb=365.40, ground=362.00, final=4800, inventory=41.70, cuttings=120, sidewall=4, coverage=55, scanned=23.0, status="部分扫描", operator="陈静"),
    dict(code="TX1", name="天西1", region="四川盆地", tectonic="川西坳陷", year=2021, type="探井", lon=103.80, lat=30.70, kb=720.00, ground=716.20, final=4600, inventory=68.02, cuttings=210, sidewall=0, coverage=47, scanned=32.0, status="部分扫描", operator="刘洋"),
    dict(code="Y101", name="岳101-3C1", region="四川盆地", tectonic="安岳气田", year=2022, type="开发井", lon=105.38, lat=30.22, kb=372.10, ground=368.80, final=4700, inventory=42.45, cuttings=96, sidewall=0, coverage=72, scanned=30.5, status="已扫描", operator="周敏"),
    dict(code="AY1", name="安岳1", region="四川盆地", tectonic="安岳气田", year=2023, type="评价井", lon=105.50, lat=30.18, kb=368.00, ground=364.50, final=4900, inventory=51.70, cuttings=140, sidewall=8, coverage=69, scanned=35.7, status="已扫描", operator="杨帆"),
    dict(code="Y102", name="岳102", region="四川盆地", tectonic="安岳气田", year=2022, type="开发井", lon=105.42, lat=30.26, kb=370.50, ground=367.00, final=4650, inventory=23.60, cuttings=75, sidewall=0, coverage=58, scanned=13.7, status="部分扫描", operator="何平"),
    dict(code="Y104", name="岳104", region="四川盆地", tectonic="安岳气田", year=2021, type="开发井", lon=105.35, lat=30.12, kb=376.20, ground=372.80, final=4550, inventory=164.30, cuttings=300, sidewall=10, coverage=85, scanned=139.6, status="已扫描", operator="罗刚"),
    dict(code="Y105", name="岳105", region="四川盆地", tectonic="安岳气田", year=2020, type="开发井", lon=105.47, lat=30.30, kb=366.80, ground=363.40, final=4500, inventory=18.20, cuttings=60, sidewall=0, coverage=41, scanned=7.5, status="部分扫描", operator="邓超"),
    dict(code="Y107", name="岳107", region="四川盆地", tectonic="安岳气田", year=2024, type="开发井", lon=105.52, lat=30.08, kb=374.40, ground=371.00, final=4600, inventory=7.10, cuttings=20, sidewall=0, coverage=18, scanned=1.3, status="待扫描", operator="谢婷"),
    dict(code="Y110", name="岳110", region="四川盆地", tectonic="安岳气田", year=2024, type="开发井", lon=105.55, lat=30.33, kb=369.90, ground=366.50, final=4580, inventory=2.50, cuttings=8, sidewall=0, coverage=0, scanned=0.0, status="待扫描", operator="王磊"),
    dict(code="Y111", name="岳111", region="四川盆地", tectonic="安岳气田", year=2024, type="开发井", lon=105.60, lat=30.05, kb=371.20, ground=367.80, final=4620, inventory=9.11, cuttings=24, sidewall=0, coverage=22, scanned=2.0, status="待扫描", operator="孙悦"),
    dict(code="Y112", name="岳112", region="四川盆地", tectonic="安岳气田", year=2024, type="开发井", lon=105.58, lat=30.20, kb=373.10, ground=369.70, final=4590, inventory=5.60, cuttings=0, sidewall=0, coverage=0, scanned=0.0, status="待扫描", operator="马超"),
]

BASE_DEPTH = {"BD16": 3943.0, "CM1": 2150.0, "Q11": 262.0, "G102B": 2032.0,
              "AP1": 1850.0, "TX1": 3200.0, "Y101": 2400.0, "AY1": 2300.0,
              "Y102": 2500.0, "Y104": 2800.0, "Y105": 2600.0, "Y107": 2700.0,
              "Y110": 2900.0, "Y111": 3000.0, "Y112": 3100.0}
RUN_COUNT = {"BD16": 4, "CM1": 2, "Q11": 2, "G102B": 2}

LAYERS = {
    "BD16": ("石炭系", "上石炭统", "巴塔玛依内山组"),
    "CM1": ("侏罗系", "下侏罗统", "八道湾组"),
    "Q11": ("二叠系", "下二叠统", "山西组"),
    "G102B": ("震旦系", "上震旦统", "灯影组"),
    "AP1": ("二叠系", "中二叠统", "茅口组"),
    "TX1": ("三叠系", "上三叠统", "须家河组"),
}
DEFAULT_LAYER = ("二叠系", "中二叠统", "茅口组")

LITH = {
    "BD16": ("细砂岩", "#b9a06a", "sand"),
    "CM1": ("砂砾岩", "#8d7b63", "congl"),
    "Q11": ("泥岩", "#6f7b78", "mud"),
    "G102B": ("白云岩", "#9fb3b8", "lime"),
    "AP1": ("灰岩", "#b9b6a4", "lime"),
    "TX1": ("细砂岩", "#b9a06a", "sand"),
    "Y101": ("中砂岩", "#c4ad78", "sand"),
    "AY1": ("细砂岩", "#b9a06a", "sand"),
    "Y102": ("泥质粉砂岩", "#8b8f7a", "mud"),
    "Y104": ("砂砾岩", "#8d7b63", "congl"),
    "Y105": ("灰岩", "#b9b6a4", "lime"),
    "Y107": ("泥岩", "#6f7b78", "mud"),
    "Y110": ("细砂岩", "#b9a06a", "sand"),
    "Y111": ("粉砂岩", "#a8a07a", "sand"),
    "Y112": ("泥岩", "#6f7b78", "mud"),
}

DESC = {
    "sand": "灰白色细砂岩，平行层理，颗粒支撑，孔隙式胶结，含油斑，局部见黄铁矿结核。",
    "mud": "深灰色泥岩，块状构造，性较脆，见水平层理，局部含粉砂质条带。",
    "lime": "浅灰色灰岩，块状构造，致密，见方解石脉及溶蚀孔洞，局部充填沥青。",
    "congl": "杂色砂砾岩，砾石成分以变质岩为主，次圆状，分选中等，砂质充填。",
}

TEMPLATES = [("COLUMN", "综合柱状图"), ("MULTI", "多井对比"), ("IMAGE", "岩心图像"),
             ("FLUOR", "荧光图像"), ("EXP", "实验分析"), ("STOCK", "库存")]

# ---------------------------------------------------------------- image generation
def _texture(w, h, seed, palette):
    r = random.Random(seed)
    img = Image.new("RGB", (w, h), palette[0])
    d = ImageDraw.Draw(img)
    y = 0
    while y < h:
        bh = r.randint(8, 34)
        c = r.choice(palette)
        pts = [(0, y)]
        for x in range(0, w + 1, 36):
            pts.append((x, y + r.randint(-3, 3)))
        pts += [(w, y + bh), (0, y + bh)]
        d.polygon(pts, fill=c)
        y += bh
    for _ in range(max(1200, w * h // 38)):
        x, yy = r.randrange(w), r.randrange(h)
        c = palette[r.randrange(len(palette))]
        rr = r.randint(1, 3)
        cc = tuple(min(255, max(0, v + r.randint(-22, 22))) for v in c)
        d.ellipse([x, yy, x + rr, yy + rr], fill=cc)
    for _ in range(r.randint(3, 7)):
        x, yy = r.randrange(w), r.randrange(h)
        pts = [(x, yy)]
        for _ in range(r.randint(3, 8)):
            x += r.randint(-28, 28)
            yy += r.randint(10, 38)
            pts.append((x, yy))
        d.line(pts, fill=(38, 34, 29), width=r.randint(1, 3))
    for _ in range(r.randint(2, 6)):
        x, yy = r.randrange(w), r.randrange(h)
        rr = r.randint(3, 9)
        d.ellipse([x, yy, x + rr, yy + rr], fill=(28, 26, 23))
    return img.filter(ImageFilter.GaussianBlur(0.35))


def _label_box(d, text, xy=(14, 14), fg=(35, 31, 26), bg=(246, 243, 233), size=15):
    f = font(size)
    tw = d.textlength(text, font=f)
    x, y = xy
    d.rectangle([x, y, x + tw + 16, y + size + 12], fill=bg, outline=(80, 72, 60))
    d.text((x + 8, y + 5), text, font=f, fill=fg)


def make_surface(w, h, seed, palette, label):
    img = _texture(w, h, seed, palette)
    d = ImageDraw.Draw(img)
    _label_box(d, label)
    # scale bar 1 cm
    x0, y0 = w - 160, h - 34
    d.rectangle([x0 - 6, y0 - 6, x0 + 110, y0 + 10], fill=(245, 242, 232))
    d.line([x0, y0, x0 + 96, y0], fill=(20, 20, 20), width=4)
    d.line([x0, y0 - 5, x0, y0 + 5], fill=(20, 20, 20), width=2)
    d.line([x0 + 96, y0 - 5, x0 + 96, y0 + 5], fill=(20, 20, 20), width=2)
    d.text((x0 + 28, y0 - 22), "1 cm", font=font(13), fill=(20, 20, 20))
    # color card
    for i, c in enumerate([(220, 220, 220), (180, 60, 50), (60, 120, 70), (50, 70, 140)]):
        d.rectangle([16 + i * 22, h - 34, 32 + i * 22, h - 18], fill=c, outline=(30, 30, 30))
    d.text((16, h - 52), "COLOR", font=font(9), fill=(240, 240, 240))
    return img


def make_rolled(w, h, seed, palette, label):
    img = _texture(w, h, seed, palette)
    d = ImageDraw.Draw(img)
    _label_box(d, label)
    for x in (int(w * 0.34), int(w * 0.67)):
        d.line([(x, 0), (x, h)], fill=(35, 30, 26), width=3)
        d.line([(x + 4, 0), (x + 4, h)], fill=(220, 210, 190), width=1)
    d.line([(20, h - 18), (w - 20, h - 18)], fill=(240, 230, 200), width=1)
    d.text((20, h - 34), "滚动展开 / 拼接方向 →", font=font(12), fill=(240, 230, 200))
    return img


def make_fluoro(w, h, seed, palette, label):
    r = random.Random(seed)
    glow = Image.new("RGB", (w, h), (2, 4, 6))
    d = ImageDraw.Draw(glow)
    for _ in range(r.randint(90, 160)):
        x, y = r.randrange(w), r.randrange(h)
        rx, ry = r.randint(4, 26), r.randint(3, 14)
        c = r.choice([(0, 240, 190), (255, 215, 70), (80, 170, 255), (190, 255, 120)])
        d.ellipse([x, y, x + rx, y + ry], fill=c)
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img = Image.blend(Image.new("RGB", (w, h), (2, 5, 8)), glow, 0.88)
    d = ImageDraw.Draw(img)
    if label:
        _label_box(d, label, fg=(210, 250, 255), bg=(4, 18, 24), size=15)
    d.text((20, h - 30), "UV 365nm", font=font(13), fill=(0, 240, 220))
    return img


def make_box(w, h, seed, palette, label):
    img = Image.new("RGB", (w, h), (12, 16, 20))
    d = ImageDraw.Draw(img)
    _label_box(d, label, fg=(240, 240, 240), bg=(18, 24, 30), size=16)
    r = random.Random(seed)
    for i in range(5):
        x = 24 + i * (w - 48) / 5
        pw = (w - 60) / 5 - 8
        tex = _texture(int(pw), 110, seed + i * 7, palette)
        img.paste(tex, (int(x), 120))
        d.rectangle([x, 120, x + pw, 230], outline=(80, 90, 100), width=2)
        d.text((x + 6, 238), f"{i+1}", font=font(12), fill=(200, 220, 240))
    d.text((24, h - 40), "岩心箱编号：001    格位：1—5", font=font(13), fill=(190, 215, 240))
    return img


def make_thin(w, h, seed, palette):
    r = random.Random(seed)
    img = Image.new("RGB", (w, h), (28, 26, 30))
    d = ImageDraw.Draw(img)
    for _ in range(150):
        cx, cy = r.randrange(w), r.randrange(h)
        rad = r.randint(14, 46)
        pts = []
        for k in range(r.randint(5, 8)):
            a = 2 * math.pi * k / 7 + r.random() * 0.4
            rr = rad * (0.6 + r.random() * 0.6)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        c = r.choice([(210, 190, 160), (180, 200, 220), (220, 210, 190), (160, 180, 150), (200, 170, 200)])
        d.polygon(pts, fill=c, outline=(35, 32, 30), width=2)
    d.text((16, 16), "薄片 单偏光 + 正交偏光", font=font(14), fill=(240, 240, 240))
    return img


def make_strip(w, h, seed, palette):
    img = _texture(w, h, seed, palette)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(20, 25, 30), width=2)
    return img



# ---------------------------------------------------------------- photo-based core images
_SOURCE_CACHE = {}
SOURCE_BY_LITH = {
    "sand": ["dolostone.jpg", "onkalo_1.jpg"],
    "mud": ["onkalo_2.jpg", "drill_core.jpg"],
    "lime": ["dolostone.jpg", "onkalo_1.jpg"],
    "congl": ["drill_core.jpg", "onkalo_2.jpg"],
}


def _source(name):
    if name in _SOURCE_CACHE:
        return _SOURCE_CACHE[name].copy()
    path = CORE_SRC / name
    if not path.exists():
        return None
    img = Image.open(path).convert("RGB")
    _SOURCE_CACHE[name] = img
    return img.copy()


def _band(name, seed, w, h):
    """Crop a realistic strip from a core-box photo, preserving scale."""
    src = _source(name)
    if src is None:
        return _texture(w, h, seed, [(150, 140, 120), (110, 105, 92)])
    rng = random.Random(seed)
    target = w / h
    crop_h = min(src.height, max(120, int(src.width / target)))
    y = rng.randint(0, max(0, src.height - crop_h))
    crop = src.crop((0, y, src.width, y + crop_h))
    if rng.random() < 0.45:
        crop = ImageOps.mirror(crop)
    crop = crop.resize((w, h), Image.Resampling.LANCZOS)
    crop = ImageEnhance.Contrast(crop).enhance(rng.uniform(1.02, 1.12))
    crop = ImageEnhance.Color(crop).enhance(rng.uniform(0.95, 1.08))
    return crop


def _fit(name, seed, w, h):
    src = _source(name)
    if src is None:
        return _texture(w, h, seed, [(150, 140, 120), (110, 105, 92)])
    rng = random.Random(seed)
    target = w / h
    sw, sh = src.size
    if sw / sh > target:
        cw = int(sh * target)
        x = rng.randint(0, max(0, sw - cw))
        box = (x, 0, x + cw, sh)
    else:
        ch = int(sw / target)
        y = rng.randint(0, max(0, sh - ch))
        box = (0, y, sw, y + ch)
    return src.crop(box).resize((w, h), Image.Resampling.LANCZOS)


def _pill(d, xy, text, f, fg=(255, 255, 255), bg=(0, 150, 210), pad=(7, 3)):
    b = d.textbbox((0, 0), text, font=f)
    tw, th = b[2] - b[0], b[3] - b[1]
    x, y = xy
    d.rounded_rectangle([x, y, x + tw + pad[0] * 2, y + th + pad[1] * 2 + 2],
                        radius=4, fill=bg)
    d.text((x + pad[0], y + pad[1] - 1), text, font=f, fill=fg)
    return tw + pad[0] * 2


def _annotate(img, code, run_no, section_no, top, bottom, seed, uv=False):
    """Mimic a field core-box photo with blue interval boxes and depth chips."""
    rng = random.Random(seed + 99)
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f10 = font(10)
    f11 = font(11)
    f12 = font(12, True)
    blue = (0, 170, 230, 245)
    cyan = (0, 235, 220, 235) if uv else blue
    yellow = (255, 207, 64, 230)

    # Three core rows, each with a blue running interval box.
    rows = 3
    top_pad = 20
    bottom_pad = 26
    row_h = (H - top_pad - bottom_pad) // rows
    for i in range(rows):
        y0 = top_pad + i * row_h + 2
        y1 = top_pad + (i + 1) * row_h - 3
        d.rounded_rectangle([6, y0, W - 6, y1], radius=4, outline=cyan, width=2)
        # a yellow inner marker like a selected core piece
        x0 = int(W * rng.uniform(0.18, 0.35))
        x1 = int(W * rng.uniform(0.55, 0.78))
        d.line([(x0, y1 - 3), (x1, y1 - 3)], fill=yellow, width=2)
        if rng.random() < 0.6:
            d.rounded_rectangle([x0, y0 + 4, x1, y1 - 5], radius=3,
                                outline=(255, 255, 255, 120), width=1)
        # depth pill at the left edge of every row
        dep = top + (bottom - top) * (i + 0.5) / rows
        _pill(d, (9, y0 + 3), f"{dep:.2f}", f10, fg=(255, 255, 255), bg=cyan)

    # Boundary depth labels, like numbers painted on the core box.
    for i in range(rows + 1):
        y = top_pad + i * row_h
        dep = top + (bottom - top) * i / rows
        d.line([(W - 118, y), (W - 8, y)], fill=(255, 255, 255, 210), width=1)
        _pill(d, (W - 112, y + 2), f"{dep:.2f}", f10, fg=(15, 45, 60),
              bg=(245, 247, 242, 225))
        d.text((W - 68, y + 4), "m", font=f10, fill=(245, 245, 245))

    # Small field label, deliberately unobtrusive.
    label = f"{code}  第{run_no}筒  {section_no}  {top:.2f}-{bottom:.2f}m"
    _pill(d, (12, 5), label, f11, fg=(255, 255, 255), bg=(6, 43, 62, 220))
    if uv:
        _pill(d, (W - 96, 5), "UV 365nm", f10, fg=(0, 250, 220), bg=(2, 20, 28, 225))

    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def make_real_surface(w, h, seed, source, label, top, bottom, code, run_no, section_no):
    return _annotate(_band(source, seed, w, h), code, run_no, section_no, top, bottom, seed)


def make_real_rolled(w, h, seed, source, top, bottom, code, run_no):
    img = _band(source, seed, w, h)
    d = ImageDraw.Draw(img)
    for x in (int(w * 0.34), int(w * 0.67)):
        d.line([(x, 0), (x, h)], fill=(230, 235, 235), width=2)
        d.line([(x + 3, 0), (x + 3, h)], fill=(30, 35, 38), width=1)
    return _annotate(img, code, run_no, "展开", top, bottom, seed)


def make_real_fluoro(w, h, seed, source, top, bottom, code, run_no, section_no):
    base = _band(source, seed, w, h).convert("RGB")
    # Dark UV base with a cyan cast; add plausible hydrocarbon fluorescence.
    dark = ImageEnhance.Brightness(base).enhance(0.28)
    blue = Image.new("RGB", (w, h), (2, 18, 30))
    img = Image.blend(dark, blue, 0.45)
    rng = random.Random(seed + 31)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    for _ in range(rng.randint(110, 190)):
        x, y = rng.randrange(w), rng.randrange(h)
        rx, ry = rng.randint(4, 22), rng.randint(2, 10)
        c = rng.choice([(0, 235, 175), (250, 220, 80), (40, 180, 255), (180, 255, 90)])
        d.ellipse([x, y, x + rx, y + ry], fill=c)
    glow = glow.filter(ImageFilter.GaussianBlur(5))
    img = Image.blend(img, glow, 0.58)
    return _annotate(img, code, run_no, section_no, top, bottom, seed, uv=True)


def make_real_box(w, h, seed, source, label, code):
    img = _fit(source, seed, w, h)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(8, 38, 55), width=4)
    _pill(d, (14, 12), label, font(15, True), fg=(255, 255, 255), bg=(8, 48, 68))
    _pill(d, (w - 126, h - 34), "岩心箱 / BOX 001", font(10), fg=(255, 255, 255),
          bg=(8, 48, 68))
    return img


def make_real_thin(w, h, seed, label):
    img = _fit("thin_section.jpg", seed, w, h)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(245, 245, 245), width=2)
    _pill(d, (14, 12), label, font(12, True), fg=(255, 255, 255), bg=(20, 24, 30))
    x0, y0 = 20, h - 30
    d.line([(x0, y0), (x0 + 120, y0)], fill=(255, 255, 255), width=4)
    d.text((x0 + 40, y0 - 18), "0.5 mm", font=font(11), fill=(255, 255, 255))
    return img


def make_real_strip(w, h, seed, source):
    return _band(source, seed, w, h)


# ---------------------------------------------------------------- db
SCHEMA = """
PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS annotations;
DROP TABLE IF EXISTS txns;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS scans;
DROP TABLE IF EXISTS experiments;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS sections;
DROP TABLE IF EXISTS strata;
DROP TABLE IF EXISTS runs;
DROP TABLE IF EXISTS wells;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS audit;
DROP TABLE IF EXISTS meta;

CREATE TABLE wells (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE, name TEXT, region TEXT, tectonic TEXT, year INTEGER, type TEXT,
  lon REAL, lat REAL, kb REAL, ground REAL, final_depth REAL,
  inventory REAL, cuttings INTEGER, sidewall INTEGER, coverage REAL, scanned REAL,
  status TEXT, operator TEXT, updated_at TEXT
);
CREATE TABLE runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, run_no INTEGER, top_md REAL, bottom_md REAL,
  footage REAL, core_length REAL, recovery REAL, layer TEXT, lithology TEXT,
  description TEXT, drilled_at TEXT
);
CREATE TABLE strata (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, run_id INTEGER, name TEXT, level TEXT, top_md REAL, bottom_md REAL, color TEXT
);
CREATE TABLE sections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER, well_id INTEGER, section_no TEXT, top_md REAL, bottom_md REAL,
  length REAL, box_no TEXT, slot TEXT, condition TEXT, oil_show TEXT, fluorescence TEXT,
  rqd REAL, lithology TEXT, color TEXT, pattern TEXT, description TEXT, strip_file TEXT
);
CREATE TABLE images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, run_id INTEGER, section_id INTEGER, type TEXT, light TEXT,
  top_md REAL, bottom_md REAL, file TEXT, thumb TEXT, width INTEGER, height INTEGER,
  dpi INTEGER, mm_per_px REAL, captured_at TEXT, device TEXT, operator TEXT, quality TEXT
);
CREATE TABLE experiments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, sample_code TEXT, sample_type TEXT, top_md REAL, bottom_md REAL,
  test_type TEXT, param TEXT, value REAL, unit TEXT, lab TEXT, test_date TEXT
);
CREATE TABLE scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, run_no INTEGER, top_md REAL, bottom_md REAL, type TEXT,
  images_count INTEGER, scanned_at TEXT, operator TEXT, status TEXT
);
CREATE TABLE products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, code TEXT, name TEXT, status TEXT, updated_at TEXT
);
CREATE TABLE inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, section_id INTEGER, location TEXT, quantity REAL, unit TEXT,
  status TEXT, updated_at TEXT
);
CREATE TABLE txns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id INTEGER, section_id INTEGER, txn_type TEXT, quantity REAL, unit TEXT,
  from_loc TEXT, to_loc TEXT, operator TEXT, txn_time TEXT, reason TEXT
);
CREATE TABLE annotations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER, type TEXT, geometry TEXT, value REAL, unit TEXT,
  label TEXT, author TEXT, created_at TEXT
);
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, account TEXT, role TEXT, org TEXT, last_login TEXT
);
CREATE TABLE audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, target TEXT, created_at TEXT
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""


def main():
    if DATA.exists():
        pass
    DATA.mkdir(parents=True, exist_ok=True)
    if CORE.exists():
        shutil.rmtree(CORE)
    CORE.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    for i, w in enumerate(WELLS):
        conn.execute("""INSERT INTO wells(code,name,region,tectonic,year,type,lon,lat,kb,ground,final_depth,
            inventory,cuttings,sidewall,coverage,scanned,status,operator,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (w["code"], w["name"], w["region"], w["tectonic"], w["year"], w["type"], w["lon"], w["lat"],
             w["kb"], w["ground"], w["final"], w["inventory"], w["cuttings"], w["sidewall"],
             w["coverage"], w["scanned"], w["status"], w["operator"],
             (datetime(2026, 11, 15) - timedelta(days=i)).strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    well_ids = {r["code"]: r["id"] for r in conn.execute("SELECT id,code FROM wells")}

    # runs / sections / strata
    for wi, w in enumerate(WELLS):
        code = w["code"]
        base = BASE_DEPTH[code]
        n_runs = RUN_COUNT.get(code, 1)
        lith, color, pattern = LITH[code]
        layer = LAYERS.get(code, DEFAULT_LAYER)
        for run_no in range(1, n_runs + 1):
            top = base + (run_no - 1) * 9.0
            bottom = top + 9.0
            if code == "BD16" and run_no == 1:
                recovery, lengths = 0.80, [1.20, 1.50, 2.00, 1.30, 1.20]
            else:
                recovery = round(0.78 + ((wi * 7 + run_no * 3) % 15) / 100.0, 2)
                core = round(9.0 * recovery, 2)
                lengths = [round(core * 0.34, 2), round(core * 0.33, 2)]
                lengths.append(round(core - sum(lengths), 2))
            core_length = round(sum(lengths), 2)
            desc = DESC[pattern]
            cur = conn.execute("""INSERT INTO runs(well_id,run_no,top_md,bottom_md,footage,core_length,recovery,
                layer,lithology,description,drilled_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (well_ids[code], run_no, top, bottom, 9.0, core_length, recovery,
                 " / ".join(layer), lith, desc,
                 (datetime(2020, 3, 1) + timedelta(days=wi * 30 + run_no * 5)).strftime("%Y-%m-%d")))
            run_id = cur.lastrowid
            for k, (nm, lv, c) in enumerate(zip(layer, ["界/系", "统", "组"], ["#2f5597", "#4472c4", "#8faadc"])):
                s_top = top + k * 3.0
                s_bottom = top + (k + 1) * 3.0 if k < 2 else bottom
                conn.execute("INSERT INTO strata(well_id,run_id,name,level,top_md,bottom_md,color) VALUES(?,?,?,?,?,?,?)",
                             (well_ids[code], run_id, nm, lv, s_top, s_bottom, c))
            cum = 0.0
            for si, ln in enumerate(lengths, start=1):
                s_top = round(top + cum / recovery, 3)
                s_bottom = round(top + (cum + ln) / recovery, 3)
                oil = "油斑" if pattern == "sand" and (si + run_no) % 3 else ("油浸" if pattern == "sand" and si == 1 else "不含油")
                flu = "3级" if oil != "不含油" else "无"
                rqd = round(52 + ((wi * 11 + run_no * 7 + si * 5) % 42), 0)
                box_no = f"{(run_no - 1) * 2 + (si + 2) // 3 + 1:03d}"
                cur2 = conn.execute("""INSERT INTO sections(run_id,well_id,section_no,top_md,bottom_md,length,box_no,slot,
                    condition,oil_show,fluorescence,rqd,lithology,color,pattern,description)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, well_ids[code], f"{run_no}-{si:02d}", s_top, s_bottom, ln, box_no,
                     str(si), "完整" if si % 4 else "破碎", oil, flu, rqd, lith, color, pattern, desc))
                conn.execute("INSERT INTO images(well_id,run_id,section_id,type,light,top_md,bottom_md,file,thumb,width,height,dpi,mm_per_px,captured_at,device,operator,quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (well_ids[code], run_id, cur2.lastrowid, "SURFACE", "WHITE", s_top, s_bottom,
                              "", "", 960, 340, 300, 0.10,
                              (datetime(2026, 10, 10) + timedelta(days=wi * 2 + run_no)).strftime("%Y-%m-%d %H:%M"),
                              "CoreScan-1200", w["operator"], "OK"))
                cum += ln
            # rolled + fluorescence per run
            for typ, light, ww, hh in [("ROLLED", "WHITE", 1500, 300), ("FLUORESCENCE", "UV", 960, 340)]:
                conn.execute("INSERT INTO images(well_id,run_id,section_id,type,light,top_md,bottom_md,file,thumb,width,height,dpi,mm_per_px,captured_at,device,operator,quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (well_ids[code], run_id, None, typ, light, top, bottom, "", "", ww, hh, 300, 0.09,
                              (datetime(2026, 10, 10) + timedelta(days=wi * 2 + run_no)).strftime("%Y-%m-%d %H:%M"),
                              "CoreScan-1200", w["operator"], "OK"))
        # box / thin section
        if code in ("BD16", "CM1", "Q11", "G102B"):
            conn.execute("INSERT INTO images(well_id,run_id,section_id,type,light,top_md,bottom_md,file,thumb,width,height,dpi,mm_per_px,captured_at,device,operator,quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (well_ids[code], None, None, "BOX", "WHITE", base, base + 9, "", "", 900, 480, 300, 0.12,
                          "2026-10-20 10:00", "CoreScan-1200", w["operator"], "OK"))
        if code in ("BD16", "G102B"):
            conn.execute("INSERT INTO images(well_id,run_id,section_id,type,light,top_md,bottom_md,file,thumb,width,height,dpi,mm_per_px,captured_at,device,operator,quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (well_ids[code], None, None, "THIN_SECTION", "XP", base + 0.5, base + 0.6, "", "", 600, 600, 300, 0.02,
                          "2026-10-21 15:00", "Axio Scope", w["operator"], "OK"))
    conn.commit()

    # experiments
    exp_defs = [("孔隙度", "POROSITY", 0.0, "%"), ("渗透率", "PERM", 0.0, "mD"),
                ("含水饱和度", "SW", 0.0, "%"), ("粒度中值", "D50", 0.0, "mm"),
                ("碳酸盐含量", "CARB", 0.0, "%"), ("有机碳", "TOC", 0.0, "%")]
    for wi, w in enumerate(WELLS):
        base = BASE_DEPTH[w["code"]]
        vals = [12.5 + wi * 0.7, 3.2 + wi * 0.6, 45 + wi * 1.2, 0.15 + wi * 0.005, 12 + wi * 0.8, 1.2 + wi * 0.05]
        for k, ((nm, code, _, unit), v) in enumerate(zip(exp_defs, vals)):
            conn.execute("""INSERT INTO experiments(well_id,sample_code,sample_type,top_md,bottom_md,test_type,param,value,unit,lab,test_date)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (well_ids[w["code"]], f"{w['code']}-1-01", "柱塞", base + 0.5, base + 0.6, nm, code,
                 round(v, 2), unit, "勘探开发研究院岩心分析实验室", "2026-10-18"))

    # scans
    for wi, w in enumerate(WELLS):
        if w["coverage"] <= 0:
            continue
        base = BASE_DEPTH[w["code"]]
        conn.execute("""INSERT INTO scans(well_id,run_no,top_md,bottom_md,type,images_count,scanned_at,operator,status)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (well_ids[w["code"]], 1, base, base + 9, "外表皮 + 展开", max(3, int(w["coverage"] / 8)),
             (datetime(2026, 11, 15, 11, 12) - timedelta(days=wi, hours=wi * 2)).strftime("%Y-%m-%d %H:%M"),
             w["operator"], "已完成"))

    # products
    for wi, w in enumerate(WELLS):
        has_img = w["coverage"] > 0
        for code, name in TEMPLATES:
            status = "done"
            if code == "MULTI" and wi % 3 == 0:
                status = "none"
            if code == "IMAGE" and not has_img:
                status = "none"
            if code == "FLUOR" and not has_img:
                status = "none"
            if code == "STOCK" and w["inventory"] <= 0:
                status = "none"
            conn.execute("INSERT INTO products(well_id,code,name,status,updated_at) VALUES(?,?,?,?,?)",
                         (well_ids[w["code"]], code, name, status,
                          (datetime(2026, 11, 15) - timedelta(days=wi)).strftime("%Y-%m-%d %H:%M")))

    # inventory + txns
    inv_count = 0
    for wi, w in enumerate(WELLS):
        for s in conn.execute("SELECT * FROM sections WHERE well_id=? ORDER BY id LIMIT 3", (well_ids[w["code"]],)):
            loc = f"{1 + wi % 3}号库-{1 + wi % 4}排-{1 + wi % 5}架-{s['box_no']}箱-{s['slot']}格"
            status = "在库"
            if w["code"] == "Y107" and s["section_no"].endswith("02"):
                status = "借出"
            if w["code"] == "Y110" and s["section_no"].endswith("03"):
                status = "损耗"
            conn.execute("INSERT INTO inventory(well_id,section_id,location,quantity,unit,status,updated_at) VALUES(?,?,?,?,?,?,?)",
                         (well_ids[w["code"]], s["id"], loc, s["length"], "m", status, "2026-11-15"))
            inv_count += 1
            if inv_count <= 8:
                conn.execute("INSERT INTO txns(well_id,section_id,txn_type,quantity,unit,from_loc,to_loc,operator,txn_time,reason) VALUES(?,?,?,?,?,?,?,?,?,?)",
                             (well_ids[w["code"]], s["id"], "入库", s["length"], "m", "", loc, "张伟",
                              "2026-10-20 09:30", "岩心整理入库"))
    for code, typ, qty, reason in [("BD16", "借阅", 1.2, "薄片取样"), ("CM1", "移库", 2.4, "库房调整"),
                                   ("G102B", "取样", 0.3, "物性分析"), ("Y104", "损耗", 0.1, "搬运破损")]:
        s = conn.execute("SELECT * FROM sections WHERE well_id=? ORDER BY id LIMIT 1", (well_ids[code],)).fetchone()
        if s:
            conn.execute("INSERT INTO txns(well_id,section_id,txn_type,quantity,unit,from_loc,to_loc,operator,txn_time,reason) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (well_ids[code], s["id"], typ, qty, "m", "1号库", "2号库", "李娜",
                          "2026-11-10 14:00", reason))

    # users / audit / meta
    users = [("系统管理员", "admin", "系统管理员", "信息中心", "2026-11-16 08:40"),
             ("张伟", "zhangwei", "数据管理员", "岩心库", "2026-11-16 08:32"),
             ("李娜", "lina", "地质人员", "勘探开发研究院", "2026-11-15 17:20"),
             ("王强", "wangqiang", "录入员", "岩心库", "2026-11-15 16:05"),
             ("陈静", "chenjing", "借阅者", "勘探开发研究院", "2026-11-14 09:10")]
    for u in users:
        conn.execute("INSERT INTO users(name,account,role,org,last_login) VALUES(?,?,?,?,?)", u)
    for a in [("张伟", "导入影像", "BD16 / 第1筒", "2026-11-15 10:12"),
              ("李娜", "查询井", "板东16", "2026-11-15 09:48"),
              ("王强", "修改岩心段", "CM1 / 1-02", "2026-11-14 16:30"),
              ("陈静", "申请借阅", "BD16 / 1-01", "2026-11-14 10:02"),
              ("admin", "新增用户", "王强", "2026-11-13 15:20")]:
        conn.execute("INSERT INTO audit(user,action,target,created_at) VALUES(?,?,?,?)", a)

    meta = {
        "total_wells": "386", "inventory_m": "8650.40", "cuttings_bags": "1280",
        "sidewall_pcs": "96", "coverage": "78.0", "scanned_m": "6745.0",
        "images": "12840", "today_scans": "6", "updated_at": "2026-11-16 08:45",
        "cuttings_by_region": json.dumps([["克拉玛依", 3400], ["青海", 1800], ["华北", 1100], ["长庆", 600], ["塔里木", 450], ["西南", 350]], ensure_ascii=False),
        "inventory_by_region": json.dumps([["克拉玛依", 3200], ["鄂尔多斯", 2100], ["四川盆地", 1600], ["准噶尔", 900], ["其他", 850]], ensure_ascii=False),
    }
    for k, v in meta.items():
        conn.execute("INSERT INTO meta(key,value) VALUES(?,?)", (k, v))
    conn.commit()

    # ---------------- generate images
    rows = conn.execute("""SELECT i.*, w.code, w.name, r.run_no, s.section_no
        FROM images i JOIN wells w ON w.id=i.well_id
        LEFT JOIN runs r ON r.id=i.run_id LEFT JOIN sections s ON s.id=i.section_id
        ORDER BY i.id""").fetchall()
    palettes = {
        "sand": [(185, 160, 106), (205, 184, 138), (160, 136, 88), (218, 200, 160)],
        "mud": [(111, 123, 120), (72, 86, 90), (138, 150, 145), (90, 100, 96)],
        "lime": [(185, 182, 164), (216, 212, 192), (143, 139, 120), (198, 196, 180)],
        "congl": [(141, 123, 99), (170, 150, 120), (110, 96, 78), (190, 170, 140)],
    }
    total = len(rows)
    for idx, row in enumerate(rows, start=1):
        code = row["code"]
        lith = LITH.get(code, ("细砂岩", "#b9a06a", "sand"))[2]
        sources = SOURCE_BY_LITH.get(lith, SOURCE_BY_LITH["sand"])
        source = sources[row["id"] % len(sources)]
        typ = row["type"]
        top = float(row["top_md"] if row["top_md"] is not None else 0)
        bottom = float(row["bottom_md"] if row["bottom_md"] is not None else top + 0.5)
        run_no = row["run_no"] or 1
        section_no = row["section_no"] or "—"
        label = f"{code}  第{run_no}筒  {section_no}  {top:.2f}-{bottom:.2f}m"
        if typ == "SURFACE":
            img = make_real_surface(960, 340, row["id"] * 13 + 5, source, label,
                                    top, bottom, code, run_no, section_no)
        elif typ == "ROLLED":
            img = make_real_rolled(1500, 300, row["id"] * 13 + 7, source,
                                   top, bottom, code, run_no)
        elif typ == "FLUORESCENCE":
            img = make_real_fluoro(960, 340, row["id"] * 13 + 11, source,
                                   top, bottom, code, run_no, section_no)
        elif typ == "BOX":
            img = make_real_box(900, 480, row["id"] * 13 + 17, source,
                                f"{code}  岩心箱  001", code)
        else:
            img = make_real_thin(600, 600, row["id"] * 13 + 19,
                                 f"{code}  {section_no}  薄片")
        file_rel = f"assets/core/img_{row['id']}.jpg"
        thumb_rel = f"assets/core/thumb_{row['id']}.jpg"
        img.save(STATIC / file_rel, quality=88)
        img.resize((240, 90), Image.Resampling.LANCZOS).save(STATIC / thumb_rel, quality=82)
        if typ in ("ROLLED", "FLUORESCENCE"):
            if typ == "ROLLED":
                v = make_real_rolled(300, 1200, row["id"] * 13 + 9, source,
                                     top, bottom, code, run_no)
            else:
                v = make_real_fluoro(300, 1200, row["id"] * 13 + 11, source,
                                     top, bottom, code, run_no, section_no)
            v.save(STATIC / file_rel.replace(".jpg", "_v.jpg"), quality=88)
        conn.execute("UPDATE images SET file=?, thumb=?, width=?, height=? WHERE id=?",
                     (file_rel, thumb_rel, img.width, img.height, row["id"]))
        if idx % 20 == 0 or idx == total:
            print(f"images {idx}/{total}")

    # strips per section
    for s in conn.execute("""SELECT s.*, w.code FROM sections s JOIN wells w ON w.id=s.well_id""").fetchall():
        lith = LITH.get(s["code"], ("细砂岩", "#b9a06a", "sand"))[2]
        source = SOURCE_BY_LITH.get(lith, SOURCE_BY_LITH["sand"])[s["id"] % 2]
        img = make_real_strip(140, 280, s["id"] * 7 + 3, source)
        rel = f"assets/core/strip_{s['id']}.jpg"
        img.save(STATIC / rel, quality=86)
        conn.execute("UPDATE sections SET strip_file=? WHERE id=?", (rel, s["id"]))
    conn.commit()

    # two demo measurements on image 1, so the viewer has something to show
    if conn.execute("SELECT COUNT(*) c FROM annotations").fetchone()["c"] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for geom, value in [
            ({"x1": 120, "y1": 80, "x2": 320, "y2": 180}, 21.5),
            ({"x1": 380, "y1": 120, "x2": 660, "y2": 190}, 19.7),
        ]:
            conn.execute("""INSERT INTO annotations(image_id,type,geometry,value,unit,label,author,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (1, "length", json.dumps(geom, ensure_ascii=False), value, "mm",
                 f"{value} mm", "admin", now))
        conn.commit()

    # summary
    counts = {t: conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"] for t in
              ["wells", "runs", "sections", "images", "experiments", "scans", "inventory", "txns"]}
    print("DB", DB_PATH)
    print("counts", counts)

    # 2026-11: build the supplemented core-data model in the same rebuild.
    # Keeps "python app/seed.py" as the single command for a complete demo DB.
    conn.close()
    from migrate_core_gap import main as build_core_gap
    build_core_gap()
    from migrate_p0 import main as build_p0
    build_p0()
    from migrate_charts import main as build_charts
    build_charts()
    from migrate_mainstream import main as build_mainstream
    build_mainstream()
    from migrate_report_cleanup import main as cleanup_reports
    cleanup_reports()
    from migrate_drop_legacy import main as drop_legacy
    drop_legacy()


if __name__ == "__main__":
    main()

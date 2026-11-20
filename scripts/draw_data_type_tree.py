# -*- coding: utf-8 -*-
"""Draw the current data type tree with data / analysis / output / support groups."""
import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\31498\Desktop\岩心数据库")
DB = BASE / "app" / "data" / "core.db"
OUT = BASE / "docs" / "data_type_tree.png"

W, H = 2300, 2020
X0, INDENT, BOX_W, ROW_H, GAP = 90, 72, 530, 44, 6
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def count(con, table, where=""):
    try:
        return con.execute(f'SELECT COUNT(*) FROM "{table}" {where}').fetchone()[0]
    except Exception:
        return 0


con = sqlite3.connect(DB)
C = {k: count(con, k) for k in [
    "wells", "runs", "strata", "coring_plan", "sections", "core_description", "core_fracture", "core_vug",
    "samples", "images", "image_calibration", "annotations", "inventory", "txns",
    "core_sidewall", "scans", "products", "core_analysis", "analysis_batch",
    "analysis_result", "report_category", "report_template", "report_output",
    "dictionary", "users", "audit",
]}
C["generated"] = count(con, "report_output", "WHERE status='已生成'")
con.close()

NAVY = (11, 59, 90)
TEAL = (14, 116, 144)
BLUE = (37, 99, 235)
GREEN = (15, 159, 110)
AMBER = (183, 121, 31)
PURPLE = (109, 76, 168)
GRAY = (96, 114, 132)
DIM = (138, 154, 169)
LINE = (197, 214, 227)
BG = (247, 250, 253)
WHITE = (255, 255, 255)

ROWS = [
    # group header
    ("G_OUT", "成果数据", "REPORT ARTIFACTS", "成果层", GREEN),
    ("cat", "成果分类", "report_category", 0, "G_OUT", "基本图 / 综合图 / 荧光 / 岩屑 / 多井 / 柱状 / 层模板", GREEN),
    ("tpl", "成果模板", "report_template", 1, "cat", "编码 · 版本 · 项目 · 配置 JSON", GREEN),
    ("out", "成果记录", "report_output", 2, "tpl", "井 × 模板 · 状态 · 来源", GREEN),
    ("file", "生成文件", "PNG", 3, "out", "file_url · file_hash · file_size", GREEN),
    ("ext", "外部成果", "uploaded", 3, "out", "外部 PDF/图片，审核后发布", AMBER),

    ("G_WELL", "井与取心数据", "WELL & CORE DATA", "数据层", NAVY),
    ("well", "井", "wells", 0, "G_WELL", "井号 · 井名 · 地区 · 构造 · 坐标", NAVY),
    ("run", "取心回次", "runs", 1, "well", "回次号 · 顶底深 · 进尺 · 心长 · 收获率", NAVY),
    ("plan", "取心设计", "coring_plan", 2, "run", "run_id 1:1 · 设计进尺/心长", BLUE),
    ("strata", "地层", "strata", 2, "run", "层位 · 顶底深", BLUE),
    ("sec", "岩心段", "sections", 2, "run", "段号 · 顶底深 · 岩性 · 荧光 · 含油", BLUE),
    ("desc", "岩心描述", "core_description", 3, "sec", "区间 · 版本 · is_current · 2017 13 项", GREEN),
    ("frac", "裂缝", "core_fracture", 3, "sec", "逐条：类型/倾角/走向/长度/充填", GREEN),
    ("vug", "孔洞", "core_vug", 3, "sec", "逐条：类型/尺寸/面积/面孔率", GREEN),
    ("sample", "样品", "samples", 3, "sec", "段/井壁/母样 · parent_sample_id", AMBER),
    ("img", "影像", "images", 3, "sec", "外表皮/展开/荧光/箱/薄片", AMBER),
    ("cal", "影像标定", "image_calibration", 4, "img", "控制点 · 像素/毫米", GRAY),
    ("anno", "测量标注", "annotations", 4, "img", "几何 · 长度/面积", GRAY),
    ("inv", "库存", "inventory", 3, "sec", "库位 · 数量 · 状态", AMBER),
    ("txn", "库存流水", "txns", 4, "inv", "出入库 · 数量 · 操作人", GRAY),
    ("side", "井壁取心", "core_sidewall", 1, "well", "样品号 · 深度 · 岩性 · 含油", BLUE),
    ("scan", "扫描记录", "scans", 1, "well", "回次 · 深度 · 影像数 · 状态", BLUE),
    ("prod", "成果总览", "products", 1, "well", "6 类成果完成状态", DIM),

    ("G_AN", "分析数据", "ANALYSIS DATA", "数据层", PURPLE),
    ("ca", "分析数据集", "core_analysis", 0, "G_AN", "名称 · 版本 · 实验室 · 深度校正", PURPLE),
    ("batch", "实验批次", "analysis_batch", 1, "ca", "批次号 · 实验室 · 方法 · 质控", PURPLE),
    ("result", "实验结果", "analysis_result", 2, "batch", "sample_id · 项目 · 参数 · 值 · 单位", PURPLE),

    ("G_SUP", "支撑数据", "REFERENCE & GOVERNANCE", "支撑层", GRAY),
    ("dict", "数据字典", "dictionary", 0, "G_SUP", "结构/构造/接触/含气/分析大类", GRAY),
    ("user", "用户", "users", 0, "G_SUP", "admin / editor / viewer", GRAY),
    ("audit", "审计", "audit", 0, "G_SUP", "录入/修改/删除/生成/恢复", GRAY),
]

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 9], fill=NAVY)
d.rectangle([0, 9, W, 12], fill=TEAL)
d.text((62, 38), "当前数据类型树", font=font(38, True), fill=NAVY)
d.text((64, 90), "数据层 · 分析数据 · 成果数据 · 支撑数据", font=font(17), fill=GRAY)
d.text((W - 350, 48), "DATA TYPE TREE", font=font(14, True), fill=TEAL)
d.text((W - 350, 76), "counts from current SQLite demo", font=font(11), fill=DIM)
d.line([64, 128, W - 60, 128], fill=LINE, width=1)

y = 150
positions = {}
for row in ROWS:
    if row[0].startswith("G_"):
        key, title, en, layer, color = row
        d.rounded_rectangle([X0 - 12, y, W - 64, y + 56], radius=8, fill=(WHITE if color != GRAY else (248, 249, 250)),
                            outline=(214, 228, 238))
        d.rounded_rectangle([X0 - 12, y, X0 + 6, y + 56], radius=3, fill=color)
        d.text((X0 + 18, y + 9), title, font=font(18, True), fill=color)
        d.text((X0 + 18, y + 34), en, font=font(9, True), fill=DIM)
        d.text((W - 210, y + 18), layer, font=font(11, True), fill=color)
        positions[key] = (X0, y, 0, None, color, True)
        y += 66
        continue
    key, title, table, level, parent, note, color = row
    x = X0 + level * INDENT
    positions[key] = (x, y, level, parent, color, False)
    y += ROW_H + GAP

# connectors
for key, (x, y, level, parent, color, group) in positions.items():
    if group or not parent or parent.startswith("G_"):
        continue
    px, py, plevel, _, pcolor, pgroup = positions[parent]
    if pgroup:
        continue
    line_x = x - 24
    d.line([(line_x, py + ROW_H / 2), (line_x, y + ROW_H / 2)], fill=(176, 199, 214), width=2)
    d.line([(line_x, y + ROW_H / 2), (x - 1, y + ROW_H / 2)], fill=(176, 199, 214), width=2)
    d.ellipse([(line_x - 3, y + ROW_H / 2 - 3), (line_x + 3, y + ROW_H / 2 + 3)], fill=color)

# boxes
for key, (x, y, level, parent, color, group) in positions.items():
    if group:
        continue
    row = next(r for r in ROWS if r[0] == key)
    title, table, note = row[1], row[2], row[5]
    d.rounded_rectangle([x + 3, y + 4, x + BOX_W + 3, y + ROW_H + 4], radius=7, fill=(226, 235, 243))
    d.rounded_rectangle([x, y, x + BOX_W, y + ROW_H], radius=7, fill=WHITE, outline=(211, 226, 237), width=1)
    d.rounded_rectangle([x, y, x + 6, y + ROW_H], radius=3, fill=color)
    d.text((x + 18, y + 6), title, font=font(16, True), fill=(30, 50, 70))
    d.text((x + 18, y + 27), table, font=font(9), fill=DIM)
    cnt = C.get({"cat": "report_category", "tpl": "report_template", "out": "report_output",
                 "file": "generated", "ext": "report_output", "well": "wells", "run": "runs",
                 "plan": "coring_plan", "strata": "strata", "sec": "sections", "desc": "core_description",
                 "frac": "core_fracture", "vug": "core_vug", "sample": "samples", "img": "images",
                 "cal": "image_calibration", "anno": "annotations", "inv": "inventory", "txn": "txns",
                 "side": "core_sidewall", "scan": "scans", "prod": "products", "ca": "core_analysis",
                 "batch": "analysis_batch", "result": "analysis_result", "dict": "dictionary",
                 "user": "users", "audit": "audit"}.get(key, ""), 0)
    if key == "ext":
        cnt = 0
    txt = str(cnt)
    tw = d.textlength(txt, font=font(15, True))
    d.rounded_rectangle([x + BOX_W - 54, y + 9, x + BOX_W - 12, y + 32], radius=10,
                        fill=(242, 249, 252), outline=(211, 229, 239))
    d.text((x + BOX_W - 33 - tw / 2, y + 11), txt, font=font(15, True), fill=color)
    d.text((940, y + 13), note, font=font(13), fill=GRAY)

# bottom summary
sy = y + ROW_H + 16
d.rounded_rectangle([X0 - 12, sy, W - 64, sy + 70], radius=8, fill=(245, 250, 253), outline=(215, 230, 240))
d.text((X0 + 10, sy + 12), f"成果记录 {C['report_output']} 条 · 已生成文件 {C['generated']} 个 · 外部成果 0 条 · 成果模板 {C['report_template']} 个",
       font=font(13, True), fill=TEAL)
d.text((X0 + 10, sy + 38), "成果图由结构化数据 + 模板生成；文件与数据版本/模板版本绑定，不把成果图当作原始录入数据。",
       font=font(11), fill=GRAY)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT, quality=95)
print("saved", OUT, C)

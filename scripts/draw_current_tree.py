# -*- coding: utf-8 -*-
"""Draw the current core-data tree from the live SQLite database."""
import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\31498\Desktop\岩心数据库")
DB = BASE / "app" / "data" / "core.db"
OUT = BASE / "docs" / "current_data_tree.png"

W, H = 2300, 1660
X0 = 100
INDENT = 82
BOX_W = 470
ROW_H = 50
GAP = 8
STEP = ROW_H + GAP
TOP = 172

NAVY = (11, 59, 90)
CYAN = (14, 116, 144)
BLUE = (37, 99, 235)
GREEN = (15, 159, 110)
AMBER = (183, 121, 31)
GRAY = (100, 116, 139)
DIM = (140, 157, 173)
LINE = (190, 208, 222)
BG = (247, 250, 253)
WHITE = (255, 255, 255)
SOFT = (235, 244, 249)

FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def count(con, table):
    try:
        return con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except Exception:
        return 0


ROWS = [
    # id, title, table, level, parent, note, color
    ("root", "井", "wells", 0, None, "井号 / 井名 / 区块 / 构造", NAVY),
    ("run", "取心回次", "runs", 1, "root", "well_id · run_no · 顶底深 · 收获率", CYAN),
    ("plan", "取心设计", "coring_plan", 2, "run", "run_id 1:1 · 设计进尺/心长", BLUE),
    ("strata", "地层", "strata", 2, "run", "run_id · 层位 · 顶底深", BLUE),
    ("section", "岩心段", "sections", 2, "run", "run_id · 段号 · 顶底深", BLUE),
    ("desc", "岩心描述", "core_description", 3, "section", "区间 · 版本 · is_current", GREEN),
    ("fracture", "裂缝", "core_fracture", 3, "section", "逐条：倾角/走向/长度/充填", GREEN),
    ("vug", "孔洞", "core_vug", 3, "section", "逐条：尺寸/面积/面孔率", GREEN),
    ("sample", "样品", "samples", 3, "section", "可挂段 / 井壁 / 母样", AMBER),
    ("image", "影像", "images", 3, "section", "可挂井 / 回次 / 段", AMBER),
    ("cal", "影像标定", "image_calibration", 4, "image", "image_id · 控制点 · 像素/毫米", GRAY),
    ("anno", "测量标注", "annotations", 4, "image", "image_id · 几何 · 长度/面积", GRAY),
    ("inv", "库存", "inventory", 3, "section", "section_id · 库位 · 数量", AMBER),
    ("txn", "库存流水", "txns", 4, "inv", "section_id · 类型 · 数量", GRAY),
    ("side", "井壁取心", "core_sidewall", 1, "root", "well_id · 样品号 · 深度", CYAN),
    ("ca", "分析数据集", "core_analysis", 1, "root", "well_id · 名称 · 版本", CYAN),
    ("batch", "实验批次", "analysis_batch", 2, "ca", "core_analysis_id · 批次号 · 实验室", BLUE),
    ("result", "实验结果", "analysis_result", 3, "batch", "batch_id · sample_id · 参数/值", GREEN),
    ("report", "成果输出", "report_output", 1, "root", "well_id × template_id · 状态", CYAN),
    ("template", "成果模板", "report_template", 1, "root", "编码 · 分类 · 版本 · 项目", CYAN),
    ("category", "成果分类", "report_category", 2, "template", "基本图 / 综合图 / 荧光 / 岩屑", BLUE),
    ("scans", "扫描记录", "scans", 1, "root", "well_id · 回次 · 扫描日期", CYAN),
    ("products", "成果总览", "products", 1, "root", "well_id · 6 类成果状态", CYAN),
]

con = sqlite3.connect(DB)
counts = {r[0]: count(con, r[2]) for r in ROWS}
con.close()

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)

# top accent
d.rectangle([0, 0, W, 8], fill=NAVY)
d.rectangle([0, 8, W, 10], fill=CYAN)

d.text((70, 42), "当前主库数据树", font=font(38, True), fill=NAVY)
d.text((72, 94), "岩心数据库 · 主流层次 · 旧表已清理", font=font(18), fill=GRAY)
d.text((W - 360, 52), "CORE DATA TREE", font=font(15, True), fill=CYAN)
d.text((W - 360, 80), "well → run → section → sample / analysis", font=font(12), fill=DIM)

# header rule
d.line([70, 132, W - 70, 132], fill=LINE, width=1)

positions = {}
for i, (key, title, table, level, parent, note, color) in enumerate(ROWS):
    y = TOP + i * STEP
    x = X0 + level * INDENT
    positions[key] = (x, y, level, parent, color)

# connectors
for key, (x, y, level, parent, color) in positions.items():
    if not parent:
        continue
    px, py, plevel, _, pcolor = positions[parent]
    line_x = x - 26
    d.line([(line_x, py + ROW_H / 2), (line_x, y + ROW_H / 2)], fill=(176, 199, 214), width=2)
    d.line([(line_x, y + ROW_H / 2), (x - 1, y + ROW_H / 2)], fill=(176, 199, 214), width=2)
    d.ellipse([(line_x - 3, y + ROW_H / 2 - 3), (line_x + 3, y + ROW_H / 2 + 3)], fill=color)

# boxes
for key, (x, y, level, parent, color) in positions.items():
    title = next(r[1] for r in ROWS if r[0] == key)
    table = next(r[2] for r in ROWS if r[0] == key)
    note = next(r[5] for r in ROWS if r[0] == key)
    # shadow
    d.rounded_rectangle([x + 3, y + 4, x + BOX_W + 3, y + ROW_H + 4], radius=7, fill=(226, 235, 243))
    d.rounded_rectangle([x, y, x + BOX_W, y + ROW_H], radius=7, fill=WHITE, outline=(213, 226, 236), width=1)
    d.rounded_rectangle([x, y, x + 6, y + ROW_H], radius=3, fill=color)
    d.text((x + 20, y + 9), title, font=font(19, True), fill=(30, 50, 70))
    d.text((x + 20, y + 31), table, font=font(11), fill=DIM)
    # count pill
    txt = str(counts[key])
    tw = d.textlength(txt, font=font(18, True))
    pill_x = x + BOX_W - 18 - max(42, tw + 20)
    d.rounded_rectangle([pill_x, y + 12, x + BOX_W - 14, y + ROW_H - 12],
                        radius=12, fill=(243, 249, 252), outline=(212, 230, 239))
    d.text((pill_x + (x + BOX_W - 14 - pill_x - tw) / 2, y + 16), txt,
           font=font(18, True), fill=color)
    # notes right column
    d.text((980, y + 13), note, font=font(14), fill=GRAY)
    # horizontal separator
    d.line([(940, y + ROW_H + 3), (W - 80, y + ROW_H + 3)], fill=(238, 244, 248), width=1)

# notes / cross-links
y_note = TOP + len(ROWS) * STEP + 14
d.rounded_rectangle([X0, y_note, W - 80, y_note + 92], radius=8, fill=(245, 250, 253),
                    outline=(215, 230, 240))
d.text((X0 + 20, y_note + 14), "跨分支引用", font=font(15, True), fill=CYAN)
d.text((X0 + 20, y_note + 40),
       "样品：可属于岩心段、井壁取心或母样；实验结果通过 sample_id 回挂样品；影像可挂井 / 回次 / 段。",
       font=font(13), fill=(80, 100, 120))
d.text((X0 + 20, y_note + 63),
       "成果输出：well_id + template_id；成果模板按分类 / 版本 / 项目区分，不再属于岩心数据。",
       font=font(13), fill=(80, 100, 120))

# legend
ly = y_note + 112
d.text((X0, ly), "图例", font=font(14, True), fill=GRAY)
d.line([(X0 + 50, ly + 10), (X0 + 105, ly + 10)], fill=(176, 199, 214), width=2)
d.text((X0 + 115, ly + 1), "父子层级", font=font(13), fill=GRAY)
d.ellipse([(X0 + 230, ly + 6), (X0 + 238, ly + 14)], fill=CYAN)
d.text((X0 + 248, ly + 1), "节点", font=font(13), fill=GRAY)
d.text((X0 + 320, ly + 1), "方框右侧数字 = 当前主库记录数", font=font(13), fill=GRAY)
d.text((W - 520, ly + 1), "说明：旧表 core_observation / experiments / chart_* 已删除",
       font=font(12), fill=DIM)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT, quality=95)
print("saved", OUT, OUT.stat().st_size, "counts", counts)

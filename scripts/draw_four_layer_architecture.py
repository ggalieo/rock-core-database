# -*- coding: utf-8 -*-
"""Draw the implemented four-layer core database architecture."""
import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\31498\Desktop\岩心数据库")
DB = BASE / "app" / "data" / "core.db"
OUT = BASE / "docs" / "four_layer_architecture.png"

W, H = 2200, 1520
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def count(con, table):
    try:
        return con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except Exception:
        return 0


con = sqlite3.connect(DB)
C = {
    "wells": count(con, "wells"), "runs": count(con, "runs"), "sections": count(con, "sections"),
    "desc": count(con, "core_description"), "samples": count(con, "samples"),
    "results": count(con, "analysis_result"), "images": count(con, "images"),
    "inventory": count(con, "inventory"), "templates": count(con, "report_template"),
    "outputs": count(con, "report_output"),
    "generated": con.execute("SELECT COUNT(*) FROM report_output WHERE status='已生成'").fetchone()[0],
}
con.close()

NAVY = (11, 59, 90)
TEAL = (14, 116, 144)
BLUE = (37, 99, 235)
GREEN = (15, 159, 110)
AMBER = (183, 121, 31)
PURPLE = (109, 76, 168)
GRAY = (92, 112, 132)
DIM = (135, 151, 166)
LINE = (201, 217, 229)
BG = (247, 250, 253)
WHITE = (255, 255, 255)

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 9], fill=NAVY)
d.rectangle([0, 9, W, 12], fill=TEAL)

d.text((64, 40), "岩心数据库四层架构", font=font(38, True), fill=NAVY)
d.text((66, 91), "数据层 → 操作层 → 展示层 → 成果层 · 当前版本已落地", font=font(17), fill=GRAY)
d.text((W - 380, 48), "FOUR-LAYER ARCHITECTURE", font=font(14, True), fill=TEAL)
d.text((W - 380, 76), "wells / core / analysis / report artifacts", font=font(11), fill=DIM)
d.line([64, 124, W - 64, 124], fill=LINE, width=1)

# Layer bands
bands = [
    ("成果层", "OUTPUT", 150, 390, (246, 252, 249), GREEN),
    ("展示层", "DISPLAY", 420, 740, (242, 249, 253), BLUE),
    ("操作层", "OPERATION", 770, 1080, (243, 250, 250), TEAL),
    ("数据层", "DATA", 1110, 1430, (247, 250, 253), NAVY),
]
for name, en, y0, y1, bg, color in bands:
    d.rounded_rectangle([50, y0, W - 50, y1], radius=12, fill=bg, outline=(214, 228, 238), width=1)
    d.rounded_rectangle([50, y0, 142, y1], radius=12, fill=color)
    d.text((66, y0 + 22), name, font=font(20, True), fill=WHITE)
    d.text((67, y0 + 52), en, font=font(8, True), fill=(230, 242, 247))

# helper
def box(x, y, w, h, title, lines, color, tag=None):
    d.rounded_rectangle([x + 3, y + 4, x + w + 3, y + h + 4], radius=8, fill=(227, 236, 244))
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=WHITE, outline=(208, 224, 235), width=1)
    d.rounded_rectangle([x, y, x + 5, y + h], radius=3, fill=color)
    d.text((x + 16, y + 12), title, font=font(15, True), fill=(27, 48, 67))
    yy = y + 36
    for line in lines:
        d.text((x + 16, yy), line, font=font(10), fill=GRAY)
        yy += 18
    if tag:
        tw = d.textlength(tag, font=font(8, True))
        d.rounded_rectangle([x + w - tw - 20, y + 10, x + w - 8, y + 26], radius=7,
                            fill=(238, 248, 243) if tag.startswith("已") else (248, 245, 238))
        d.text((x + w - tw - 14, y + 12), tag, font=font(8, True), fill=GREEN if tag.startswith("已") else AMBER)


# Output layer
box(180, 190, 300, 125, "成果记录", ["report_output", f"{C['outputs']} 条井×模板", "source_type / status"], GREEN, "已实现")
box(515, 190, 300, 125, "生成文件", ["PNG /generated/reports", f"已生成 {C['generated']} 个", "file_url / file_hash"], GREEN, "已实现")
box(850, 190, 300, 125, "版本与快照", ["template_version", "data_version", "file_size / generated_at"], GREEN, "已实现")
box(1185, 190, 300, 125, "PDF/外部成果", ["PDF 导出扩展", "uploaded 外部文件", "审核后发布"], AMBER, "可扩展")
box(1520, 190, 300, 125, "审核/发布", ["review_status", "未审核 → 已审核", "审计留痕"], AMBER, "可扩展")

# Display layer
box(180, 455, 300, 110, "井档案", ["基础信息 / 取心 / 影像", "岩心数据 / 成果输出", "库存与实验"], BLUE, "已实现")
box(515, 455, 300, 110, "综合柱状图", ["深度 / 地层 / 岩性", "描述 / 照片 / 曲线", "样品 / RQD"], BLUE, "已实现")
box(850, 455, 300, 110, "影像查看器", ["真实岩心照片", "蓝色区间/深度标注", "标定与测量"], BLUE, "已实现")
box(1185, 455, 300, 110, "成果矩阵", [f"{C['templates']} 类模板", "状态/文件/版本", "单井与全局视图"], BLUE, "已实现")
box(1520, 455, 300, 110, "数据质量/导出", ["表格全字段", "筛选/导出", "质量检查扩展"], BLUE, "部分")

# Operation layer
box(180, 810, 300, 110, "数据录入", ["13 类业务对象", "多版本描述/母样", "分析批次/结果"], TEAL, "已实现")
box(515, 810, 300, 110, "批量导入", ["Excel 模板/参考 ID", "预检查/错误 CSV", "业务编码解析"], TEAL, "已实现")
box(850, 810, 300, 110, "成果生成", ["生成任务/渲染器", "PNG 落盘 + 哈希", "数据版本绑定"], GREEN, "已实现")
box(1185, 810, 300, 110, "审核/权限", ["admin/editor/viewer", "审计日志", "审核流扩展"], TEAL, "部分")
box(1520, 810, 300, 110, "检索/维护", ["井号/岩性/描述", "编辑/删除/恢复", "软删除与回收站"], TEAL, "已实现")

# Data layer
box(180, 1150, 300, 145, "井与取心", [f"井 {C['wells']} · 回次 {C['runs']}", f"岩心段 {C['sections']}", "地层 / 取心设计"], NAVY, "已实现")
box(515, 1150, 300, 145, "岩心描述", [f"core_description {C['desc']}", "裂缝/孔洞/井壁", "区间 + 版本 + 当前"], NAVY, "已实现")
box(850, 1150, 300, 145, "样品与分析", [f"样品 {C['samples']}", "数据集/批次/结果", f"结果 {C['results']}"], NAVY, "已实现")
box(1185, 1150, 300, 145, "影像与库存", [f"影像 {C['images']}", "标定/标注", f"库存 {C['inventory']} + 流水"], NAVY, "已实现")
box(1520, 1150, 300, 145, "配置/支撑", ["成果模板/分类", "字典 / 用户", "审计 / 库位"], NAVY, "已实现")

# Side services
side_y = 190
side = [
    ("认证与权限", ["Session / RBAC", "admin / editor / viewer"]),
    ("审计", ["audit 5 条（演示）", "生成/录入/删除"]),
    ("关系库", ["SQLite 演示", "PostgreSQL + PostGIS"]),
    ("文件存储", ["本地 / MinIO", "影像 + 生成成果"]),
    ("渲染器", ["Pillow PNG", "PDF 扩展"]),
]
for title, lines in side:
    d.rounded_rectangle([W - 270, side_y, W - 64, side_y + 76], radius=8, fill=WHITE, outline=(208, 224, 235))
    d.text((W - 252, side_y + 10), title, font=font(13, True), fill=NAVY)
    for i, line in enumerate(lines):
        d.text((W - 252, side_y + 32 + i * 16), line, font=font(9), fill=GRAY)
    side_y += 88

# Arrows between layers
# (tail, head, label): arrows point to the head
for x, tail, head, label in [
    (1090, 390, 420, "成果记录回写展示"),
    (1090, 770, 740, "页面操作 / 生成请求"),
    (1090, 1110, 1080, "读取结构化数据"),
]:
    d.line([(x, tail), (x, head)], fill=TEAL, width=3)
    direction = 1 if head > tail else -1
    d.polygon([(x - 6, head - 8 * direction), (x + 6, head - 8 * direction), (x, head)], fill=TEAL)
    tw = d.textlength(label, font=font(8))
    d.rectangle([x - tw / 2 - 6, (tail + head) / 2 - 7, x + tw / 2 + 6, (tail + head) / 2 + 7], fill=BG)
    d.text((x - tw / 2, (tail + head) / 2 - 5), label, font=font(8), fill=TEAL)

# bottom note
d.text((64, H - 52), "说明：综合柱状图由结构化数据 + 模板参数生成；成果文件与数据版本绑定，不把图当成原始录入数据。",
       font=font(11), fill=DIM)
d.text((W - 390, H - 52), "current build · SQLite demo · PNG renderer", font=font(9), fill=DIM)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT, quality=95)
print("saved", OUT, C)

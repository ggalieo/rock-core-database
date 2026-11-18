-- ============================================================
-- 岩心数据补充模型 v1
-- 依据：2017《钻井地质设计》第4页表1-1 岩心资料 13 项
-- 说明：本文件只新增对象，不删除、不改写现有业务表
-- ============================================================

-- 1. 数据字典：结构、构造、接触关系、化石、含气、破碎磨损、分析大类
CREATE TABLE IF NOT EXISTS dictionary (
  dict_type   TEXT NOT NULL,
  code        TEXT NOT NULL,
  name        TEXT NOT NULL,
  parent_code TEXT,
  sort_no     INTEGER DEFAULT 0,
  remark      TEXT,
  PRIMARY KEY (dict_type, code)
);

-- 2. 取心设计：与 runs 1:1，补“取心目的、原则、设计值、变更”
CREATE TABLE IF NOT EXISTS coring_plan (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id             INTEGER UNIQUE,
  purpose            TEXT,
  principle          TEXT,
  design_top_md      REAL,
  design_bottom_md   REAL,
  design_footage     REAL,
  design_core_length REAL,
  change_reason      TEXT,
  approved_by        TEXT,
  approved_at        TEXT
);

-- 3. 岩心观察：与 sections 1:1，补 2017 的结构/构造/缝/洞/接触/化石/倾角/含气/破碎磨损
CREATE TABLE IF NOT EXISTS core_observation (
  id                        INTEGER PRIMARY KEY AUTOINCREMENT,
  section_id                INTEGER UNIQUE,
  structure_code            TEXT,
  structure_desc            TEXT,
  sedimentary_structure_code TEXT,
  sedimentary_structure_desc TEXT,
  fracture_desc             TEXT,
  fracture_density          REAL,
  fracture_angle            REAL,
  vug_desc                  TEXT,
  vug_size_mm               REAL,
  vug_area_pct              REAL,
  contact_relation_code     TEXT,
  fossil_desc               TEXT,
  dip_angle                 REAL,
  gas_show_code             TEXT,
  breakage_wear_code        TEXT,
  observer                  TEXT,
  observed_at               TEXT,
  remark                    TEXT
);

-- 4. 裂缝：1 个岩心段可有多条裂缝，可挂影像与几何
CREATE TABLE IF NOT EXISTS core_fracture (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  section_id    INTEGER,
  fracture_no   TEXT,
  type_code     TEXT,
  dip_angle     REAL,
  strike_angle  REAL,
  length_mm     REAL,
  width_mm      REAL,
  fill_code     TEXT,
  density_per_m REAL,
  image_id      INTEGER,
  geometry      TEXT,
  description   TEXT,
  created_at    TEXT
);

-- 5. 孔洞：1 个岩心段可有多个孔洞，可挂影像与几何
CREATE TABLE IF NOT EXISTS core_vug (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  section_id  INTEGER,
  vug_no      TEXT,
  type_code   TEXT,
  size_mm     REAL,
  area_mm2    REAL,
  area_pct    REAL,
  fill_code   TEXT,
  image_id    INTEGER,
  geometry    TEXT,
  description TEXT,
  created_at  TEXT
);

-- 6. 井壁取心：井级对象，补 2017“包括井壁取心”的逐颗记录
CREATE TABLE IF NOT EXISTS core_sidewall (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  well_id          INTEGER,
  depth_md         REAL,
  sample_no        TEXT UNIQUE,
  lithology        TEXT,
  description      TEXT,
  oil_show         TEXT,
  fluorescence     TEXT,
  image_id         INTEGER,
  analysis_summary TEXT,
  collected_at     TEXT
);

-- 7. 样品主表：连接“岩心段/井壁取心”与“实验”
CREATE TABLE IF NOT EXISTS samples (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  sample_no   TEXT UNIQUE,
  well_id     INTEGER,
  section_id  INTEGER,
  sidewall_id INTEGER,
  sample_type TEXT,
  top_md      REAL,
  bottom_md   REAL,
  collected_at TEXT,
  keeper      TEXT,
  status      TEXT
);

-- 8. 影像标定：像素—深度控制点、残差、版本
CREATE TABLE IF NOT EXISTS image_calibration (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id      INTEGER,
  method        TEXT,
  control_points TEXT,
  pixel_per_mm  REAL,
  residual_px   REAL,
  residual_mm   REAL,
  version       TEXT,
  operator      TEXT,
  calibrated_at TEXT
);

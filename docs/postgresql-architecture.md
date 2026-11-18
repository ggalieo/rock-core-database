# PostgreSQL 16 + PostGIS + MinIO/S3 + pgvector 架构

## 1. 目标

把当前“SQLite 单文件 + 本地 JPG”的演示架构，升级为可承载真实岩心数据、多人访问、影像/CT 文件和后续 AI 检索的生产架构：

```text
浏览器 / 移动端
      │  HTTP
      ▼
app/server.py  （保留现有 API 与前端）
      │
      ├── PostgreSQL 16  ── 主数据、观察、裂缝/孔洞、样品、实验、库存、审计
      │      ├── PostGIS      井位、井轨迹、剖面、空间查询
      │      ├── JSONB        可变地质描述、标注几何、标定控制点
      │      └── pgvector     图像/文本 Embedding（后续 AI）
      │
      └── MinIO / S3  ── 原图、缩略图、条带、薄片、CT、PDF、成果文件
```

## 2. 数据分层

| 层 | 存储 | 内容 |
|---|---|---|
| 主数据 | PostgreSQL | 井、回次、地层、岩心段、样品、取心设计 |
| 地质观察 | PostgreSQL | 结构、构造、裂缝、孔洞、接触关系、化石、倾角、含气、破碎磨损 |
| 影像元数据 | PostgreSQL | 类型、光性、深度、宽高、DPI、mm/px、设备、操作人、质量 |
| 空间/深度 | PostgreSQL + PostGIS + range | 井位点、井轨迹、段深度、影像深度、实验深度 |
| 影像文件 | MinIO/S3 | 原图、缩略图、条带、薄片、CT、PDF |
| 标注/标定 | PostgreSQL JSONB | 线/面/框几何、控制点、残差、版本 |
| 向量 | pgvector | 图像 Embedding、文本 Embedding，用于相似检索 |
| 检索 | PostgreSQL GIN/Trigram；可选 OpenSearch | 描述、井号、岩性、全文 |
| 分析 | PostgreSQL 物化视图；可选 ClickHouse/DuckDB | 覆盖率、岩性、实验、多井对比 |

## 3. 关键表

- 原有：`wells`、`runs`、`strata`、`sections`、`images`、`scans`、`experiments`、`inventory`、`txns`、`products`、`users`、`audit`、`meta`
- 2017 补充：`core_fracture`、`core_vug`、`core_sidewall`、`samples`、`coring_plan`、`image_calibration`、`dictionary`
- 主流层次：`core_analysis`、`core_description`、`analysis_batch`、`analysis_result`；`samples.parent_sample_id`
- 成果输出：`report_category`、`report_template`、`report_output`（与岩心数据分离）
- 空间/深度镜像：`well_geometry`、`run_depth`、`section_depth`、`image_depth`、`experiment_depth`
- 向量：`image_embedding(image_id, model, embedding vector(512))`，HNSW 余弦索引

镜像表的设计目的：让现有 API 的 `SELECT * FROM wells/sections/images` 保持兼容，不把 PostGIS geometry / range 对象直接塞进返回 JSON。

## 4. 本地/服务器部署

### 4.1 启动

```bash
cd deploy
docker compose up -d --build
```

服务：

- 应用：<http://127.0.0.1:8010>
- MinIO 控制台：<http://127.0.0.1:9001>
- PostgreSQL：`127.0.0.1:5432`，库 `core`，用户 `core`

首次启动时 PostgreSQL 会按顺序执行：

1. `db/postgres/001_schema.sql`
2. `db/postgres/002_seed.sql`

`002_seed.sql` 从当前 SQLite 演示库导出，包含 15 口井、65 个岩心段、113 张影像、65 条观察、21 条裂缝、25 条孔洞、24 条井壁取心、15 个样品、21 条取心设计、65 条影像标定、28 个字典码。

### 4.2 单独上传影像

```bash
python scripts/upload_assets_to_minio.py
```

上传到 `rock-core/core/<filename>`；应用请求 `/assets/core/<filename>` 时，由 `app/s3store.py` 从 MinIO 读取，失败再回退本地静态文件。

### 4.3 环境变量

| 变量 | 用途 |
|---|---|
| `DATABASE_URL` | 设置后切换到 PostgreSQL；不设置则继续使用 SQLite |
| `S3_ENDPOINT` | MinIO/S3 地址 |
| `S3_BUCKET` | 影像桶，默认 `rock-core` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | 访问凭据 |
| `S3_REGION` | 默认 `us-east-1` |

## 5. 应用兼容方式

`app/db_backend.py`：

- `DATABASE_URL` 为空 → 原 SQLite，演示模式完全不变；
- `DATABASE_URL` 有值 → psycopg 连接 PostgreSQL，自动把现有 `?` 占位符转成 `%s`；
- `app/server.py` 只改了几处数据库方言差异：统计 `CAST(... AS numeric)`、年份 `EXTRACT`、标注 `RETURNING id`、审计 `user_name` 别名。

`app/s3store.py`：

- `/assets/core/*` 优先从 MinIO 取；
- 对象不存在时回退本地 `app/static/assets/core`，方便离线演示。

## 6. 迁移顺序

1. 启动 PostgreSQL/MinIO；
2. 执行 `001_schema.sql`；
3. 执行 `002_seed.sql`；
4. 上传影像到 MinIO；
5. 设置 `DATABASE_URL` / `S3_*` 启动应用；
6. 用前端逐页验收：总览、井档案、柱状图、影像、检索、库存、统计、设置；
7. 之后再把真实数据导入，停用演示 seed。

## 7. 备份与安全

- PostgreSQL：`pg_dump -Fc core > core.dump`，定期演练恢复。
- MinIO：`mc mirror local/rock-core /backup/rock-core`，开启版本/生命周期。
- 凭据：不要提交真实密码；生产用 `.env` 或 Secret 管理。
- 当前 `users` 仍没有真实登录/RBAC；上生产前必须补认证与行级权限。
- `image_embedding` 只是表结构，尚未接模型；AI 结果必须保留模型版本和人工复核。

## 8. 当前限制

- 本机没有 Docker/PostgreSQL/MinIO，所以只完成了代码、Schema、Seed、Compose，未在本机启动实例验证。
- `002_seed.sql` 是演示数据导出，不是生产数据迁移工具。
- `images.size_bytes/etag` 目前由上传脚本可补，但 seed 未写入。
- HNSW 索引和 pgvector 写入需要按实际 embedding 维度（当前 512）调整。

## 9. 数据录入接口

应用层新增 `app/entry.py`，由字段元数据同时驱动前端表单和后端校验：

- `GET /api/entry/meta`：实体、字段、字典、井/回次/段/样品选项
- `GET /api/entry/recent?entity=`：最近 8 条
- `POST /api/entry/<entity>`：`well`、`run`、`section`、`observation`、`fracture`、`vug`、`sidewall`、`sample`、`experiment`、`coring_plan`

写入前会校验必填、类型、字典、外键、顶底深、唯一键和“一段一观察”“样品只属于段或井壁取心之一”等规则。SQLite 使用 `lastrowid`，PostgreSQL 使用 `RETURNING id`，由 `app/db_backend.py` 统一。


## 10. 编辑、删除与 Excel 导入

- `GET /api/entry/list?entity=`：分页列表（当前最近 40 条）
- `GET /api/entry/<entity>/<id>`：取单条记录用于编辑
- `PUT /api/entry/<entity>/<id>`：更新
- `DELETE /api/entry/<entity>/<id>`：删除；有子记录时返回 409，不级联删除
- `GET /api/entry/template?entity=`：下载 Excel 模板（含字段说明和井/回次/段/样品参考 ID）
- `POST /api/entry/import/<entity>`：Base64 上传 `.xlsx` / `.xlsm`，逐行校验并返回成功/失败明细

## 11. P0 安全与数据治理

- 登录：`/api/auth/login`、`/api/auth/logout`、`/api/auth/me`；会话 Cookie 为 HttpOnly/SameSite=Lax。
- RBAC：`admin`、`editor`、`viewer`；写接口只允许 admin/editor。
- 审计：`audit` 表新增 `details`，所有写操作记录操作人、动作、对象和摘要。
- 软删除：核心表新增 `deleted_at`；列表默认排除，回收站/恢复接口保留记录。
- 影像：`images` 新增 `object_key/thumb_key/content_type/size_bytes/etag/deleted_at`；上传后本地 + MinIO 双写。
- 注意：P0 实现的是本地会话和基础 RBAC；生产还需接 SSO/LDAP、CSRF token、审计留存策略和对象存储生命周期。

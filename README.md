# 🃏 斗地主账单系统

基于 **Vue 3 + FastAPI** 的斗地主对局账单管理工具：上传结算截图 → AI 自动识别 → 记录分数 → 统计分析 → 结账计算最优转账方案。

前端使用 Vue 3（Vite + Naive UI + ECharts）编译为静态网页，后端使用 FastAPI；两者由同一个 Python 进程统一服务（单进程、单端口）。

---

## 一、架构

```
浏览器 ──► FastAPI (backend/main.py)
             │  ├─ /api/*           REST 接口（players / bills / stats / settlement / recognize）
             │  └─ 其他 GET 路径    前端静态资源 + SPA 回退（frontend/dist）
             └─ SQLite (data/bills.db)
```

- **前端**：Vue 3 + Vite 构建，产物生成到 `frontend/dist`，由 FastAPI 以静态资源方式返回；History 路由在服务端做 SPA 回退。
- **后端**：FastAPI + SQLite（WAL 模式，沿用旧数据结构，可直接对接已有数据）。
- **AI 识别**：OpenAI 兼容 API（默认 Mimo），把结算截图识别为结构化 JSON。

## 二、项目结构

```
doudizhu-bills/
├── backend/                 # FastAPI 后端包
│   ├── main.py              # 入口：注册 /api 路由 + 前端静态资源/SPA
│   ├── config.py            # 全局配置（路径、DB、API Key、模型名）
│   ├── database.py          # 数据库层（SQLite CRUD + 统计查询）
│   ├── llm.py               # OpenAI 兼容 API 图像识别
│   ├── settlement.py        # 结账计算（最少转账次数贪心算法）
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── utils.py             # 纯业务逻辑（去重/零和校验）
│   └── routers/             # 按领域拆分：players/bills/stats/settlement/recognize
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── App.vue          # 布局（侧边栏 + 顶栏 + 深色模式）
│   │   ├── router/          # 路由（History 模式）
│   │   ├── api/             # axios 封装 + 接口函数
│   │   ├── views/           # 六个页面（概览/上传/记录/玩家/统计/结账）
│   │   ├── components/      # 复用组件（StatCard / WinLossPill）
│   │   └── composables/     # useTheme 等
│   └── dist/                # 前端构建产物（FastAPI 运行时服务）
├── data/
│   ├── bills.db             # SQLite 数据库（WAL 模式）
│   └── images/              # 上传截图存储
├── pyproject.toml           # 后端依赖（uv 管理）
├── Dockerfile               # 多阶段构建：Vue → FastAPI
└── docker-compose.yml
```

## 三、快速启动

### 1. 后端依赖

```bash
uv sync          # 安装 FastAPI / uvicorn / openai 等后端依赖
```

### 2. 运行后端（同时服务前端构建产物）

先构建前端，再启动 FastAPI：

```bash
cd frontend && npm install && npm run build && cd ..
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

打开 http://127.0.0.1:8000 即可使用。

### 3. 前端开发模式（热更新）

```bash
# 终端 1：启动 FastAPI（提供 /api）
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 终端 2：启动 Vite 开发服务器（已配置 /api 代理到 8000）
cd frontend && npm run dev
```

打开 http://127.0.0.1:5173 。

## 四、环境变量（可选）

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `OPENAI_API_KEY` | AI 识别的 API Key（也可在页面上配置） | 空 |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址 | `https://api.xiaomimimo.com/v1` |
| `OPENAI_MODEL` | 识别模型 | `mimo-v2.5` |

可将它们写入项目根目录的 `.env` 文件（优先于系统环境变量），`config.py` 会自动加载。

## 五、Docker 部署

```bash
APP_PORT=8000 OPENAI_API_KEY=sk-xxx docker compose up -d --build
```

Dockerfile 分两阶段：先用 Node 构建前端，再用 Python 安装后端依赖并运行 FastAPI。

## 六、API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/players` | 玩家列表 / 新增 |
| PUT/DELETE | `/api/players/{id}` | 重命名 / 删除玩家 |
| GET | `/api/sessions` | 按局分组返回账单 |
| DELETE | `/api/sessions/{id}` | 删除整局 |
| PUT/DELETE | `/api/bills/{id}` | 更新 / 删除账单 |
| POST | `/api/recognize` | 批量识别截图（不落库） |
| POST | `/api/sessions/batch` | 批量保存（写图片 + 会话 + 账单） |
| GET | `/api/stats/*` | 累计 / 按月 / 按日 / 按局统计 |
| POST | `/api/settlement/transfers` | 计算最优转账方案 |
| POST | `/api/sessions/{id}/settle` | 结账 |
| POST | `/api/sessions/{id}/unsettle` | 取消结账 |

## 七、数据模型

```
players (1) ──< bills (N)
game_sessions (1) ──< bills (N)
```

- **`players`**：`id`, `name`(唯一), `created_at`
- **`game_sessions`**：`id`, `game_date`, `game_time`, `image_path`, `raw_text`, `price_per_point`, `settled`, `settled_at`, `created_at`
- **`bills`**：`id`, `game_session_id`(可空=零散账单), `game_date`, `player_id`, `win_points`, `landlord_count`, `landlord_win`, `farmer_count`, `farmer_win`, `remark`, `created_at`

### 核心设计决策

- 数据单位是**分数**而非金额：存储 `win_points`，结账时输入「每分单价」才换算为金额。
- `bills.game_date` 为冗余字段，与 `game_sessions.game_date` 同步，简化按日统计。
- 整局总分必须为 0（零和校验，误差 < 0.01）。

## 八、结账算法

贪心法求最少转账次数：汇总每个玩家总分数 → 正分为赢家、负分取绝对值作为输家 → 双方按金额降序 → 每次取最大赢家与最大输家，转 `min(赢额, 输额)` → 一方清零后继续，直到清算完毕。

## 九、约定与注意

- 所有界面文案为**中文**。
- 使用 `uv` 管理 Python 依赖（**不要用 pip**）；`uv add` 安装、`uv run` 运行。
- 每个数据库函数独立打开/关闭连接（SQLite WAL 模式）。
- `data/`（数据库与截图）已加入 `.gitignore`，`.env` 含密钥不入库。
- 截图存储在 `data/images/{uuid8}_{原文件名}`。

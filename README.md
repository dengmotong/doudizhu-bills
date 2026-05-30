# 🃏 斗地主账单系统

基于 Streamlit + OpenAI 兼容 API（Mimo 等）的斗地主对局账单管理工具。上传结算截图 → AI 自动识别 → 记录分数 → 统计分析 → 结账计算最优转账方案。

---

## 一、项目结构

```
doudizhu-bills/
├── app.py                  # 首页概览（入口）
├── config.py               # 全局配置（DB路径、API Key、模型名）
├── database.py             # 数据库层（SQLite CRUD + 统计查询）
├── llm.py                  # OpenAI 兼容 API 图像识别（Mimo 等）
├── pyproject.toml          # 项目依赖（uv 管理）
├── uv.lock                 # 依赖锁定文件
├── pages/
│   ├── 1_账单上传.py        # 批量上传截图 + AI 识别 + 编辑保存
│   ├── 2_账单记录.py        # 查看/编辑/删除历史账单
│   ├── 3_玩家管理.py        # 玩家增删改
│   ├── 4_统计分析.py        # 累计/按月/按日/按局四种统计策略
│   └── 5_结账.py            # 选择对局 → 计算最优转账 → 标记已结账
├── data/
│   ├── bills.db            # SQLite 数据库（WAL 模式）
│   └── images/             # 上传截图存储（UUID前缀_原文件名）
└── README.md
```

---

## 二、快速启动

```bash
# 安装依赖（使用 uv）
uv sync

# 设置环境变量（可选，也可以在页面中输入）
set OPENAI_API_KEY=sk-xxxxx
set OPENAI_BASE_URL=https://api.xiaomimimo.com/v1
set OPENAI_MODEL=mimo-v2-omni

# 启动
uv run streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

---

## 三、技术栈

| 组件 | 技术 |
|------|------|
| 前端框架 | Streamlit（多页面架构，`pages/` 目录自动注册侧边栏） |
| 数据库 | SQLite（WAL 模式，路径 `data/bills.db`） |
| AI 识别 | Xiaomi MiMo（`mimo-v2-omni`，通过 openai SDK 调用） |
| 图表 | Plotly（柱状图、折线图、饼图、面积图） |
| 数据处理 | Pandas |
| 图像处理 | Pillow |
| 包管理 | uv（`pyproject.toml` + `uv.lock`） |
| Python 版本 | ≥ 3.13 |

---

## 四、数据模型

### 4.1 ER 关系

```
players (1) ──< bills (N)
game_sessions (1) ──< bills (N)
```

### 4.2 表结构

#### `players` — 玩家表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `name` | TEXT UNIQUE | 玩家昵称（全局唯一） |
| `created_at` | TEXT | 创建时间（本地时间） |

#### `game_sessions` — 对局会话表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `game_date` | TEXT | 游戏日期 `YYYY-MM-DD`（从文件名解析或默认今天） |
| `game_time` | TEXT | 游戏时间 `HH:MM`（从文件名解析） |
| `image_path` | TEXT | 截图文件名（存储在 `data/images/`） |
| `raw_text` | TEXT | AI 识别原始结果（JSON 字符串） |
| `price_per_point` | REAL | 每分单价（结账时设置，默认 5.0） |
| `settled` | INTEGER | 是否已结账（0/1） |
| `settled_at` | TEXT | 结账时间 |
| `created_at` | TEXT | 记录创建时间 |

#### `bills` — 账单明细表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `game_session_id` | INTEGER FK | 关联对局（允许 NULL，处理零散账单） |
| `game_date` | TEXT | 冗余存储日期（与 session 同步，方便按日统计） |
| `player_id` | INTEGER FK | 关联玩家 |
| `win_points` | REAL | 输赢分数（正=赢，负=输，**不是金额**） |
| `landlord_count` | INTEGER | 地主总次数 |
| `landlord_win` | INTEGER | 地主赢次 |
| `farmer_count` | INTEGER | 农民总次数 |
| `farmer_win` | INTEGER | 农民赢次 |
| `remark` | TEXT | 备注 |
| `created_at` | TEXT | 记录创建时间 |

### 4.3 核心设计决策

- **数据单位是「分数」而非「金额」**：上传和存储的是 `win_points`（输赢分数），结账时输入「每分单价」才换算为金额。这样同一组数据可以按不同单价结账。
- **`bills.game_date` 冗余字段**：与 `game_sessions.game_date` 保持同步，简化按日统计的 SQL 查询（无需 JOIN session）。
- **`game_session_id` 允许 NULL**：兼容零散账单，`get_bills_grouped_by_session` 会将 NULL 的归入「未分组」。
- **整局总分校验**：上传和编辑时验证所有玩家 `win_points` 之和必须为 0（零和博弈）。

---

## 五、功能模块详解

### 5.1 📤 账单上传（`pages/1_账单上传.py`）

**核心流程：上传截图 → AI 识别 → 编辑 → 保存**

#### 批量上传流程

```
选择多张截图 → 预览缩略图
      ↓
点击「开始识别全部」
      ↓
逐张识别（每张识别完立即 rerun，已完成的可查看编辑）
      ↓
逐张编辑 + 单条保存 / 一键批量保存
```

#### 关键实现

- **不阻塞 UI 的识别**：识别逻辑放在页面顶部（渲染之前），用 `st.empty()` 显示轻量状态提示。识别完一张后 `st.rerun()`，UI 重新渲染时已完成的结果可立即查看编辑。
- **进度提示**：顶部显示 `已识别 N | 识别中 1 | 待识别 M | 失败 K`。
- **文件名解析**：从截图文件名中用正则提取日期时间（格式 `Screenshot_YYYY-MM-DD-HH-MM-SS-...`）。
- **图片存储**：`data/images/{UUID hex 8位}_{原文件名}`，保留原始文件名便于溯源。
- **新玩家自动创建**：识别出的昵称如果不在玩家列表中，保存时自动创建。
- **重试机制**：识别失败的条目可单独重试。

#### 校验规则

- 所有玩家 `win_points` 之和必须为 0（误差 < 0.01）
- 批量保存时先收集所有数据并验证，全部通过才保存

### 5.2 📋 账单记录（`pages/2_账单记录.py`）

**功能：查看 / 编辑 / 删除历史账单**

#### 主要特性

- **按局分组展示**：每个 `game_sessions` 显示为一个卡片，包含日期、时间、各玩家分数摘要
- **便捷删除**：每个局顶部有 🗑️ 按钮，无需展开即可删除整局
- **排序切换**：支持「最新优先」和「最早优先」两种排序
- **展开编辑**：展开后可编辑每条账单的玩家、分数、地主/农民数据
- **编辑校验**：编辑时同样验证整局总分必须为 0
- **已结账标识**：已结账的局显示 ✅ 和金额信息

### 5.3 👥 玩家管理（`pages/3_玩家管理.py`）

**功能：玩家增删改**

- 添加玩家（全局唯一昵称）
- 删除玩家（级联删除关联账单）
- 重命名玩家

### 5.4 📊 统计分析（`pages/4_统计分析.py`）

**四种统计策略：**

| 策略 | 图表 | 说明 |
|------|------|------|
| **累计排名** | 柱状图 + 饼图 | 所有玩家累计分数、对局数、地主/农民胜率 |
| **按月统计** | 分组柱状图 + 折线图 | 月度分数对比和趋势 |
| **按日统计** | 分组柱状图 + 折线图 + 堆叠面积图 | 每日分数、趋势、累计占比 |
| **按局统计** | 展开卡片 + 赢家饼图 | 每局各玩家分数详情 |

#### 数据来源

| 统计策略 | database.py 函数 | SQL 分组依据 |
|----------|------------------|-------------|
| 累计排名 | `get_player_cumulative_stats()` | GROUP BY player |
| 按月统计 | `get_player_stats_by_month()` | GROUP BY player, strftime('%Y-%m') |
| 按日统计 | `get_player_stats_by_day()` | GROUP BY player, game_date |
| 按局统计 | `get_player_stats_by_session()` | GROUP BY session |

### 5.5 💰 结账（`pages/5_结账.py`）

**功能：选择对局 → 计算最优转账方案 → 标记已结账**

#### 最优转账算法

贪心算法求最少转账次数：
1. 汇总每个玩家的总分数
2. 正分为赢家，负分取绝对值为输家
3. 赢家和输家各按金额从大到小排序
4. 每次取当前最大的赢家和输家，转 `min(赢额, 输额)`
5. 一方清零后移动到下一个，直到全部清算完毕

```python
# 核心逻辑（pages/5_结账.py → calculate_settlement）
transfers.append({
    "from": loser_name,
    "to": winner_name,
    "points": round(transfer_pts, 2),
    "money": round(transfer_pts * price_per_point, 2),
})
```

#### 结账模式

- **批量结账**：多选对局，合并计算分数，统一按单价结账
- **单局结账**：展开单局，查看分数和转账方案后结账
- **取消结账**：已结账的局可取消，恢复为待结账状态

---

## 六、AI 识别模块（`llm.py`）

### 调用方式

```python
from llm import recognize_bill
result = recognize_bill(image, api_key="sk-xxx")
```

### 识别结果结构

```json
{
    "game_date": "2024-01-15",
    "game_time": "14:30",
    "players": [
        {
            "name": "玩家昵称",
            "win_points": 5.0,
            "landlord_count": 2,
            "landlord_win": 1,
            "farmer_count": 1,
            "farmer_win": 1
        }
    ]
}
```

### Prompt 设计要点

1. **严格 JSON 输出**：要求只返回 JSON，不包含其他文字
2. **昵称识别规则**：详细说明哪些不是昵称（"大赢家"、"地主"、"农民"等系统标签）
3. **字段默认值**：地主/农民字段缺失时填 0，日期缺失时用今天
4. **Markdown 代码块清理**：LLM 可能返回被 ` ```json ``` ` 包裹的 JSON，代码中已处理

### 常见识别问题

- **昵称误识别**：系统评语标签（"大赢家"、"MVP"）可能被误认为玩家昵称
- **分数识别偏差**：负号、小数点可能被遗漏
- **日期时间**：截图中如果没有明确日期时间，会从文件名解析

---

## 七、数据库操作（`database.py`）

### 常用函数速查

| 函数 | 用途 |
|------|------|
| `get_all_players()` | 获取所有玩家 |
| `add_player(name)` | 添加玩家，返回 ID |
| `delete_player(player_id)` | 删除玩家（级联删除账单） |
| `rename_player(player_id, new_name)` | 重命名玩家 |
| `add_game_session(...)` | 创建对局会话，返回 session ID |
| `add_bills(bills_list)` | 批量插入账单 |
| `get_all_game_sessions()` | 获取所有对局（按日期倒序） |
| `get_session_bills(session_id)` | 获取某局的所有账单 |
| `get_bills_grouped_by_session()` | 按局分组返回（跳过无账单的 session） |
| `update_bill(...)` | 更新单条账单 |
| `delete_bill(bill_id)` | 删除单条账单 |
| `delete_game_session(session_id)` | 删除对局（级联删除账单） |
| `settle_game_session(session_id, ppp)` | 标记已结账 |
| `unsettle_game_session(session_id)` | 取消结账 |
| `get_player_cumulative_stats()` | 累计统计 |
| `get_player_stats_by_month()` | 按月统计 |
| `get_player_stats_by_day()` | 按日统计 |
| `get_player_stats_by_session()` | 按局统计 |
| `get_settled_sessions_with_money()` | 已结账 + 金额 |

### 迁移机制

`_migrate()` 函数通过 `ALTER TABLE ... ADD COLUMN` 逐字段尝试添加，利用 `sqlite3.OperationalError` 静默跳过已存在的字段。旧的 `win_amount` 字段会自动迁移到 `win_points`。

---

## 八、Streamlit 页面架构

Streamlit 多页面应用规则：
- `app.py` 是首页（`/`）
- `pages/` 目录下的文件自动注册为侧边栏页面
- 文件名前的数字控制排序：`1_账单上传.py` 排在 `2_账单记录.py` 前面
- 每个页面独立调用 `st.set_page_config()`，必须是页面第一个 Streamlit 命令

### session_state 使用

| Key | 类型 | 说明 |
|-----|------|------|
| `api_key` | str | API Key |
| `base_url` | str | API Base URL |
| `model` | str | 模型名 |
| `batch_items` | list[dict] | 批量上传的识别状态列表 |
| `date_{idx}` | date | 第 idx 张图的日期 |
| `time_{idx}` | str | 第 idx 张图的时间 |
| `pl_{idx}_{name}` | str | 第 idx 张图中某玩家选择的昵称 |
| `pts_{idx}_{name}` | float | 第 idx 张图中某玩家的分数 |
| `lc/lw/fc/fw_{idx}_{name}` | int | 地主/农民次数和赢次 |
| `batch_select` | list[int] | 结账页选中的对局 ID 列表 |
| `default_ppp` | float | 每分单价 |

---

## 九、配置说明（`config.py`）

```python
BASE_DIR = Path(__file__).parent                # 项目根目录
DB_PATH = BASE_DIR / "data" / "bills.db"        # 数据库路径
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")    # API Key
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")  # API 地址
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "mimo-v2-omni")  # 模型名
```

API Key / Base URL / 模型名 优先级：环境变量 > 页面输入框 > config.py 默认值。

---

## 十、注意事项与已知问题

### 开发注意

1. **不要用 `pip`**：项目使用 `uv` 管理依赖，安装用 `uv add`，运行用 `uv run`
2. **SQLite WAL 模式**：`PRAGMA journal_mode=WAL`，支持读写并发
3. **数据库连接**：每个函数独立获取和关闭连接，不要在函数间共享连接
4. **Streamlit rerun**：每次交互会重新执行整个脚本，`st.session_state` 是唯一持久状态
5. **st.spinner 阻塞**：`with st.spinner()` 会阻塞其内部所有 UI 渲染，识别等耗时操作应放在页面顶部 UI 之前

### 已知问题

1. **AI 昵称识别**：系统评语标签（"大赢家"、"MVP"）有时被误认为玩家昵称，需要人工校验
2. **负号识别**：AI 有时遗漏分数的负号，需检查
3. **同名玩家**：如果玩家昵称不同但被识别为相同名字，会合并分数。使用「玩家管理」重命名可解决
4. **session_state 清理**：`batch_items` 在上传页切换图片后可能残留旧数据（已有清理逻辑，但极端情况可能残留）
5. **game_date 冗余**：`bills.game_date` 与 `game_sessions.game_date` 需保持同步，编辑账单日期时需同步更新

### 数据安全

- `data/` 目录（含数据库和截图）已加入 `.gitignore`，不会被提交
- API Key 通过环境变量配置，不要硬编码在代码中
- 数据库使用 WAL 模式，异常退出不会损坏数据

---

## 十一、扩展方向

- [ ] 支持更多截图格式和批量拖拽上传
- [ ] AI 识别结果缓存（相同图片不重复调用 API）
- [ ] 导出功能（CSV / Excel / PDF）
- [ ] 多房间支持（按房间分组统计）
- [ ] 月度/周度自动汇总报表
- [ ] 用户认证（多用户独立账本）
- [ ] 移动端适配优化

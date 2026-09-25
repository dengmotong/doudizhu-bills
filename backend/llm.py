"""OpenAI 兼容 API 图像识别（Mimo 等）：识别斗地主结算截图并返回结构化 JSON。"""
import base64
import json
from io import BytesIO

from PIL import Image

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def encode_image_base64(image: Image.Image) -> str:
    """将 PIL Image 编码为 base64 字符串"""
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _to_rate(value, default: float | None = None) -> float | None:
    """把 LLM 返回的胜率归一化为 0-100 的百分数。

    兼容 "63%" / "63" / 0.63 三种写法；无法解析时返回 default。
    """
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip().rstrip("%").strip()
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return default
    if rate < 0:
        return default
    # 0-1 之间视为小数比例（如 0.63），但 0 与 1 存在歧义：
    # 胜率 1 表示 100% 更常见，而 1% 的胜率极罕见，故 1 按 100% 处理。
    if 0 < rate <= 1:
        rate *= 100
    return min(rate, 100.0)


def _to_count(value) -> int:
    try:
        return max(int(round(float(value))), 0)
    except (TypeError, ValueError):
        return 0


def apply_win_rates(result: dict) -> dict:
    """用「盘数 × 胜率」在本地计算胜负盘数，不信任 LLM 直接给出的赢次。

    这样胜负盘数由程序运算，避免模型在算术上出错；
    同时把推导出的胜率回填到结果里，便于前端展示与核对。
    """
    for p in result.get("players", []):
        landlord_count = _to_count(p.get("landlord_count"))
        farmer_count = _to_count(p.get("farmer_count"))
        p["landlord_count"] = landlord_count
        p["farmer_count"] = farmer_count

        l_rate = _to_rate(p.get("landlord_rate"))
        f_rate = _to_rate(p.get("farmer_rate"))

        if l_rate is None:
            # 兼容：模型仍返回赢次时，反推胜率；否则视为 0
            l_rate = (p["landlord_win"] / landlord_count * 100) if landlord_count and p.get("landlord_win") else 0.0
        if f_rate is None:
            f_rate = (p["farmer_win"] / farmer_count * 100) if farmer_count and p.get("farmer_win") else 0.0

        p["landlord_rate"] = round(l_rate, 1)
        p["farmer_rate"] = round(f_rate, 1)

        # 胜负盘数一律由程序计算，并夹在 [0, 盘数] 区间内
        p["landlord_win"] = min(landlord_count, int(round(landlord_count * l_rate / 100)))
        p["farmer_win"] = min(farmer_count, int(round(farmer_count * f_rate / 100)))

    return result


def recognize_bill(
    image: Image.Image,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    player_names: list[str] | None = None,
) -> dict:
    """
    使用 OpenAI 兼容 API（如 Mimo）识别斗地主结算截图。

    参数:
        image: PIL Image 对象
        api_key: API Key（为空则使用 config 中的默认值）
        base_url: API 地址（为空则使用 config 中的默认值）
        model: 模型名（为空则使用 config 中的默认值）
        player_names: 已知玩家昵称列表，帮助 LLM 精准匹配现有用户

    返回:
        {
            "game_date": "2024-01-15",
            "game_time": "14:30",
            "players": [
                {"name": "玩家昵称", "win_points": 5.0,
                 "landlord_count": 2, "landlord_rate": 50.0, "landlord_win": 1,
                 "farmer_count": 1, "farmer_rate": 100.0, "farmer_win": 1}, ...
            ]
        }

    说明:
        LLM 只负责「看」——识别盘数与胜率；胜负盘数由 apply_win_rates()
        在本地用「盘数 × 胜率」计算，避免模型算术出错。
    """
    key = api_key or OPENAI_API_KEY
    url = base_url or OPENAI_BASE_URL
    mdl = model or OPENAI_MODEL

    if not key:
        raise ValueError("请配置 API Key（环境变量 OPENAI_API_KEY 或在页面中输入）")
    if not url:
        raise ValueError("请配置 Base URL（环境变量 OPENAI_BASE_URL 或在页面中输入）")

    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=url)

    img_base64 = encode_image_base64(image)

    from datetime import date

    today = date.today().strftime("%Y-%m-%d")

    system_msg = (
        f"You are MiMo, an AI assistant developed by Xiaomi. "
        f"Today is {today}. "
        f"Please respond in JSON only, no extra text."
    )

    prompt = """请仔细识别这张斗地主游戏结算截图，分析每个玩家的输赢情况和对局数据。

请严格按以下 JSON 格式返回结果（不要包含任何其他文字，只返回 JSON）：
{
    "game_date": "YYYY-MM-DD 格式的日期",
    "game_time": "HH:MM 格式的时间",
    "players": [
        {
            "name": "玩家昵称",
            "win_points": 5.0,
            "landlord_count": 2,
            "landlord_rate": 50.0,
            "farmer_count": 1,
            "farmer_rate": 100.0
        }
    ]
}

=== 重要：如何识别玩家昵称 ===

1. 玩家昵称是每个人自己的名字/ID，通常显示在头像旁边或列表的左侧列
2. 以下内容绝对不是玩家昵称，千万不要识别为名字：
   - "大赢家"、"大输家"、"最佳配合"、"MVP" 等描述性文字（这些是系统评语标签）
   - "地主"、"农民"、"地主胜"、"农民胜" 等角色描述
   - "本局得分"、"本局输赢"、"总战绩" 等标题文字
   - 金额数字本身（如 "+5.00"、"-3.00"）
   - 任何看起来像统计标签而非个人名字的文字
3. 昵称长度可以是任意的——1个字符（如"-"、"A"）到十几个字符都可能是真实昵称，不要因为短就忽略
4. 典型的昵称特征：包含字母/数字/中文/符号，每个玩家一个，出现在头像/玩家列表旁边
5. 如果不确定某个文字是昵称还是标签，请观察它是否出现在头像/玩家列表旁边

=== 字段说明 ===
- win_points: 每个玩家的输赢分数（不是金额），赢为正数，输为负数，用数字
- landlord_count: 该玩家当本地主的盘数（没有显示则填 0）
- landlord_rate: 该玩家当本地主的胜率，用百分数数字表示（例如 63% 填 63，不要填赢的盘数）
- farmer_count: 该玩家当农民的盘数
- farmer_rate: 该玩家当农民的胜率，用百分数数字表示（例如 40% 填 40）
- 如果截图中没有地主/农民的详细数据，这四个字段都填 0
- 如果截图中有日期请使用截图中的日期，没有则使用今天的日期
- 如果截图中有时间请使用截图中的时间，没有则留空字符串

=== 重要：只识别，不要做算术 ===
- 请只忠实抄录截图上的「盘数」和「胜率」，不要自行计算赢的盘数，也不要输出 landlord_win / farmer_win 字段。
- 胜率请直接抄录截图显示的数字；如果截图只显示赢的盘数而没有胜率，请留空或填 0，不要换算。"""

    if player_names:
        prompt += f"""

=== 已知玩家列表（请优先匹配） ===
以下是在系统中已有的玩家昵称列表：
{", ".join(player_names)}

截图中的玩家昵称应优先匹配到这些已知昵称。
如果截图中的昵称与列表中某个昵称高度相似，请使用列表中精确的昵称，不要创建新的变体。
特别注意以下容易混淆的字符：短横线 -、中文破折号 —、汉字"一"、下划线 _ 等。"""

    try:
        response = client.chat.completions.create(
            model=mdl,
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            max_completion_tokens=8192,
        )
    except TypeError:
        # 部分 API 不支持 max_completion_tokens，回退到 max_tokens
        response = client.chat.completions.create(
            model=mdl,
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            max_tokens=8192,
        )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            f"API 返回内容为空，响应: {response.model_dump_json(indent=2)}"
        )

    # 提取 JSON（可能被 markdown 代码块包裹）
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    result = json.loads(content)

    # 验证结构
    if "game_date" not in result or "players" not in result:
        raise ValueError("识别结果格式不正确，缺少必要字段")

    # 去除玩家名字首尾空白
    for p in result["players"]:
        p["name"] = p.get("name", "").strip()

    # 确保每个 player 都有地主/农民字段
    for p in result["players"]:
        p.setdefault("landlord_count", 0)
        p.setdefault("farmer_count", 0)

    result.setdefault("game_time", "")

    # 胜负盘数由程序计算，不用模型给的结果
    apply_win_rates(result)

    return result

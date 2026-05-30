import base64
import json
from io import BytesIO

from PIL import Image

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def encode_image_base64(image: Image.Image) -> str:
    """将 PIL Image 编码为 base64 字符串"""
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def recognize_bill(
    image: Image.Image,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> dict:
    """
    使用 OpenAI 兼容 API（如 Mimo）识别斗地主结算截图。

    参数:
        image: PIL Image 对象
        api_key: API Key（为空则使用 config 中的默认值）
        base_url: API 地址（为空则使用 config 中的默认值）
        model: 模型名（为空则使用 config 中的默认值）

    返回:
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
                },
                ...
            ]
        }
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
            "landlord_win": 1,
            "farmer_count": 1,
            "farmer_win": 1
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
- landlord_count: 该玩家当本地主的次数（没有显示则填 0）
- landlord_win: 该玩家当本地主赢的次数
- farmer_count: 该玩家当农民的次数
- farmer_win: 该玩家当农民赢的次数
- 如果截图中没有地主/农民的详细数据，这四个字段都填 0
- 如果截图中有日期请使用截图中的日期，没有则使用今天的日期
- 如果截图中有时间请使用截图中的时间，没有则留空字符串"""

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
        # 打印完整响应用于调试
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

    # 确保每个 player 都有地主/农民字段
    for p in result["players"]:
        p.setdefault("landlord_count", 0)
        p.setdefault("landlord_win", 0)
        p.setdefault("farmer_count", 0)
        p.setdefault("farmer_win", 0)

    result.setdefault("game_time", "")

    return result

"""ダイスロールと CoC キャラクター作成の計算を行います。"""

import logging
from dataclasses import dataclass, field
from random import randint

logger = logging.getLogger(__name__)

# フリーズを防ぐため、この値以上の数値は扱いません (5 桁以上)。
MAX_NUMBER = 10000
# 目標値判定モードを示す接頭辞です (例: "xxx50 1d100")。
TARGET_PREFIX = "xxx"

TOO_BIG_MESSAGE = "BotError: Too big number was used."
INVALID_INPUT_MESSAGE = "BotError: Please check your input or blame the maker."


@dataclass
class RollResult:
    """ダイス式の計算結果です。

    total は合計値です。式が不正な場合はエラーメッセージの文字列になります。
    terms は各項の結果 ("+18" や "-3" など) です。
    success は目標値判定モードでの成否です。
    """

    total: int | str
    terms: list[str] = field(default_factory=list)
    success: bool = False


def random_int(digit: int) -> int:
    """digit 桁の乱数を返します。"""
    return randint(10 ** (digit - 1), 10**digit - 1)


def is_too_big(num: int) -> bool:
    """数値が大きすぎる (5 桁以上) 場合に True を返します。"""
    return num >= MAX_NUMBER


def simple_dice_roll(count: int | str, sides: int | str) -> int | None:
    """countDsides の合計を返します。数値が大きすぎる場合は None を返します。"""
    count = int(count)
    sides = int(sides)
    if is_too_big(count) or is_too_big(sides):
        return None
    return roll(count, sides)


def roll(count: int, sides: int) -> int:
    """sides 面ダイスを count 個振った合計を返します (上限確認は行いません)。"""
    return sum(randint(1, sides) for _ in range(count))


def expression_dice_roll(expression: str, use_target_number: bool = False) -> RollResult:
    """「1d100」「2d4 -1d4」「1d6 3」「10 -1」のような式を計算します。

    use_target_number が True で、式が「xxx50 1d100」のように TARGET_PREFIX と
    目標値から始まる場合は、合計が目標値以下かどうかを success に設定します。
    """
    terms_in = expression.lower().split(" ")
    result = RollResult(0)
    total = 0
    target_number = 0
    try:
        if use_target_number and terms_in[0].startswith(TARGET_PREFIX):
            target_number = int(terms_in.pop(0)[len(TARGET_PREFIX) :])

        for term in terms_in:
            negative = term.startswith("-")
            body = term[1:] if negative else term
            if "d" in body:
                count, sides = body.split("d")
                value = simple_dice_roll(count, sides)
                if not value:
                    result.total = TOO_BIG_MESSAGE
                    break
            else:
                value = int(body)
                if is_too_big(value):
                    result.total = TOO_BIG_MESSAGE
                    break
            total = total - value if negative else total + value
            result.terms.append(("-" if negative else "+") + str(value))
        else:
            result.total = total

        if use_target_number and isinstance(result.total, int):
            result.success = result.total <= target_number
    except ValueError as error:
        logger.debug("invalid dice expression %r: %s", expression, error)
        result.total = INVALID_INPUT_MESSAGE
    return result


def coc_charamake() -> str:
    """CoC (6 版) のキャラクター能力値を作成して文字列で返します。"""
    stats = {
        "STR": roll(3, 6),
        "CON": roll(3, 6),
        "POW": roll(3, 6),
        "DEX": roll(3, 6),
        "APP": roll(3, 6),
        "SIZ": roll(2, 6) + 6,
        "INT": roll(2, 6) + 6,
        "EDU": roll(3, 6) + 3,
    }
    return " ".join(f"{name}:{value}" for name, value in stats.items())

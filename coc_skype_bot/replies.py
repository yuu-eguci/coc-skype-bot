"""発言内容から bot の返答文を作成します。"""

from collections.abc import Callable
from dataclasses import dataclass

from coc_skype_bot import dice

OPEN_MESSAGE = "SKYPE BOT MESSAGE: Now opened the Skype Bot!"
CLOSE_MESSAGE = "You closed the Bot. Bye bye!"
ERROR_MESSAGE = "SKYPE BOT MESSAGE: Got an error! Close the Skype Bot..."

# 能力値コマンドと、その値の振り方です。
STAT_ROLLS: dict[str, Callable[[], int]] = {
    "str": lambda: dice.roll(3, 6),
    "con": lambda: dice.roll(3, 6),
    "pow": lambda: dice.roll(3, 6),
    "dex": lambda: dice.roll(3, 6),
    "app": lambda: dice.roll(3, 6),
    "siz": lambda: dice.roll(2, 6) + 6,
    "int": lambda: dice.roll(2, 6) + 6,
    "edu": lambda: dice.roll(3, 6) + 3,
}


@dataclass(frozen=True)
class Reply:
    """返答です。end が True の場合、bot は返答を送信した後に終了します。"""

    text: str
    end: bool = False


def help_message(key: str) -> str:
    """ヘルプ文を返します。"""
    return (
        "Dice roll format example: '1d100', '2d4 -1d4', '1d6 3' or '10 -1'. "
        f"Success check: '{dice.TARGET_PREFIX}50 1d100' (success if the result <= 50). "
        "You can use also commands: charamake str con pow dex app siz int edu end help. "
        f"Write one of them after '{key} '. :::Written by Midoriiro:::"
    )


def build_reply(body: str, key: str) -> Reply:
    """「{key} {command}」形式の発言に対する返答を「{command} {結果}」の形で返します。"""
    command = " ".join(body[len(key) + 1 :].split())
    name = command.lower()
    end = False
    if name in ("", "help"):
        result = help_message(key)
    elif name == "charamake":
        result = dice.coc_charamake()
    elif name in STAT_ROLLS:
        result = f"{name.upper()}: {STAT_ROLLS[name]()}"
    elif name == "end":
        result = CLOSE_MESSAGE
        end = True
    elif name.startswith(dice.TARGET_PREFIX):
        roll = dice.expression_dice_roll(command, use_target_number=True)
        verdict = "SUCCESS!" if roll.success else "FAILED.."
        result = f"Result: {roll.total} {roll.terms} {verdict}"
    else:
        roll = dice.expression_dice_roll(command)
        result = f"Result: {roll.total} {roll.terms}"
    return Reply(f"{command} {result}".lstrip(), end)

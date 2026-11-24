"""発言内容から bot の返答文を作成します。"""

from coc_skype_bot import dice

OPEN_MESSAGE = "SKYPE BOT MESSAGE: Now opened the Skype Bot!"
CLOSE_MESSAGE = "You closed the Bot. Bye bye!"
ERROR_MESSAGE = "SKYPE BOT MESSAGE: Got an error! Close the Skype Bot..."


def help_message(key: str) -> str:
    """ヘルプ文を返します。"""
    return (
        "Dice roll format example: '1d100', '2d4 -1d4', '1d6 3' or '10 -1'. "
        "You can use also commands: charamake str con pow dex app siz int edu end help. "
        f"Write one of them after '{key} '. :::Written by Midoriiro:::"
    )


def build_reply(body: str, key: str) -> str:
    """「{key} {command}」形式の発言に対する返答を「{command} {結果}」の形で返します。"""
    command = body[len(key) + 1 :]
    if command in "charamake":
        result = dice.coc_charamake()
    elif command in "str":
        result = f"STR: {dice.roll(3, 6)}"
    elif command in "con":
        result = f"CON: {dice.roll(3, 6)}"
    elif command in "pow":
        result = f"POW: {dice.roll(3, 6)}"
    elif command in "dex":
        result = f"DEX: {dice.roll(3, 6)}"
    elif command in "app":
        result = f"APP: {dice.roll(3, 6)}"
    elif command in "siz":
        result = f"SIZ: {dice.roll(2, 6) + 6}"
    elif command in "int":
        result = f"INT: {dice.roll(2, 6) + 6}"
    elif command in "edu":
        result = f"EDU: {dice.roll(3, 6) + 3}"
    elif command in "end":
        result = CLOSE_MESSAGE
    elif command in "help":
        result = help_message(key)
    elif command.startswith(dice.TARGET_PREFIX):
        roll = dice.expression_dice_roll(command, use_target_number=True)
        verdict = "SUCCESS!" if roll.success else "FAILED.."
        result = f"Result: {roll.total} {roll.terms} {verdict}"
    else:
        roll = dice.expression_dice_roll(command)
        result = f"Result: {roll.total} {roll.terms}"
    return f"{command} {result}"


def is_end_reply(reply: str) -> bool:
    """返答が bot の終了を示すかどうかを返します。"""
    return reply == f"end {CLOSE_MESSAGE}"

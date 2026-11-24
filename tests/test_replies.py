"""発言から返答を作成する処理のテストです。"""

import pytest

from coc_skype_bot import dice, replies


@pytest.fixture
def fixed_dice(monkeypatch):
    monkeypatch.setattr(dice, "randint", lambda low, high: high)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("str", "str STR: 18"),
        ("con", "con CON: 18"),
        ("pow", "pow POW: 18"),
        ("dex", "dex DEX: 18"),
        ("app", "app APP: 18"),
        ("siz", "siz SIZ: 18"),
        ("int", "int INT: 18"),
        ("edu", "edu EDU: 21"),
        ("STR", "STR STR: 18"),
        ("charamake", "charamake STR:18 CON:18 POW:18 DEX:18 APP:18 SIZ:18 INT:18 EDU:21"),
        ("1d100", "1d100 Result: 100 ['+100']"),
        ("2d4 -1d4", "2d4 -1d4 Result: 4 ['+8', '-4']"),
        ("xxx50 1d100", "xxx50 1d100 Result: 100 ['+100'] FAILED.."),
        ("xxx100 1d100", "xxx100 1d100 Result: 100 ['+100'] SUCCESS!"),
    ],
)
def test_build_reply_commands(fixed_dice, command, expected):
    reply = replies.build_reply(f"xxx {command}", "xxx")
    assert reply.text == expected
    assert reply.end is False


@pytest.mark.parametrize("command", ["c", "e", "a", "d", "st", "en", "nd", "charamak"])
def test_partial_command_is_not_treated_as_command(command):
    reply = replies.build_reply(f"xxx {command}", "xxx")
    assert reply.text == f"{command} Result: {dice.INVALID_INPUT_MESSAGE} []"
    assert reply.end is False


@pytest.mark.parametrize("body", ["xxx end", "xxx End", "xxx  end "])
def test_end_command_requests_stop(body):
    reply = replies.build_reply(body, "xxx")
    assert reply.text.endswith(replies.CLOSE_MESSAGE)
    assert reply.end is True


@pytest.mark.parametrize("body", ["xxx help", "xxx ", "xxx"])
def test_help_and_empty_command_show_help(body):
    reply = replies.build_reply(body, "xxx")
    assert reply.text.endswith(replies.help_message("xxx"))


def test_help_mentions_target_check():
    assert "xxx50 1d100" in replies.help_message("bot")


def test_extra_spaces_are_ignored(fixed_dice):
    assert replies.build_reply("xxx  1d6   3 ", "xxx").text == "1d6 3 Result: 9 ['+6', '+3']"

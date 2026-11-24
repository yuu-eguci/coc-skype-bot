"""ダイス計算の挙動を確認するテストです。"""

import pytest

from coc_skype_bot import dice


@pytest.fixture
def fixed_dice(monkeypatch):
    """randint を「最大値を返す」決定的な関数に差し替えます。"""
    monkeypatch.setattr(dice, "randint", lambda low, high: high)


def test_simple_dice_roll_sums_each_die(fixed_dice):
    assert dice.simple_dice_roll(3, 6) == 18


def test_simple_dice_roll_stays_in_range():
    for _ in range(200):
        assert 2 <= dice.simple_dice_roll(2, 6) <= 12


def test_simple_dice_roll_rejects_five_digit_numbers():
    assert dice.simple_dice_roll(10000, 6) is None
    assert dice.simple_dice_roll(1, 10000) is None


@pytest.mark.parametrize(
    ("expression", "total", "terms"),
    [
        ("1d100", 100, ["+100"]),
        ("2d4 -1d4", 4, ["+8", "-4"]),
        ("1D6 3", 9, ["+6", "+3"]),
        ("10 -1", 9, ["+10", "-1"]),
    ],
)
def test_expression_dice_roll(fixed_dice, expression, total, terms):
    assert dice.expression_dice_roll(expression) == dice.RollResult(total, terms, False)


@pytest.mark.parametrize(("target", "expected"), [("xxx100", True), ("xxx99", False)])
def test_expression_dice_roll_target_mode(fixed_dice, target, expected):
    result = dice.expression_dice_roll(f"{target} 1d100", use_target_number=True)
    assert result.total == 100
    assert result.success is expected


def test_expression_dice_roll_reports_invalid_input():
    assert dice.expression_dice_roll("abc").total == dice.INVALID_INPUT_MESSAGE


def test_expression_dice_roll_reports_too_big_number():
    assert dice.expression_dice_roll("10000").total == dice.TOO_BIG_MESSAGE


def test_coc_charamake(fixed_dice):
    assert dice.coc_charamake() == "STR:18 CON:18 POW:18 DEX:18 APP:18 SIZ:18 INT:18 EDU:21"


def test_random_int_has_requested_digits():
    for _ in range(50):
        assert len(str(dice.random_int(13))) == 13

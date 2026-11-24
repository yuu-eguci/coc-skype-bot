"""Command (ダイス計算) の現行挙動を固定するテストです。"""

import pytest

import Command as command_module
from Command import Command


@pytest.fixture
def fixed_dice(monkeypatch):
    """randint を「最大値を返す」決定的な関数に差し替えます。"""
    monkeypatch.setattr(command_module, "randint", lambda low, high: high)


def test_simple_dice_roll_sums_each_die(fixed_dice):
    assert Command.simpleDiceRoll(3, 6) == 18


def test_simple_dice_roll_stays_in_range():
    for _ in range(200):
        assert 2 <= Command.simpleDiceRoll(2, 6) <= 12


def test_simple_dice_roll_rejects_five_digit_numbers():
    assert Command.simpleDiceRoll(10000, 6) is False
    assert Command.simpleDiceRoll(1, 10000) is False


@pytest.mark.parametrize(
    ("expression", "result", "result_list"),
    [
        ("1d100", 100, ["+100"]),
        ("2d4 -1d4", 4, ["+8", "-4"]),
        ("1D6 3", 9, ["+6", "+3"]),
        ("10 -1", 9, ["+10", "-1"]),
    ],
)
def test_expression_dice_roll(fixed_dice, expression, result, result_list):
    assert Command.expressionDiceRoll(expression, useResultList=True) == {
        "result": result,
        "resultList": result_list,
        "targetResult": False,
    }


@pytest.mark.parametrize(("target", "expected"), [("xxx100", True), ("xxx99", False)])
def test_expression_dice_roll_target_mode(fixed_dice, target, expected):
    result = Command.expressionDiceRoll(f"{target} 1d100", useResultList=True, useTargetNumber=True)
    assert result["result"] == 100
    assert result["targetResult"] is expected


def test_expression_dice_roll_reports_invalid_input():
    result = Command.expressionDiceRoll("abc", useResultList=True)
    assert result["result"] == "BotError: Please check your input or blame the maker."


def test_expression_dice_roll_reports_too_big_number():
    result = Command.expressionDiceRoll("10000", useResultList=True)
    assert result["result"] == "BotError: Too big number was used."


def test_coc_charamake_string(fixed_dice):
    assert Command.cocCharamake(getString=True) == (
        "STR:18 CON:18 POW:18 DEX:18 APP:18 SIZ:18 INT:18 EDU:21"
    )


def test_random_int_has_requested_digits():
    for _ in range(50):
        assert len(str(Command.randomInt(13))) == 13

"""オフラインで動作確認するためのモード (console / demo) のテストです。"""

import io
import sqlite3

import pytest

from coc_skype_bot import dice, local, replies


@pytest.fixture
def fixed_dice(monkeypatch):
    monkeypatch.setattr(dice, "randint", lambda low, high: high)


def test_stream_sender_writes_lines():
    out = io.StringIO()
    local.StreamSender(out).send("hello")
    assert out.getvalue() == "hello\n"


def test_console_replies_only_to_addressed_lines(fixed_dice):
    out = io.StringIO()
    lines = ["hello\n", "xxx 1d6 3\n", "XXX str\n", "xxx end\n", "xxx 1d100\n"]

    assert local.run_console(lines, out, key="xxx", author="you") == 0

    assert out.getvalue().splitlines() == [
        replies.OPEN_MESSAGE,
        "you->1d6 3 Result: 9 ['+6', '+3']",
        "you->str STR: 18",
        "you->end " + replies.CLOSE_MESSAGE,
    ]


def test_parse_events_skips_comments_and_blank_lines():
    text = "# 合成イベント\n\nalice: xxx 1d100\nbob:hello: world\n"
    assert local.parse_events(text.splitlines()) == [
        ("alice", "xxx 1d100"),
        ("bob", "hello: world"),
    ]


def test_parse_events_rejects_line_without_author():
    with pytest.raises(ValueError, match="line 1"):
        local.parse_events(["xxx 1d100"])


def test_create_synthetic_main_db(tmp_path):
    local.create_synthetic_main_db(tmp_path)
    local.insert_message(tmp_path, 1, "alice", "xxx 1d6", timestamp=10)

    connection = sqlite3.connect(tmp_path / "main.db")
    rows = connection.execute("SELECT id, author, timestamp, body_xml FROM Messages").fetchall()
    connection.close()
    assert rows == [(1, "alice", 10, "xxx 1d6")]


def test_demo_runs_messages_through_database_watch(fixed_dice):
    out = io.StringIO()
    events = [
        ("alice", "xxx 1d100"),
        ("bob", "good evening"),
        ("bob", "xxx xxx50 1d100"),
        ("alice", "xxx end"),
        ("alice", "xxx 1d6"),
    ]

    assert local.run_demo(events, out, key="xxx", delay=0) == 0

    assert out.getvalue().splitlines() == [
        replies.OPEN_MESSAGE,
        "> alice: xxx 1d100",
        "alice->1d100 Result: 100 ['+100']",
        "> bob: good evening",
        "> bob: xxx xxx50 1d100",
        "bob->xxx50 1d100 Result: 100 ['+100'] FAILED..",
        "> alice: xxx end",
        "alice->end " + replies.CLOSE_MESSAGE,
    ]


def test_demo_stops_without_end_command(fixed_dice):
    out = io.StringIO()

    assert local.run_demo([("alice", "xxx 3")], out, key="xxx", delay=0) == 0
    assert out.getvalue().splitlines()[-1] == "alice->3 Result: 3 ['+3']"


def test_default_events_end_the_demo():
    assert local.DEFAULT_EVENTS[-1][1] == "xxx end"


def test_demo_reports_watcher_error_without_waiting_for_timeout(monkeypatch):
    def fail(self, exclude_ids):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(local.SkypeDatabase, "fetch_new_messages", fail)
    out = io.StringIO()

    with pytest.raises(RuntimeError, match="synthetic failure"):
        local.run_demo([("alice", "xxx 3")], out, delay=0, reply_timeout=30)
    assert out.getvalue().splitlines()[-1] == replies.ERROR_MESSAGE

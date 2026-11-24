"""Bot 本体 (メッセージ取得 → 返答 → 送信) のテストです。"""

import threading
import time

import pytest

from coc_skype_bot import replies
from coc_skype_bot.bot import SkypeBot, run_watching
from coc_skype_bot.skype import Message


class FakeSource:
    def __init__(self, messages):
        self.messages = messages
        self.excluded = []

    def fetch_new_messages(self, exclude_ids):
        self.excluded.append(set(exclude_ids))
        return [m for m in self.messages if m.id not in exclude_ids]


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)


def test_greet_sends_open_message_once():
    sender = FakeSender()
    bot = SkypeBot(FakeSource([]), sender, key="xxx")

    bot.greet()
    bot.greet()

    assert sender.sent == [replies.OPEN_MESSAGE]


def test_process_replies_once_per_message():
    source = FakeSource([Message(1, "alice", "xxx 10 -1"), Message(2, "bob", "xxx 3")])
    sender = FakeSender()
    bot = SkypeBot(source, sender, key="xxx")

    assert bot.process() is False
    assert bot.process() is False

    assert sender.sent == ["alice->10 -1 Result: 9 ['+10', '-1']", "bob->3 Result: 3 ['+3']"]
    assert source.excluded[-1] == {1, 2}


def test_process_requests_stop_on_end_command():
    sender = FakeSender()
    bot = SkypeBot(FakeSource([Message(1, "alice", "xxx end")]), sender, key="xxx")

    assert bot.process() is True
    assert sender.sent == ["alice->end " + replies.CLOSE_MESSAGE]


class FailingSource:
    def fetch_new_messages(self, exclude_ids):
        raise RuntimeError("synthetic failure")


def test_run_watching_notifies_error_and_reraises(tmp_path):
    sender = FakeSender()
    with pytest.raises(RuntimeError):
        run_watching(SkypeBot(FailingSource(), sender, key="xxx"), str(tmp_path))
    assert sender.sent == [replies.OPEN_MESSAGE, replies.ERROR_MESSAGE]


def test_run_watching_reacts_to_main_db_change(tmp_path):
    source = FakeSource([])
    sender = FakeSender()
    bot = SkypeBot(source, sender, key="xxx")
    thread = threading.Thread(target=run_watching, args=(bot, str(tmp_path), 30.0))
    thread.start()
    time.sleep(0.5)
    source.messages.append(Message(1, "alice", "xxx end"))
    (tmp_path / "main.db").write_bytes(b"changed")

    thread.join(timeout=10)
    assert not thread.is_alive()
    assert sender.sent[-1] == "alice->end " + replies.CLOSE_MESSAGE

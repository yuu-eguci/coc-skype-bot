"""旧 Skype (classic) 連携部分のテストです。合成した DB と HTTP モックだけを使います。"""

import json
import sqlite3
from unittest import mock

import pytest

from coc_skype_bot.skype import Message, SkypeDatabase, SkypeWebSender

URL = "https://example.invalid/v1/users/ME/conversations/19:room/messages"


def create_main_db(directory, rows):
    """Skype classic の main.db を模した最小限の Messages テーブルを作成します。"""
    connection = sqlite3.connect(directory / "main.db")
    with connection:
        connection.execute(
            "CREATE TABLE Messages "
            "(id INTEGER PRIMARY KEY, convo_id INTEGER, author TEXT, timestamp INTEGER, "
            "body_xml TEXT)"
        )
        connection.executemany("INSERT INTO Messages VALUES (?, ?, ?, ?, ?)", rows)
    connection.close()


@pytest.fixture
def db_dir(tmp_path):
    create_main_db(
        tmp_path,
        [
            (1, 10, "alice", 50, "xxx 1d100"),  # 起動前の発言
            (2, 10, "alice", 150, "xxx 1d100"),
            (3, 20, "bob", 160, "xxx charamake"),
            (4, 10, "carol", 170, "hello"),
            (5, 10, "dave", 180, "xxx1d6"),
        ],
    )
    return tmp_path


def test_fetch_new_messages_filters_by_time_and_key(db_dir):
    database = SkypeDatabase(str(db_dir), key="xxx", room_id="", since=100)

    assert database.fetch_new_messages(set()) == [
        Message(2, "alice", "xxx 1d100"),
        Message(3, "bob", "xxx charamake"),
    ]


def test_fetch_new_messages_excludes_done_ids_and_filters_room(db_dir):
    database = SkypeDatabase(str(db_dir), key="xxx", room_id="10", since=100)

    assert database.fetch_new_messages({2}) == []
    assert database.fetch_new_messages(set()) == [Message(2, "alice", "xxx 1d100")]


def test_fetch_new_messages_treats_like_wildcards_in_key_literally(tmp_path):
    create_main_db(tmp_path, [(1, 10, "alice", 150, "a_b 1d6"), (2, 10, "bob", 150, "axb 1d6")])
    database = SkypeDatabase(str(tmp_path), key="a_b", room_id="", since=100)

    assert database.fetch_new_messages(set()) == [Message(1, "alice", "a_b 1d6")]


def test_fetch_new_messages_retries_operational_error(db_dir, monkeypatch):
    database = SkypeDatabase(str(db_dir), key="xxx", room_id="", since=100, retry_wait=0)
    real_connect = sqlite3.connect
    calls = []

    def flaky_connect(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", flaky_connect)
    assert len(database.fetch_new_messages(set())) == 2
    assert len(calls) == 2


def test_fetch_new_messages_gives_up_after_retries(tmp_path):
    database = SkypeDatabase(str(tmp_path), key="xxx", room_id="", since=0, retry_wait=0)

    with pytest.raises(sqlite3.OperationalError):
        database.fetch_new_messages(set())


def test_sender_posts_valid_escaped_json():
    session = mock.Mock()
    sender = SkypeWebSender(URL, "synthetic-token", session=session)

    sender.send('alice->say "hi" <b>&</b>')

    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args == (URL,)
    payload = json.loads(kwargs["data"])
    assert payload["content"] == 'alice-&gt;say "hi" &lt;b&gt;&amp;&lt;/b&gt;'
    assert payload["messagetype"] == "RichText"
    assert payload["contenttype"] == "text"
    assert len(payload["clientmessageid"]) == 13
    assert kwargs["headers"]["RegistrationToken"] == "synthetic-token"
    assert kwargs["timeout"] > 0
    session.post.return_value.raise_for_status.assert_called_once()


@pytest.mark.parametrize("url", ["http://example.invalid/messages", "", "file:///etc/passwd"])
def test_sender_rejects_non_https_url(url):
    with pytest.raises(ValueError, match="https"):
        SkypeWebSender(url, "synthetic-token", session=mock.Mock())

"""Skype を使わずに、ローカルで bot の動作を確認するためのモードです。

- console: 標準入力の 1 行を 1 発言として扱い、返答を標準出力へ書き出します。
- demo: 合成した main.db に発言を書き込み、本番と同じ監視・取得・返答処理を通します。
"""

import sqlite3
import tempfile
import threading
import time
from collections.abc import Iterable
from os import PathLike
from pathlib import Path
from typing import TextIO

from coc_skype_bot import replies
from coc_skype_bot.bot import SkypeBot, run_watching
from coc_skype_bot.skype import Message, SkypeDatabase

# demo で使う合成イベント (発言者, 発言) です。実在の人物やチャットとは関係ありません。
DEFAULT_EVENTS: list[tuple[str, str]] = [
    ("alice", "xxx help"),
    ("alice", "xxx 1d100"),
    ("bob", "good evening, everyone"),
    ("bob", "xxx 2d4 -1d4"),
    ("carol", "xxx xxx50 1d100"),
    ("carol", "xxx charamake"),
    ("alice", "xxx siz"),
    ("bob", "xxx 1d6  3"),
    ("alice", "xxx end"),
]

# demo の発言に付けるタイムスタンプの基準値です (bot 起動時刻として扱います)。
DEMO_START_TIMESTAMP = 1_000_000


class StreamSender:
    """返答をテキストストリーム (標準出力など) へ書き出す MessageSender です。"""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def send(self, text: str) -> None:
        print(text, file=self.stream, flush=True)


def run_console(lines: Iterable[str], out: TextIO, key: str, author: str = "you") -> int:
    """lines の各行を author の発言として扱い、bot 宛ての発言に返答します。"""
    bot = SkypeBot(StreamSender(out), key)
    bot.greet()
    for number, line in enumerate(lines, start=1):
        body = line.rstrip("\r\n")
        if replies.is_addressed(body, key) and bot.handle(Message(number, author, body)):
            break
    return 0


def parse_events(lines: Iterable[str]) -> list[tuple[str, str]]:
    """「発言者: 発言」形式の行を読み込みます。空行と # から始まる行は無視します。"""
    events = []
    for number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        author, separator, body = line.partition(":")
        if not separator or not author.strip():
            raise ValueError(f"line {number}: 「発言者: 発言」の形式で記述してください。")
        events.append((author.strip(), body.strip()))
    return events


def create_synthetic_main_db(directory: str | PathLike[str]) -> None:
    """Skype classic の main.db を模した、Messages テーブルだけの空の DB を作成します。"""
    connection = sqlite3.connect(Path(directory) / "main.db")
    try:
        with connection:
            connection.execute(
                "CREATE TABLE Messages (id INTEGER PRIMARY KEY, convo_id INTEGER, "
                "author TEXT, timestamp INTEGER, body_xml TEXT)"
            )
    finally:
        connection.close()


def insert_message(
    directory: str | PathLike[str],
    message_id: int,
    author: str,
    body: str,
    timestamp: int,
    convo_id: int = 1,
) -> None:
    """合成した main.db に発言を 1 件追加します。"""
    connection = sqlite3.connect(Path(directory) / "main.db")
    try:
        with connection:
            connection.execute(
                "INSERT INTO Messages (id, convo_id, author, timestamp, body_xml) "
                "VALUES (?, ?, ?, ?, ?)",
                (message_id, convo_id, author, timestamp, body),
            )
    finally:
        connection.close()


def run_demo(
    events: Iterable[tuple[str, str]],
    out: TextIO,
    key: str = "xxx",
    delay: float = 0.3,
    reply_timeout: float = 10.0,
) -> int:
    """合成した main.db を使って、本番と同じ監視・取得・返答の流れを実行します。

    発言ごとに main.db へ書き込み、bot 宛ての発言は返答されるまで待ちます。
    返答は out へ書き出し、実際の Skype へは送信しません。
    """
    sender = StreamSender(out)
    with tempfile.TemporaryDirectory(prefix="coc-skype-bot-demo-") as tmp:
        create_synthetic_main_db(tmp)
        source = SkypeDatabase(tmp, key, room_id="", since=DEMO_START_TIMESTAMP)
        bot = SkypeBot(sender, key)
        # 発言の表示より先に起動メッセージが出るよう、監視を始める前に挨拶します。
        bot.greet()
        stop = threading.Event()
        errors: list[BaseException] = []

        def watch() -> None:
            try:
                run_watching(bot, source, tmp, poll_interval=0.5, stop=stop)
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=watch, name="demo-watcher")
        thread.start()
        try:
            for message_id, (author, body) in enumerate(events, start=1):
                if not thread.is_alive():
                    break
                time.sleep(delay)
                sender.send(f"> {author}: {body}")
                insert_message(tmp, message_id, author, body, DEMO_START_TIMESTAMP + message_id)
                if replies.is_addressed(body, key):
                    _wait_for_reply(bot, message_id, reply_timeout)
                    if bot.ended:
                        break
        finally:
            stop.set()
            thread.join(timeout=reply_timeout)
    if errors:
        raise errors[0]
    return 0


def _wait_for_reply(bot: SkypeBot, message_id: int, timeout: float) -> None:
    """bot が message_id の発言へ返答し終えるまで待ちます。"""
    deadline = time.monotonic() + timeout
    while message_id not in bot.done_ids:
        if time.monotonic() > deadline:
            raise TimeoutError("bot から返答がありませんでした。")
        time.sleep(0.02)

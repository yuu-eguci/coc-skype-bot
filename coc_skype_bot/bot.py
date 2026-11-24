"""発言の取得・返答の作成・送信をまとめる bot 本体です。"""

import contextlib
import os
import threading

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from coc_skype_bot import replies
from coc_skype_bot.skype import MessageSender, MessageSource


class SkypeBot:
    """MessageSource から発言を取得し、返答を MessageSender へ送信します。"""

    def __init__(self, source: MessageSource, sender: MessageSender, key: str) -> None:
        self.source = source
        self.sender = sender
        self.key = key
        self.done_ids: set[int] = set()
        self.greeted = False

    def greet(self) -> None:
        """起動メッセージを 1 回だけ送信します。"""
        if not self.greeted:
            self.sender.send(replies.OPEN_MESSAGE)
            self.greeted = True

    def process(self) -> bool:
        """未処理の発言に返答します。end コマンドを受け取った場合は True を返します。"""
        for message in self.source.fetch_new_messages(self.done_ids):
            self.done_ids.add(message.id)
            reply = replies.build_reply(message.body, self.key)
            self.sender.send(f"{message.author}->{reply}")
            if replies.is_end_reply(reply):
                return True
        return False


class _MainDbChanged(FileSystemEventHandler):
    """main.db の変更を検知して通知します。"""

    def __init__(self, on_change: threading.Event) -> None:
        self.on_change = on_change

    def on_modified(self, event: FileSystemEvent) -> None:
        if os.fsdecode(event.src_path).endswith("main.db"):
            self.on_change.set()


def run_watching(bot: SkypeBot, watch_dir: str, poll_interval: float = 5.0) -> None:
    """watch_dir の main.db が変更されるたびに bot.process() を実行します。

    ファイル変更の通知が届かない環境に備え、poll_interval 秒ごとにも確認します。
    end コマンドを受け取るか、処理中に例外が発生すると終了します。
    """
    changed = threading.Event()
    observer = Observer()
    observer.schedule(_MainDbChanged(changed), watch_dir, recursive=False)
    observer.start()
    try:
        bot.greet()
        while True:
            try:
                if bot.process():
                    return
            except Exception:
                # 終了する前に、エラーで停止することをチャットへ通知します。
                with contextlib.suppress(Exception):
                    bot.sender.send(replies.ERROR_MESSAGE)
                raise
            changed.wait(poll_interval)
            changed.clear()
    finally:
        observer.stop()
        observer.join()

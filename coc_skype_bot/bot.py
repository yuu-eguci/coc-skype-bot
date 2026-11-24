"""発言の取得・返答の作成・送信をまとめる bot 本体です。"""

import contextlib
import os
import threading

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from coc_skype_bot import replies
from coc_skype_bot.skype import Message, MessageSender, MessageSource


class SkypeBot:
    """発言に対する返答を MessageSender へ送信します。"""

    def __init__(self, sender: MessageSender, key: str) -> None:
        self.sender = sender
        self.key = key
        self.done_ids: set[int] = set()
        self.greeted = False
        self.ended = False

    def greet(self) -> None:
        """起動メッセージを 1 回だけ送信します。"""
        if not self.greeted:
            self.sender.send(replies.OPEN_MESSAGE)
            self.greeted = True

    def handle(self, message: Message) -> bool:
        """1 件の発言に返答します。end コマンドの場合は True を返します。

        返答を送信し終えてから、発言を処理済み (done_ids) として記録します。
        """
        reply = replies.build_reply(message.body, self.key)
        self.sender.send(f"{message.author}->{reply.text}")
        self.ended = self.ended or reply.end
        self.done_ids.add(message.id)
        return reply.end

    def process(self, source: MessageSource) -> bool:
        """source の未処理の発言に返答します。end コマンドを受け取った場合は True を返します。"""
        return any(self.handle(message) for message in source.fetch_new_messages(self.done_ids))


class _MainDbChanged(FileSystemEventHandler):
    """main.db の変更を検知して通知します。"""

    def __init__(self, on_change: threading.Event) -> None:
        self.on_change = on_change

    def on_modified(self, event: FileSystemEvent) -> None:
        if os.fsdecode(event.src_path).endswith("main.db"):
            self.on_change.set()


def run_watching(
    bot: SkypeBot,
    source: MessageSource,
    watch_dir: str,
    poll_interval: float = 5.0,
    stop: threading.Event | None = None,
) -> None:
    """watch_dir の main.db が変更されるたびに、source の発言へ返答します。

    ファイル変更の通知が届かない環境に備え、poll_interval 秒ごとにも確認します。
    end コマンドを受け取るか、stop が設定されるか、処理中に例外が発生すると終了します。
    """
    changed = threading.Event()
    observer = Observer()
    observer.schedule(_MainDbChanged(changed), watch_dir, recursive=False)
    observer.start()
    try:
        bot.greet()
        while not (stop and stop.is_set()):
            try:
                if bot.process(source):
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

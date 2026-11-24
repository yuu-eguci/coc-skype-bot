"""旧 Skype (classic デスクトップ版の main.db と Skype for Web) との送受信を行います。

Skype は 2025-05-05 に提供が終了しているため、ここでの実サービス連携は現在は動作しません。
"""

import html
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

import requests

from coc_skype_bot import dice

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Message:
    """Messages テーブルの 1 発言です。"""

    id: int
    author: str
    body: str


class MessageSource(Protocol):
    """未処理の発言を取得するものです。"""

    def fetch_new_messages(self, exclude_ids: set[int]) -> list[Message]: ...


class MessageSender(Protocol):
    """返答を送信するものです。"""

    def send(self, text: str) -> None: ...


def _escape_like(value: str) -> str:
    """LIKE のワイルドカードを文字どおりに扱うためエスケープします。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SkypeDatabase:
    """Skype classic の main.db から、bot 宛ての新しい発言を取得します。"""

    def __init__(
        self,
        db_path: str,
        key: str,
        room_id: str,
        since: int,
        retries: int = 5,
        retry_wait: float = 0.2,
    ) -> None:
        self.main_db = Path(db_path) / "main.db"
        self.key = key
        self.room_id = room_id
        self.since = since
        self.retries = retries
        self.retry_wait = retry_wait

    def fetch_new_messages(self, exclude_ids: set[int]) -> list[Message]:
        """since 以降の「{key} 」から始まる発言のうち、exclude_ids 以外を返します。

        Skype の書き込み中に sqlite3.OperationalError が発生することがあるため、
        待機を挟んで retries 回まで再試行します。
        """
        for attempt in range(1, self.retries + 1):
            try:
                return self._select(exclude_ids)
            except sqlite3.OperationalError:
                if attempt == self.retries:
                    raise
                logger.warning("sqlite3.OperationalError (retry %d/%d)", attempt, self.retries)
                time.sleep(self.retry_wait)
        return []

    def _select(self, exclude_ids: set[int]) -> list[Message]:
        ids = sorted(exclude_ids)
        sql = (
            "SELECT id, author, body_xml FROM Messages "
            "WHERE timestamp > ? AND body_xml LIKE ? ESCAPE '\\'"
        )
        params: list[object] = [self.since, _escape_like(self.key) + " %"]
        if ids:
            sql += f" AND id NOT IN ({', '.join('?' * len(ids))})"
            params.extend(ids)
        if self.room_id:
            sql += " AND convo_id = ?"
            params.append(self.room_id)
        sql += " ORDER BY id"

        # 接続はスレッドをまたいで共有できないため、毎回この場で作成します。
        connection = sqlite3.connect(f"{self.main_db.resolve().as_uri()}?mode=ro", uri=True)
        try:
            rows = connection.execute(sql, params).fetchall()
        finally:
            connection.close()
        return [Message(int(row[0]), str(row[1]), str(row[2])) for row in rows]


class SkypeWebSender:
    """Skype for Web のメッセージ送信 API へ返答を POST します。"""

    TIMEOUT_SECONDS = 10

    def __init__(self, url: str, token: str, session: requests.Session | None = None) -> None:
        if urlsplit(url).scheme != "https":
            raise ValueError("url には https の URL を指定してください。")
        self.url = url
        self.session = session or requests.Session()
        self.headers = {
            "Accept": "application/json, text/javascript",
            "BehaviorOverride": "redirectAs404",
            "ClientInfo": (
                "os=Windows; osVer=7; proc=Win32; lcid=en-us; deviceType=1; country=n/a; "
                "clientName=skype.com; clientVer=908/1.42.0.98//skype.com"
            ),
            "Content-Type": "application/json",
            "Origin": "https://web.skype.com",
            "RegistrationToken": token,
        }

    def send(self, text: str) -> None:
        payload = {
            # RichText として送信するため、HTML として解釈される文字をエスケープします。
            "content": html.escape(text, quote=False),
            "clientmessageid": str(dice.random_int(13)),
            "messagetype": "RichText",
            "contenttype": "text",
        }
        response = self.session.post(
            self.url,
            data=json.dumps(payload),
            headers=self.headers,
            timeout=self.TIMEOUT_SECONDS,
        )
        response.raise_for_status()

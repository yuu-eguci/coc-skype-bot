"""SkypeBot.conf を読み込みます。"""

from dataclasses import dataclass, field
from os import PathLike


class ConfigError(ValueError):
    """設定ファイルの内容が不正な場合に送出します。"""


@dataclass(frozen=True)
class Config:
    """bot の設定です。token はログや repr に出力しません。"""

    db_path: str
    room_id: str
    key: str
    url: str
    token: str = field(repr=False)


def load_config(path: str | PathLike[str]) -> Config:
    """「name = value」形式の設定ファイルを読み込みます。# から始まる行は無視します。"""
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as conf:
        for line in conf:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip()

    if not values.get("key"):
        raise ConfigError("key が設定されていません。")
    return Config(
        db_path=values.get("dbPath", ""),
        room_id=values.get("roomId", ""),
        key=values["key"],
        url=values.get("url", ""),
        token=values.get("token", ""),
    )

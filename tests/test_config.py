"""設定ファイル読み込みのテストです。"""

import pytest

from coc_skype_bot.config import Config, ConfigError, load_config

TEMPLATE = """\
# コメント行は無視されます。
dbPath = /tmp/skype/synthetic-user
roomId =
key = xxx
url = https://example.invalid/v1/users/ME/conversations/19:room/messages
token = synthetic-token
"""


def test_load_config_reads_all_values(tmp_path):
    path = tmp_path / "SkypeBot.conf"
    path.write_text(TEMPLATE, encoding="utf-8")

    assert load_config(path) == Config(
        db_path="/tmp/skype/synthetic-user",
        room_id="",
        key="xxx",
        url="https://example.invalid/v1/users/ME/conversations/19:room/messages",
        token="synthetic-token",
    )


def test_token_is_hidden_from_repr():
    config = Config(db_path="d", room_id="", key="xxx", url="https://x", token="secret-value")
    assert "secret-value" not in repr(config)


def test_load_config_requires_key(tmp_path):
    path = tmp_path / "SkypeBot.conf"
    path.write_text("dbPath = /tmp/x\nkey =\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="key"):
        load_config(path)


def test_template_is_loadable():
    config = load_config("SkypeBot.conf.default")
    assert config.key == "xxx"

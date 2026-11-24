"""CLI のテストです。実際の通信や監視は行いません。"""

import pytest

from coc_skype_bot import cli

CONF = """\
dbPath = {db}
roomId =
key = xxx
url = {url}
token = synthetic-token
"""


def write_conf(tmp_path, url):
    path = tmp_path / "SkypeBot.conf"
    path.write_text(CONF.format(db=tmp_path, url=url), encoding="utf-8")
    return path


def test_run_wires_database_and_sender(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_watching", lambda bot, watch_dir: calls.append((bot, watch_dir)))
    conf = write_conf(tmp_path, "https://example.invalid/messages")

    assert cli.main(["run", "--config", str(conf)]) == 0

    bot, watch_dir = calls[0]
    assert watch_dir == str(tmp_path)
    assert bot.key == "xxx"
    assert bot.sender.url == "https://example.invalid/messages"


def test_run_returns_error_when_bot_fails(tmp_path, monkeypatch):
    def fail(bot, watch_dir):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(cli, "run_watching", fail)
    conf = write_conf(tmp_path, "https://example.invalid/messages")

    assert cli.main(["run", "--config", str(conf)]) == 1


def test_run_rejects_non_https_url(tmp_path):
    conf = write_conf(tmp_path, "http://example.invalid/messages")

    with pytest.raises(ValueError, match="https"):
        cli.main(["run", "--config", str(conf)])

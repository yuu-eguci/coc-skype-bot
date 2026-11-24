"""CLI のテストです。実際の通信は行いません。"""

import io

import pytest

from coc_skype_bot import cli, local, replies

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
    monkeypatch.setattr(
        cli, "run_watching", lambda bot, source, watch_dir: calls.append((bot, source, watch_dir))
    )
    conf = write_conf(tmp_path, "https://example.invalid/messages")

    assert cli.main(["run", "--config", str(conf)]) == 0

    bot, source, watch_dir = calls[0]
    assert watch_dir == str(tmp_path)
    assert bot.key == "xxx"
    assert bot.sender.url == "https://example.invalid/messages"
    assert source.main_db == tmp_path / "main.db"


def test_run_dry_run_prints_instead_of_posting(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli, "run_watching", lambda bot, source, watch_dir: calls.append((bot, source, watch_dir))
    )
    conf = write_conf(tmp_path, "")

    assert cli.main(["run", "--config", str(conf), "--dry-run"]) == 0

    assert isinstance(calls[0][0].sender, local.StreamSender)


def test_run_returns_error_when_bot_fails(tmp_path, monkeypatch):
    def fail(bot, source, watch_dir):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(cli, "run_watching", fail)
    conf = write_conf(tmp_path, "https://example.invalid/messages")

    assert cli.main(["run", "--config", str(conf)]) == 1


def test_run_rejects_non_https_url(tmp_path):
    conf = write_conf(tmp_path, "http://example.invalid/messages")

    with pytest.raises(ValueError, match="https"):
        cli.main(["run", "--config", str(conf)])


def test_console_reads_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("xxx 3\nxxx end\n"))

    assert cli.main(["console", "--author", "you"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        replies.OPEN_MESSAGE,
        "you->3 Result: 3 ['+3']",
        "you->end " + replies.CLOSE_MESSAGE,
    ]


def test_seed_makes_rolls_reproducible(monkeypatch, capsys):
    outputs = []
    for _ in range(2):
        monkeypatch.setattr("sys.stdin", io.StringIO("xxx 3d100\n"))
        cli.main(["console", "--seed", "42"])
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]


def test_demo_reads_events_file(tmp_path, capsys):
    events = tmp_path / "events.txt"
    events.write_text("alice: xxx 3\nalice: xxx end\n", encoding="utf-8")

    assert cli.main(["demo", "--events", str(events), "--delay", "0"]) == 0

    assert capsys.readouterr().out.splitlines()[-1] == "alice->end " + replies.CLOSE_MESSAGE


def test_demo_reads_events_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("alice: xxx 3\nalice: xxx end\n"))

    assert cli.main(["demo", "--events", "-", "--delay", "0"]) == 0

    assert capsys.readouterr().out.splitlines()[-1] == "alice->end " + replies.CLOSE_MESSAGE


def test_example_events_file_is_valid():
    with open("examples/demo-events.txt", encoding="utf-8") as file:
        events = local.parse_events(file)
    assert events[-1] == ("keeper", "xxx end")

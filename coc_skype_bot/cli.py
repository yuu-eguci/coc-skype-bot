"""コマンドラインから bot を起動します。"""

import argparse
import logging
import random
import sys
import time
from collections.abc import Sequence

from coc_skype_bot import local
from coc_skype_bot.bot import SkypeBot, run_watching
from coc_skype_bot.config import load_config
from coc_skype_bot.skype import MessageSender, SkypeDatabase, SkypeWebSender


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coc-skype-bot", description="CoC TRPG dice bot")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, help="乱数のシード (結果を再現したい場合に指定します)")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser(
        "run",
        parents=[common],
        help="旧 Skype classic の main.db を監視し、Skype for Web へ返答します",
    )
    run.add_argument("--config", default="SkypeBot.conf", help="設定ファイルのパス")
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Skype for Web へ送信せず、返答を標準出力へ書き出します",
    )

    console = subcommands.add_parser(
        "console",
        parents=[common],
        help="標準入力の各行を発言として扱い、返答を標準出力へ書き出します",
    )
    console.add_argument("--key", default="xxx", help="bot を呼び出す接頭辞 (既定: xxx)")
    console.add_argument("--author", default="you", help="発言者の名前 (既定: you)")

    demo = subcommands.add_parser(
        "demo",
        parents=[common],
        help="合成した main.db に発言を書き込み、監視から返答までの流れを実行します",
    )
    demo.add_argument(
        "--events", help="「発言者: 発言」形式の合成イベントファイル (- で標準入力から読み込みます)"
    )
    demo.add_argument("--key", default="xxx", help="bot を呼び出す接頭辞 (既定: xxx)")
    demo.add_argument("--delay", type=float, default=0.3, help="発言の間隔 (秒)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.seed is not None:
        random.seed(args.seed)

    if args.command == "console":
        return local.run_console(sys.stdin, sys.stdout, key=args.key, author=args.author)
    if args.command == "demo":
        events = local.DEFAULT_EVENTS
        if args.events == "-":
            events = local.parse_events(sys.stdin)
        elif args.events:
            with open(args.events, encoding="utf-8") as file:
                events = local.parse_events(file)
        return local.run_demo(events, sys.stdout, key=args.key, delay=args.delay)
    return _run(args.config, args.dry_run)


def _run(config_path: str, dry_run: bool) -> int:
    config = load_config(config_path)
    source = SkypeDatabase(config.db_path, config.key, config.room_id, since=round(time.time()))
    sender: MessageSender = (
        local.StreamSender(sys.stdout) if dry_run else SkypeWebSender(config.url, config.token)
    )
    try:
        run_watching(SkypeBot(sender, config.key), source, config.db_path)
    except Exception:
        logging.getLogger(__name__).exception("bot の処理中にエラーが発生したため終了します。")
        return 1
    return 0

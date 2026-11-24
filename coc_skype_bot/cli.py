"""コマンドラインから bot を起動します。"""

import argparse
import logging
import time
from collections.abc import Sequence

from coc_skype_bot.bot import SkypeBot, run_watching
from coc_skype_bot.config import load_config
from coc_skype_bot.skype import SkypeDatabase, SkypeWebSender


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coc-skype-bot", description="CoC TRPG dice bot")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser(
        "run", help="旧 Skype classic の main.db を監視し、Skype for Web へ返答します"
    )
    run.add_argument("--config", default="SkypeBot.conf", help="設定ファイルのパス")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config(args.config)
    source = SkypeDatabase(config.db_path, config.key, config.room_id, since=round(time.time()))
    sender = SkypeWebSender(config.url, config.token)
    try:
        run_watching(SkypeBot(source, sender, config.key), config.db_path)
    except Exception:
        logging.getLogger(__name__).exception("bot の処理中にエラーが発生したため終了します。")
        return 1
    return 0

"""CLI entry point and top-level orchestration."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bot",
        description="QQ news bot -- OneBot v11 RSS digest bot.",
    )
    parser.add_argument(
        "--connect",
        action="store_true",
        help="Connect to OneBot WS and start the bot loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without connecting to OneBot.",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Fetch and print news to stdout (useful with --dry-run).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.connect and not args.dry_run:
        parser.print_help()
        sys.exit(1)

    if args.dry_run and args.news:
        print("[dry-run] news fetch placeholder -- not yet implemented")
        return

    if args.connect:
        print("[connect] OneBot WS client -- not yet implemented")
        sys.exit(1)

    # dry-run without --news: just confirm startup
    print("[dry-run] bot started (no action requested)")

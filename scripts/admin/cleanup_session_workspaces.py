#!/usr/bin/env python3
import argparse
import json
import sys

from app.tools.session_workspace import cleanup_stale_session_workspaces


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up stale sandbox session workspaces.")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=168,
        help="Delete session workspaces whose latest activity is older than this many hours. Default: 168 (7 days).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete matching workspaces. Without this flag, run in dry-run mode.",
    )
    args = parser.parse_args()

    result = cleanup_stale_session_workspaces(
        max_age_hours=args.max_age_hours,
        dry_run=not args.apply,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

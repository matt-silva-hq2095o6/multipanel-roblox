import argparse
import sys
from multipanel_roblox.config import load_config
from multipanel_roblox.panel import run_dashboard

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multipanel",
        description="Roblox Open Cloud multi-universe manager and monitor",
    )
    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        help="path to multipanel config file (defaults to ~/.config/multipanel/config.toml)",
    )
    parser.add_argument(
        "-e", "--env",
        dest="target_env",
        help="environment/universe preset to target",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="raw_json",
        help="dump raw responses without table formatting",
    )

    subparsers = parser.add_subparsers(dest="command", help="subcommand to run")

    # dashboard UI
    subparsers.add_parser("tui", help="launch interactive textual dashboard")

    # tail place/server logs
    tail_p = subparsers.add_parser("tail", help="tail live logs from cloud places")
    tail_p.add_argument("universe_id", nargs="?", help="target universe ID or alias")
    tail_p.add_argument("-f", "--follow", action="store_true", help="keep connection open and stream new entries")
    tail_p.add_argument("-n", "--lines", type=int, default=50, help="initial lines to fetch")

    # datastore query
    ds_p = subparsers.add_parser("ds", help="datastores operations")
    ds_p.add_argument("action", choices=["get", "list", "set", "delete"], help="operation")
    ds_p.add_argument("--store", required=True, help="datastore name")
    ds_p.add_argument("--scope", default="global", help="datastore scope (default: global)")
    ds_p.add_argument("--key", help="key name")
    ds_p.add_argument("--value", help="json payload for set operations")

    # messaging / ordered data queues
    q_p = subparsers.add_parser("msg", help="publish cloud messaging topic payload")
    q_p.add_argument("--topic", required=True, help="topic name")
    q_p.add_argument("--message", required=True, help="string message or serialized json")
    q_p.add_argument("--universe", help="target universe id (overrides active env)")

    return parser

def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # print(f"DEBUG: command={args.command} env={args.target_env}")

    try:
        cfg = load_config(args.config_path)
    except Exception as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.command is None or args.command == "tui":
        return run_dashboard(cfg, target_env=args.target_env)

    if args.command == "tail":
        from multipanel_roblox.logs import stream_logs
        u_id = args.universe_id or cfg.resolve_universe(args.target_env)
        if not u_id:
            print("Error: no universe specified and none mapped in active config", file=sys.stderr)
            return 1
        return stream_logs(cfg, u_id, follow=args.follow, limit=args.lines, raw=args.raw_json)

    if args.command == "ds":
        from multipanel_roblox.datastore import handle_ds_cli
        return handle_ds_cli(cfg, args)

    if args.command == "msg":
        from multipanel_roblox.queue import publish_message
        u_id = args.universe or cfg.resolve_universe(args.target_env)
        if not u_id:
            print("Error: publish requires target universe", file=sys.stderr)
            return 1
        return publish_message(cfg, u_id, args.topic, args.message)

    return 0

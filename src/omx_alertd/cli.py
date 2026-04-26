from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from .actions import trigger_alert
from .config import Config, load_config
from .nws import Alert, fetch_active_alerts, matching_alerts


EVENT_ALIASES = {
    "tnd": "Tornado",
    "tor": "Tornado",
    "tornado": "Tornado",
    "svr": "Severe Thunderstorm",
    "severe": "Severe Thunderstorm",
    "thunderstorm": "Severe Thunderstorm",
    "severe-thunderstorm": "Severe Thunderstorm",
}

RATING_ALIASES = {
    "eme": "Emergency",
    "emergency": "Emergency",
    "wch": "Watch",
    "watch": "Watch",
    "warn": "Warning",
    "warning": "Warning",
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    argv = expand_shorthand(argv)

    parser = argparse.ArgumentParser(prog="alertd-omx")
    parser.add_argument("--config", help="Path to config TOML")
    sub = parser.add_subparsers(dest="command")

    daemon = sub.add_parser("daemon", help="Poll NWS and trigger configured alerts")
    daemon.add_argument("--once", action="store_true", help="Check once, trigger, then exit")

    check = sub.add_parser("check", help="Print currently matching alerts")
    check.add_argument("--dry-run", action="store_true", help="Do not trigger actions")

    test = sub.add_parser("test", help="Trigger a synthetic alert")
    test.add_argument("event", help="Event alias: tnd, tornado, svr")
    test.add_argument("rating", nargs="?", default="warn", help="eme, wch, or warn")

    args = parser.parse_args(argv)
    config_path = Path(args.config).expanduser() if args.config else None
    config = load_config(config_path)

    if args.command == "daemon":
        return run_daemon(config, once=args.once)
    if args.command == "check":
        return run_check(config, dry_run=args.dry_run)
    if args.command == "test":
        alert = synthetic_alert(args.event, args.rating)
        print(f"Triggering test alert: {alert.summary}")
        trigger_alert(alert, config.actions, wait_for_audio=False)
        return 0

    parser.print_help()
    return 2


def expand_shorthand(argv: list[str]) -> list[str]:
    known_subcommands = {"daemon", "check", "test"}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in known_subcommands:
            return argv
        if token in {"--config"}:
            index += 2
            continue
        if token.startswith("--config="):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if token.lower() in EVENT_ALIASES:
            return [*argv[:index], "test", *argv[index:]]
        return argv
    return argv


def run_daemon(config: Config, once: bool = False) -> int:
    seen: set[str] = set()
    print(f"alertd-omx polling every {config.poll_seconds}s")
    while True:
        try:
            alerts = matching_alerts(fetch_active_alerts(config), config)
            for alert in alerts:
                if alert.id in seen:
                    continue
                seen.add(alert.id)
                print_alert(alert)
                trigger_alert(alert, config.actions)
        except Exception as exc:
            print(f"alertd-omx: {exc}", file=sys.stderr)

        if once:
            return 0
        time.sleep(config.poll_seconds)


def run_check(config: Config, dry_run: bool = True) -> int:
    alerts = matching_alerts(fetch_active_alerts(config), config)
    if not alerts:
        print("No matching active alerts.")
        return 0
    for alert in alerts:
        print_alert(alert)
        if not dry_run:
            trigger_alert(alert, config.actions)
    return 0


def synthetic_alert(event_alias: str, rating_alias: str) -> Alert:
    base = EVENT_ALIASES.get(event_alias.lower())
    rating = RATING_ALIASES.get(rating_alias.lower())
    if not base:
        raise SystemExit(f"Unknown event '{event_alias}'. Try: {', '.join(sorted(EVENT_ALIASES))}")
    if not rating:
        raise SystemExit(f"Unknown rating '{rating_alias}'. Try: eme, wch, warn")

    event = f"{base} {rating}"
    severity = "Extreme" if rating == "Emergency" else "Severe" if rating == "Warning" else "Moderate"
    urgency = "Immediate" if rating in {"Emergency", "Warning"} else "Expected"
    return Alert(
        id=f"test-{base.lower().replace(' ', '-')}-{rating.lower()}",
        event=event,
        headline=f"{event}: local alertd-omx test",
        description="This is a local test alert. No real NOAA/NWS alert has been issued.",
        instruction="Verify that audio, notification, and optional radar behavior work.",
        severity=severity,
        certainty="Observed" if rating == "Emergency" else "Likely",
        urgency=urgency,
        effective="now",
        expires="test",
        zones=[],
        same_codes=[],
        url="",
    )


def print_alert(alert: Alert) -> None:
    print(f"{alert.summary}")
    if alert.headline:
        print(f"  {alert.headline}")
    if alert.effective or alert.expires:
        print(f"  effective: {alert.effective} expires: {alert.expires}")
    if alert.url:
        print(f"  {alert.url}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)

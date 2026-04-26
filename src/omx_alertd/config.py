from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG_PATH = Path("~/.config/alertd-omx/config.toml").expanduser()


@dataclass(frozen=True)
class Actions:
    notify: bool = True
    audio: bool = True
    set_volume: bool = True
    volume_percent: int = 100
    open_radar: bool = False
    radar_url: str = "https://radar.weather.gov/"


@dataclass(frozen=True)
class Config:
    user_agent: str = "alertd-omx/0.1"
    poll_seconds: int = 60
    zones: list[str] = field(default_factory=list)
    same_codes: list[str] = field(default_factory=list)
    events: list[str] = field(
        default_factory=lambda: [
            "Tornado Warning",
            "Tornado Watch",
            "Severe Thunderstorm Warning",
            "Severe Thunderstorm Watch",
        ]
    )
    actions: Actions = field(default_factory=Actions)


def load_config(path: Path | None = None) -> Config:
    config_path = path or Path(os.environ.get("ALERTD_OMX_CONFIG", DEFAULT_CONFIG_PATH)).expanduser()
    if not config_path.exists():
        return Config()

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    actions_raw = raw.get("actions", {})
    actions = Actions(
        notify=bool(actions_raw.get("notify", True)),
        audio=bool(actions_raw.get("audio", True)),
        set_volume=bool(actions_raw.get("set_volume", True)),
        volume_percent=int(actions_raw.get("volume_percent", 100)),
        open_radar=bool(actions_raw.get("open_radar", False)),
        radar_url=str(actions_raw.get("radar_url", "https://radar.weather.gov/")),
    )
    return Config(
        user_agent=str(raw.get("user_agent", "alertd-omx/0.1")),
        poll_seconds=max(30, int(raw.get("poll_seconds", 60))),
        zones=[str(zone).upper() for zone in raw.get("zones", [])],
        same_codes=[str(code).zfill(6) for code in raw.get("same_codes", [])],
        events=[str(event) for event in raw.get("events", Config().events)],
        actions=actions,
    )

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Config


API_BASE = "https://api.weather.gov/alerts/active"


@dataclass(frozen=True)
class Alert:
    id: str
    event: str
    headline: str
    description: str
    instruction: str
    severity: str
    certainty: str
    urgency: str
    effective: str
    expires: str
    zones: list[str]
    same_codes: list[str]
    url: str

    @property
    def summary(self) -> str:
        bits = [self.event, self.severity, self.urgency]
        return " | ".join(bit for bit in bits if bit)


def fetch_active_alerts(config: Config, timeout: int = 15) -> list[Alert]:
    params: dict[str, str] = {}
    if config.zones:
        params["zone"] = ",".join(config.zones)
    url = API_BASE
    if params:
        url = f"{url}?{urlencode(params)}"

    req = Request(
        url,
        headers={
            "Accept": "application/geo+json, application/json",
            "User-Agent": config.user_agent,
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)

    return [_alert_from_feature(feature) for feature in payload.get("features", [])]


def matching_alerts(alerts: list[Alert], config: Config) -> list[Alert]:
    configured_events = {normalize_event(event) for event in config.events}
    configured_zones = {zone.upper() for zone in config.zones}
    configured_same = {code.zfill(6) for code in config.same_codes}
    matches: list[Alert] = []

    for alert in alerts:
        event_match = not configured_events or normalize_event(alert.event) in configured_events
        zone_match = not configured_zones or bool(configured_zones.intersection(alert.zones))
        same_match = not configured_same or bool(configured_same.intersection(alert.same_codes))
        if event_match and (zone_match or same_match):
            matches.append(alert)
    return matches


def normalize_event(event: str) -> str:
    return " ".join(event.lower().replace("-", " ").split())


def _alert_from_feature(feature: dict) -> Alert:
    props = feature.get("properties", {})
    geocode = props.get("geocode") or {}
    zones = [zone.rsplit("/", 1)[-1].upper() for zone in props.get("affectedZones", [])]
    same_codes = [str(code).zfill(6) for code in geocode.get("SAME", [])]
    return Alert(
        id=str(props.get("id") or feature.get("id") or ""),
        event=str(props.get("event") or "Weather Alert"),
        headline=str(props.get("headline") or ""),
        description=str(props.get("description") or ""),
        instruction=str(props.get("instruction") or ""),
        severity=str(props.get("severity") or ""),
        certainty=str(props.get("certainty") or ""),
        urgency=str(props.get("urgency") or ""),
        effective=_format_time(props.get("effective")),
        expires=_format_time(props.get("expires")),
        zones=zones,
        same_codes=same_codes,
        url=str(props.get("@id") or props.get("uri") or feature.get("id") or ""),
    )


def _format_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    except ValueError:
        return value

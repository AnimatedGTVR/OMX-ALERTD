from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import wave
import math
import struct
import webbrowser

from .config import Actions
from .nws import Alert


def trigger_alert(alert: Alert, actions: Actions, wait_for_audio: bool = True) -> None:
    if actions.set_volume:
        set_volume(actions.volume_percent)
    if actions.notify:
        notify(alert)
    if actions.audio:
        play_alarm(wait=wait_for_audio)
    if actions.open_radar:
        webbrowser.open(actions.radar_url)


def set_volume(percent: int) -> None:
    pct = max(0, min(percent, 150))
    commands = [
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%"],
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"],
        ["amixer", "set", "Master", f"{pct}%"],
    ]
    for command in commands:
        if shutil.which(command[0]):
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return


def notify(alert: Alert) -> None:
    if not shutil.which("notify-send"):
        return
    title = alert.event.upper()
    body = alert.headline or alert.description or alert.summary
    subprocess.run(
        [
            "notify-send",
            "--urgency=critical",
            "--app-name=alertd-omx",
            title,
            body[:900],
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def play_alarm(wait: bool = True) -> None:
    player = _first_available(["paplay", "aplay", "ffplay"])
    if not player:
        print("\a", end="", flush=True)
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        path = Path(fh.name)
    try:
        _write_alarm_wav(path)
        if player == "ffplay":
            command = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
        else:
            command = [player, str(path)]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if wait:
            process.wait()
        else:
            threading.Thread(target=_cleanup_after_exit, args=(process, path), daemon=True).start()
            path = None
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def _first_available(names: list[str]) -> str | None:
    for name in names:
        if shutil.which(name):
            return name
    return None


def _cleanup_after_exit(process: subprocess.Popen, path: Path) -> None:
    process.wait()
    path.unlink(missing_ok=True)


def _write_alarm_wav(path: Path) -> None:
    sample_rate = 44_100
    duration = 4.5
    frames = int(sample_rate * duration)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            t = index / sample_rate
            on = int(t * 4) % 2 == 0
            freq = 1050 if on else 850
            envelope = 0.9 if on else 0.35
            sample = int(32767 * envelope * math.sin(2 * math.pi * freq * t))
            wav.writeframesraw(struct.pack("<h", sample))

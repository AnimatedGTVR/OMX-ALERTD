# alertd-omx

NOAA/NWS alert daemon for Omarchy-style Linux desktops.

It polls the National Weather Service active alerts API, filters by your county/zone or SAME/FIPS code, and can trigger:

- loud audio alert
- desktop notification
- optional radar page

NWS asks clients not to request alerts more often than every 30 seconds. The default interval is 60 seconds.

## Install for local testing

No-pip Omarchy/local launcher:

```bash
mkdir -p ~/.local/share/omarchy/bin
ln -sf /home/animated/work/omx-alertd/bin/alertd-omx ~/.local/share/omarchy/bin/alertd-omx
chmod +x /home/animated/work/omx-alertd/bin/alertd-omx
```

Then open a new shell or run `hash -r`.

Python package install, if `pip` is available:

```bash
python3 -m pip install -e .
```

## Configure

Create a config file:

```bash
mkdir -p ~/.config/alertd-omx
cp alertd-omx.toml.example ~/.config/alertd-omx/config.toml
```

Edit `~/.config/alertd-omx/config.toml`.

Useful filters:

- `zones`: NWS county/forecast zone IDs, such as `ALC007` or `ALZ034`
- `same_codes`: 6-digit SAME/FIPS county codes, such as `001007`
- `events`: alert event names to trigger on

## Run

```bash
alertd-omx daemon
```

Run once and print matching alerts without triggering:

```bash
alertd-omx check --dry-run
```

## Test alerts

Shorthand:

```bash
alertd-omx tnd warn
alertd-omx svr wch
alertd-omx tnd eme
```

Explicit:

```bash
alertd-omx test tornado warning
```

Supported rating aliases:

- `eme`, `emergency`
- `wch`, `watch`
- `warn`, `warning`

Supported event aliases:

- `tnd`, `tor`, `tornado`
- `svr`, `thunderstorm`, `severe-thunderstorm`

## Systemd user service

After installing, copy and enable the example unit:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/alertd-omx.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now alertd-omx.service
```

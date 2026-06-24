# Running mod-ui with systemd

Two user-level systemd units are provided. They run under your own login
session — no root privileges are required to start or stop them.

| Unit | Role |
|---|---|
| `mod-host.service` | Starts the LV2 plugin engine (`mod-host`) |
| `mod-ui.service` | Starts the web UI server (`mod-ui`) |

`mod-ui.service` declares `Wants=mod-host.service`, so enabling mod-ui is
usually enough — systemd will attempt to pull in mod-host automatically.
If mod-host is not installed, the `Wants=` dependency is silently ignored
and mod-ui can still run in development mode (no audio).

---

## Prerequisites

### Full audio mode (recommended)

- **mod-host** installed and on `$PATH`
- **JACK** or **PipeWire-JACK** running in your user session before the
  services start

  JACK is typically managed outside systemd (e.g. via QJackCtl, Cadence,
  or a PipeWire session that provides the JACK API automatically). Start
  your JACK server before enabling the units, or ensure PipeWire-JACK is
  active in your desktop session.

### Development / no-audio mode

Only mod-ui is needed. mod-host and JACK are not required. Set
`MOD_DEV_HOST=1` in the configuration file (see [Configuration](#configuration)).

---

## Installation

The units are installed by `make install` under `$(LIBDIR)/systemd/user/`
(typically `/usr/lib/systemd/user/`). After installation, reload the
daemon so systemd picks up the new files:

```sh
systemctl --user daemon-reload
```

---

## Usage

### Enable and start at login (persistent)

```sh
# Full audio (mod-host + mod-ui)
systemctl --user enable --now mod-host.service mod-ui.service

# Web UI only (no audio, dev mode — set MOD_DEV_HOST=1 first, see below)
systemctl --user enable --now mod-ui.service
```

`enable` makes the unit start automatically every time you log in.
`--now` also starts it immediately without waiting for a reboot.

### Start/stop for the current session only

```sh
systemctl --user start mod-host.service mod-ui.service
systemctl --user stop  mod-ui.service mod-host.service
```

### Check status and logs

```sh
systemctl --user status mod-host.service mod-ui.service

# Follow live logs for both units
journalctl --user -f -u mod-host.service -u mod-ui.service

# Show all logs since last boot
journalctl --user -b -u mod-ui.service
```

### Restart after a configuration change

```sh
systemctl --user restart mod-ui.service
```

---

## Configuration

Runtime settings are read from `/etc/mod-ui/mod-ui.env` (installed as a
commented template). Uncomment and edit the lines you need, then restart
the service.

```sh
sudoedit /etc/mod-ui/mod-ui.env
systemctl --user restart mod-ui.service
```

| Variable | Default | Description |
|---|---|---|
| `MOD_DEVICE_WEBSERVER_PORT` | `8888` | TCP port the web UI listens on |
| `MOD_DATA_DIR` | `~/.local/share/mod-ui` | User data directory (pedalboards, keys…) |
| `MOD_DEV_HOST` | *(unset — real mod-host)* | Set to `1` to use a stub host (no audio) |
| `MOD_DEV_ENVIRONMENT` | `1` | Set to `0` only when MOD Duo hardware is connected |
| `MOD_LOG` | `1` | Set to `0` to silence verbose logging |
| `MOD_HTML_DIR` | `/usr/share/mod/html` | Override HTML asset location |
| `MOD_DEFAULT_PEDALBOARD` | `/usr/share/mod/default.pedalboard` | Override default pedalboard location |

### Running without audio (dev mode)

If mod-host is not installed or JACK is not available, add this line to
`/etc/mod-ui/mod-ui.env`:

```
MOD_DEV_HOST=1
```

The web UI will start with a stub backend — the pedalboard editor is fully
usable but no sound is produced and no LV2 plugins are loaded.

### Changing the web server port

```
MOD_DEVICE_WEBSERVER_PORT=9000
```

Then open `http://localhost:9000` in your browser.

---

## Startup sequence

When both units are enabled, systemd starts them in this order:

```
sound.target  ──►  mod-host.service  ──►  mod-ui.service
network.target ─────────────────────────►
```

`mod-host` binds TCP ports **5555** (command) and **5556** (feedback)
before mod-ui connects to them.

Both units are configured with `Restart=on-failure` so they are
automatically restarted if they crash.

---

## Disabling

```sh
# Stop and disable both units
systemctl --user disable --now mod-ui.service mod-host.service
```

User data in `~/.local/share/mod-ui` is not removed by disabling the units.

# ha-inteno-router

A Home Assistant **custom integration** (`custom_components/inteno_router/`)
for the user's Inteno/IOPSYS home router — stats, connected-device
presence, and reboot control via the router's `ubus` API.

## Architecture constraint: this must be a real integration, not a push script

**Data flows from the router into Home Assistant through code that Home
Assistant itself loads and runs** (a proper `custom_components/`
integration, set up via HA's config flow, polled by a
`DataUpdateCoordinator`) — never through an external script or cron job
that pushes state into HA's REST API from outside. That approach was tried
and explicitly rejected during scoping (2026-08-22): it's fragile (nothing
restarts it if it dies, no HA-native config UI, doesn't show up as a normal
integration to manage/remove), and doesn't match how every other
integration on this HA instance already works. If a task here starts
looking like "write a script that calls Home Assistant's REST API," stop —
that's the wrong shape for this repo.

## Where this deploys

Home Assistant instance: Raspberry Pi 5, `root@192.168.3.71` via SSH
(default key `~/.ssh/id_ed25519` — see the `home-assistant` skill for how
this was discovered/confirmed). Config root is `/config`; this
integration's code goes to `/config/custom_components/inteno_router/`.

**HACS is already installed** on this instance (`/config/custom_components/hacs`).
Once the integration is in a working state, it should be installable as a
HACS custom repository rather than only manual SSH/`rsync` deployment — add
a `hacs.json` and keep `custom_components/inteno_router/` as the
HACS-recognized structure from the start rather than restructuring later.

## Cross-project knowledge — read these skills first

Two Claude Code skills hold knowledge this repo depends on and shouldn't
duplicate — read them before assuming router capabilities, HA instance
details, or credentials from scratch:

- **`inteno-router`** skill: the router's identity (Inteno/IOPSYS/JUCI),
  its `ubus`-over-websocket API (`ws://192.168.1.1/ubus`, subprotocol
  `ubus-json`), the full confirmed ACL (which `ubus` objects/methods exist
  and what they return), and router admin credentials location
  (`~/.config/inteno-router/env`).
- **`home-assistant`** skill: this HA instance's location/auth, SSH
  deployment access, and general HA conventions.

If either skill is missing information this repo needs, update the skill
directly (it outlives this repo and any other HA/router project), not just
a comment here.

## Project tracking

This repo implements atask 185 (parent: pull stats / connected devices /
reboot, in that milestone order) and atask 186 (connected-device detail,
child of 185). Check `atask show 185` / `atask show 186` for current state
and update them as milestones land — don't let this file and atask drift
out of sync about what's actually done.

## Integration structure

Standard HA custom integration layout:

```
custom_components/inteno_router/
  __init__.py       # entry setup/unload, creates the coordinator
  manifest.json      # domain, requirements (websockets), config_flow: true
  const.py           # DOMAIN and shared constants
  ubus_client.py      # async ubus-over-websocket client (login + call)
  coordinator.py      # DataUpdateCoordinator, polls ubus on an interval
  config_flow.py      # UI setup: host/username/password, validates login
  sensor.py           # stats + per-client entities from coordinator data
```

`ubus_client.py` should stay a thin, dependency-light wrapper around the
raw JSON-RPC protocol (see the `inteno-router` skill for the exact request/
response shapes already confirmed working) — easy to unit test without a
live router, and reusable if `device_tracker`/`button` platforms get added
later for milestones 2/3.

Session tokens from `ubus`'s `session.login` expire in ~300s — the
coordinator must re-login each poll cycle (or check `expires` and refresh),
never assume one token lasts for the integration's whole lifetime.

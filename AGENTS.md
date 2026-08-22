# ha-inteno-router

A Home Assistant **custom integration** (`custom_components/inteno_router/`)
for an Inteno/IOPSYS home router — stats, connected-device presence, and
reboot control via the router's `ubus` API.

## Architecture

Data flows from the router into Home Assistant through a
`custom_components/` integration that Home Assistant itself loads and
runs: a config flow handles setup, and a `DataUpdateCoordinator` polls the
router on an interval. This is what makes the integration restart-safe,
configurable through HA's own UI, and manageable — install, reconfigure,
remove — exactly like any other integration on the instance.

## Where this deploys

This integration's code goes to `/config/custom_components/inteno_router/`
on whatever machine runs Home Assistant. This repo doesn't need to know
(or record) that machine's address or how to reach it — see the private
`home-assistant` Claude Code skill for the actual instance details and
deployment access, since that's operational/personal information that
belongs there, not in a public repo.

**HACS is already installed** on the target instance
(`/config/custom_components/hacs`). Once the integration is in a working
state, it should be installable as a HACS custom repository — keep
`hacs.json` present and `custom_components/inteno_router/` in the
HACS-recognized structure from the start.

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

## Project milestones

In order: pull stats from the router into Home Assistant; surface each
connected device's full info — hostname, IP, MAC, link speed, wired/
wireless; trigger a reboot through Home Assistant. Progress against these
is tracked outside this repo — check with whoever's driving the work for
current state.

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

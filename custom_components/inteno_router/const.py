"""Constants for the Inteno Router integration."""

DOMAIN = "inteno_router"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_HOST = "192.168.1.1"

# ubus session tokens expire in ~300s server-side; poll well inside that
# window so every update cycle re-authenticates fresh rather than racing
# an expiry mid-poll.
UPDATE_INTERVAL_SECONDS = 60

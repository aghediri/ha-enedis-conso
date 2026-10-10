"""Constants for the Enedis Consumption integration."""
from __future__ import annotations

DOMAIN = "enedis_conso"

# MyElectricalData gateway (proxies the official Enedis Data Connect APIs and
# adds Tempo day colors + tariff prices). No Enedis app registration needed —
# the user supplies their PRM (PDL) and a MyElectricalData token.
API_BASE = "https://www.myelectricaldata.fr"

# ---- Endpoints (consumption side only — NO production) ----------------------
# Daily consumption (kWh/day).
EP_DAILY = "{base}/daily_consumption/{prm}/start/{start}/end/{end}"
# 30-min load curve (average power W per half-hour).
EP_LOAD_CURVE = "{base}/consumption_load_curve/{prm}/start/{start}/end/{end}"
# Daily max power (VA) drawn.
EP_MAX_POWER = "{base}/consumption_max_power/{prm}/start/{start}/end/{end}"
# Contract details (subscribed power kVA, tariff formula, etc.).
EP_CONTRACTS = "{base}/contracts/{prm}"
# Delivery address / usage-point identity.
EP_ADDRESSES = "{base}/addresses/{prm}"
# Tempo day colors (blue/white/red) — MyElectricalData convenience endpoint.
EP_TEMPO = "{base}/rte/tempo/{start}/{end}"

# ---- Config entry keys ------------------------------------------------------
CONF_PRM = "prm"
CONF_TOKEN = "token"
CONF_NAME = "name"
CONF_PRICE_BASE = "price_base"          # €/kWh flat (Base tariff)
CONF_PRICE_HP = "price_hp"              # €/kWh peak (HP/HC)
CONF_PRICE_HC = "price_hc"              # €/kWh off-peak (HP/HC)
CONF_PRICE_BLUE_HP = "price_blue_hp"    # Tempo blue peak
CONF_PRICE_BLUE_HC = "price_blue_hc"
CONF_PRICE_WHITE_HP = "price_white_hp"
CONF_PRICE_WHITE_HC = "price_white_hc"
CONF_PRICE_RED_HP = "price_red_hp"
CONF_PRICE_RED_HC = "price_red_hc"

DEFAULT_NAME = "Enedis Consumption"

# Default EDF regulated prices (€/kWh, incl. taxes) — editable in options.
# These are sane 2025 ballparks; the user tunes them to their contract.
DEFAULT_PRICE_BASE = 0.2516
DEFAULT_PRICE_HP = 0.27
DEFAULT_PRICE_HC = 0.2068
DEFAULT_PRICE_BLUE_HP = 0.162
DEFAULT_PRICE_BLUE_HC = 0.128
DEFAULT_PRICE_WHITE_HP = 0.188
DEFAULT_PRICE_WHITE_HC = 0.144
DEFAULT_PRICE_RED_HP = 0.756
DEFAULT_PRICE_RED_HC = 0.1568

# Poll interval — Enedis data updates once per day; 6h keeps it fresh without
# hammering the gateway (which rate-limits).
UPDATE_INTERVAL_HOURS = 6

# HP/HC default split (local time). Enedis HC hours vary per contract; this is
# the common 22:00–06:00 window. Overridable later via options.
DEFAULT_HC_START = 22
DEFAULT_HC_END = 6

ATTRIBUTION = "Data: Enedis via MyElectricalData (myelectricaldata.fr)"

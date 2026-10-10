# Enedis Consumption (Home Assistant)

A HACS custom integration that pulls the **full consumption-side** data for a
French **Linky** meter into Home Assistant, via the **MyElectricalData** gateway
— no Enedis app registration, no production data, just everything about what you
*consume*.

> Consumption-only by design. If you have solar and want production too, this
> isn't the one — this focuses on getting the most out of consumption data.

## What you get

| Sensor | What it is |
|---|---|
| `sensor.*_daily_consumption` | Yesterday's energy (kWh) |
| `sensor.*_month_consumption` | This month's total (kWh) |
| `sensor.*_hp_consumption` / `_hc_consumption` | Peak / off-peak split (kWh) |
| `sensor.*_last_power` | Latest 30-min load-curve power (W) |
| `sensor.*_daily_max_power` | Daily peak power drawn (VA) |
| `sensor.*_daily_cost` / `_month_cost` | € cost (tariff- and Tempo-aware) |
| `sensor.*_subscribed_power` | Contract subscribed power (kVA) |
| `sensor.*_tariff` | Detected tariff formula |
| `sensor.*_tempo_today` / `_tomorrow` | Tempo day color (blue/white/red) |
| `sensor.*_address` | Delivery address |

Plus **long-term statistics backfill** (up to ~3 years of daily history) so the
**Energy dashboard** and `statistics-graph` cards are populated the moment you
install it.

## Why MyElectricalData?

The official Enedis Data Connect API gives raw consumption, load curve, max
power, contract and address — but **not** Tempo day colors or tariff prices.
MyElectricalData proxies the Enedis APIs **and** adds Tempo + prices, with a
simple token (no OAuth app registration). This integration targets that gateway.

## Install

### 1. Get a MyElectricalData token
- Go to [myelectricaldata.fr](https://www.myelectricaldata.fr), link your Enedis
  account, consent to data sharing for your PDL, and copy:
  - your **PRM / PDL** (14 digits)
  - your **token**
- ⚠️ The **load curve** (30-min power) requires "collecte horaire" (hourly
  collection) enabled for your PDL on the Enedis side — daily consumption works
  immediately, the curve may take ~a day to start after you enable it.

### 2. Install via HACS
- HACS → Integrations → ⋮ → Custom repositories → add
  `https://github.com/aghediri/ha-enedis-conso` (category: Integration) →
  install → restart HA.

### 3. Add the integration
- Settings → Devices & Services → **+ Add Integration** → **Enedis Consumption**
- Enter your **PRM** + **token**, and your **€/kWh prices** (defaults provided;
  tune later in the integration's Options).

### 4. Energy dashboard
- Settings → Dashboards → Energy → **Electricity grid** → add consumption →
  pick `sensor.*_daily_consumption`. History backfills automatically; re-run via
  the `enedis_conso.backfill_statistics` service if needed.

## Tariffs & cost

The integration computes **€ cost** from your configured prices:
- **Base** — flat `price_base`.
- **HP/HC** — `price_hp` / `price_hc`, split by the load curve (default off-peak
  22:00–06:00).
- **Tempo** — `price_{blue,white,red}_{hp,hc}`, applied by the day's Tempo color
  (pulled automatically). Red-day awareness lets you build "shift load off red
  days" automations.

All prices are editable in **Options** after setup.

## Services

- `enedis_conso.backfill_statistics` — import N days (max ~1095) of daily
  consumption history into statistics.

## Notes

- Enedis data updates roughly **once per day**; the integration polls every 6h.
- Everything is **consumption-side only** — no production endpoints are called.

## License

MIT — see [LICENSE](LICENSE).

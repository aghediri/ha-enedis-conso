"""Config + options flow for Enedis Consumption."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_NAME,
    CONF_PRICE_BASE,
    CONF_PRICE_BLUE_HC,
    CONF_PRICE_BLUE_HP,
    CONF_PRICE_HC,
    CONF_PRICE_HP,
    CONF_PRICE_RED_HC,
    CONF_PRICE_RED_HP,
    CONF_PRICE_WHITE_HC,
    CONF_PRICE_WHITE_HP,
    CONF_PRM,
    CONF_TOKEN,
    DEFAULT_NAME,
    DEFAULT_PRICE_BASE,
    DEFAULT_PRICE_BLUE_HC,
    DEFAULT_PRICE_BLUE_HP,
    DEFAULT_PRICE_HC,
    DEFAULT_PRICE_HP,
    DEFAULT_PRICE_RED_HC,
    DEFAULT_PRICE_RED_HP,
    DEFAULT_PRICE_WHITE_HC,
    DEFAULT_PRICE_WHITE_HP,
    DOMAIN,
)


def _price_schema(defaults: dict) -> dict:
    """Build the price fields (shared by config + options)."""
    g = defaults.get
    return {
        vol.Optional(CONF_PRICE_BASE, default=g(CONF_PRICE_BASE, DEFAULT_PRICE_BASE)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_HP, default=g(CONF_PRICE_HP, DEFAULT_PRICE_HP)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_HC, default=g(CONF_PRICE_HC, DEFAULT_PRICE_HC)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_BLUE_HP, default=g(CONF_PRICE_BLUE_HP, DEFAULT_PRICE_BLUE_HP)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_BLUE_HC, default=g(CONF_PRICE_BLUE_HC, DEFAULT_PRICE_BLUE_HC)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_WHITE_HP, default=g(CONF_PRICE_WHITE_HP, DEFAULT_PRICE_WHITE_HP)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_WHITE_HC, default=g(CONF_PRICE_WHITE_HC, DEFAULT_PRICE_WHITE_HC)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_RED_HP, default=g(CONF_PRICE_RED_HP, DEFAULT_PRICE_RED_HP)): vol.Coerce(float),
        vol.Optional(CONF_PRICE_RED_HC, default=g(CONF_PRICE_RED_HC, DEFAULT_PRICE_RED_HC)): vol.Coerce(float),
    }


class EnedisConsoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial UI setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            prm = str(user_input[CONF_PRM]).strip()
            await self.async_set_unique_id(prm)
            self._abort_if_unique_id_configured()
            if not prm.isdigit() or len(prm) != 14:
                errors["prm"] = "invalid_prm"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_PRM): str,
                vol.Required(CONF_TOKEN): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                **_price_schema({}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return EnedisConsoOptionsFlow(entry)


class EnedisConsoOptionsFlow(OptionsFlow):
    """Let the user tune prices after setup."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        merged = {**self._entry.data, **self._entry.options}
        schema = vol.Schema(_price_schema(merged))
        return self.async_show_form(step_id="init", data_schema=schema)

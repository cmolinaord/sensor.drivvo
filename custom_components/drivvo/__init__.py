import hashlib
import logging

import requests

from homeassistant import config_entries, core
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    BASE_URL,
    CONF_EMAIL,
    CONF_ID_VEHICLE,
    CONF_PASSWORD,
    CONF_VEHICLES,
    DOMAIN,
    LOGIN_BASE_URL,
)

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
):
    if await auth(
        hass=hass,
        user=entry.data.get(CONF_EMAIL),
        password=entry.data.get(CONF_PASSWORD),
    ):
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = entry.data

        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )
    else:
        raise ConfigEntryAuthFailed("Invalid authentication")
    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        vehicle = []
        vehicle.append(config_entry.data.get(CONF_ID_VEHICLE))
        data_new = {
            CONF_EMAIL: config_entry.data.get(CONF_EMAIL),
            CONF_PASSWORD: config_entry.data.get(CONF_PASSWORD),
            CONF_VEHICLES: vehicle,
        }

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=data_new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def auth(
    hass,
    user,
    password,
    token: bool | None = False,
) -> bool:
    password = hashlib.md5(password.encode("utf-8")).hexdigest()

    def login():
        return requests.post(
            LOGIN_BASE_URL,
            data={
                "email": user,
                "senha": password,
            },
        )

    response = await hass.async_add_executor_job(login)

    if response.ok:
        if token:
            return response.json().get("token")
        return True

    return False


async def get_vehicles(
    hass,
    token: bool | None = False,
) -> bool:
    def get():
        return requests.get(
            "https://api.drivvo.com/veiculo/web",
            headers={"x-token": token},
        )

    response = await hass.async_add_executor_job(get)
    _LOGGER.debug("API Response Vehicles: %s", response.json())

    if response.ok:
        return response.json()
    return None


async def get_data_vehicle(hass, user, password, id_vehicle, info):
    """Get The request from the api."""

    def get():
        return requests.get(url, headers={"x-token": token})

    token = await auth(
        hass=hass,
        user=user,
        password=password,
        token=True,
    )
    if token:
        if info == "abastecimento":
            url = BASE_URL.format(f"veiculo/{id_vehicle}/abastecimento/web")
        elif info == "base":
            url = BASE_URL.format(f"veiculo/{id_vehicle}")
        else:
            return None

        response = await hass.async_add_executor_job(get)

        def sort_by_key(list):
            return list["data"]

        if response.ok:
            data = response.json()
            if info == "abastecimento":
                data = sorted(data, key=sort_by_key, reverse=True)

            _LOGGER.debug("API Response Data Vehicle - %s: %s", info, data)
            return data

    _LOGGER.debug("API Response Data Vehicle - %s: %s", info, response)
    return None

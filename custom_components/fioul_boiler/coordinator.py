from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from .const import (
    CONF_POWER_SENSOR,
    CONF_LPH_RUN,
    CONF_DEBOUNCE,
    CONF_KWH_PER_LITER,
    DEFAULT_LPH_RUN,
    DEFAULT_DEBOUNCE,
    DEFAULT_KWH_PER_LITER,
    DEFAULT_THRESHOLDS,
    STATE_ARRET,
    STATE_NUIT,
    STATE_POMPE,
    STATE_PRECH,
    STATE_POST,
    STATE_BURN,
    STATE_HORS,
)

_LOGGER = logging.getLogger(__name__)


class FioulBoilerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Coordinator converting power readings into boiler state and deltas.

    Er liefert nur noch Momentanwerte und Delta-Mengen, die von den
    Sensor-Entitäten in Home Assistant persistiert und integriert werden.

    Fehlerlogik:

    1. PHC-Fehler:
       - Gefilterter Zustand war mindestens 20 Sekunden im Pré-chauffage-Zustand
         (STATE_PRECH).
       - Danach startet eine Prüfphase von 2 Minuten.
       - Wenn nach Ablauf dieser 2 Minuten der gefilterte Zustand nicht im
         Brennerzustand (STATE_BURN) ist **und** dieser Zustandswechsel zum
         Brenner nicht mindestens 20 Sekunden stabil anhält, wird ein PHC-Fehler gesetzt.

    2. Abwesenheits-Fehler (>1h kein Brennerlauf):
       - Wenn der Brennerzustand länger als 1 Stunde nicht aktiv war,
         wird error_absence = True gesetzt.
       - Ausgenommen: Arrêt (STATE_ARRET) und Mode nuit (STATE_NUIT).
    """

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        self.power_entity_id: str = entry.data[CONF_POWER_SENSOR]

        opts = entry.options or {}
        self.lph_run = opts.get(CONF_LPH_RUN, entry.data.get(CONF_LPH_RUN, DEFAULT_LPH_RUN))
        self.debounce = opts.get(CONF_DEBOUNCE, entry.data.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE))
        self.kwh_per_liter = opts.get(CONF_KWH_PER_LITER, DEFAULT_KWH_PER_LITER)

        thresholds_opt = opts.get("thresholds") or {}
        self.thresholds: dict[str, float] = {**DEFAULT_THRESHOLDS, **thresholds_opt}

        # Time/state tracking
        self._last_update: Optional[datetime] = None
        self._last_raw_state: str = STATE_ARRET
        self._last_raw_state_change: Optional[datetime] = None

        # Debounced state tracking
        self._last_state_filtered: str = STATE_ARRET
        self._last_state_filtered_change: Optional[datetime] = None

        # PHC error tracking
        self._phc_pending = False
        self._phc_check_base_time: Optional[datetime] = None
        self._phc_error = False

        # Last valid burn (for >1h absence detection)
        self._burn_last_ok: Optional[datetime] = None

        super().__init__(
            hass,
            _LOGGER,
            name="Fioul Boiler Coordinator",
            update_interval=timedelta(seconds=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        now = datetime.utcnow()

        # Read power
        state_obj = self.hass.states.get(self.power_entity_id)
        if state_obj is None or state_obj.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            power = 0.0
        else:
            try:
                power = float(state_obj.state)
            except Exception as err:
                raise UpdateFailed(f"Invalid power value: {state_obj.state}") from err

        t = self.thresholds

        # Determine raw state
        if power < t["arret"]:
            state_raw = STATE_ARRET
        elif power < t["nuit"]:
            state_raw = STATE_NUIT
        elif power < t["pompe"]:
            state_raw = STATE_POMPE
        elif power < t["prechauffage"]:
            state_raw = STATE_PRECH
        elif power < t["postcirc"]:
            state_raw = STATE_POST
        elif power <= t["burn_max"]:
            state_raw = STATE_BURN
        else:
            state_raw = STATE_HORS

        # Raw state change tracking
        if self._last_raw_state_change is None or state_raw != self._last_raw_state:
            self._last_raw_state = state_raw
            self._last_raw_state_change = now

        prev_data = self.data or {}
        prev_filtered = prev_data.get("state_filtered", state_raw)

        # Debounce
        if self._last_raw_state_change is None:
            state_filtered = state_raw
        else:
            elapsed_raw = (now - self._last_raw_state_change).total_seconds()
            if elapsed_raw >= self.debounce:
                state_filtered = self._last_raw_state
            else:
                state_filtered = prev_filtered

        # Track filtered duration (for error logic)
        if self._last_state_filtered_change is None:
            self._last_state_filtered = state_filtered
            self._last_state_filtered_change = now
        elif state_filtered != self._last_state_filtered:
            prev_state = self._last_state_filtered
            prev_duration = (now - self._last_state_filtered_change).total_seconds()

            # PCR detection: Pre-chauffage expired cleanly
            if prev_state == STATE_PRECH and prev_duration >= 20.0:
                self._phc_pending = True
                self._phc_check_base_time = now
                self._phc_error = False

            self._last_state_filtered = state_filtered
            self._last_state_filtered_change = now

        # PCR evaluation after 2 minutes
        if self._phc_pending and self._phc_check_base_time is not None:
            check_time = self._phc_check_base_time + timedelta(minutes=2)
            if now >= check_time:
                if state_filtered == STATE_BURN and self._last_state_filtered_change:
                    burn_duration = (now - self._last_state_filtered_change).total_seconds()
                    if burn_duration >= 20.0:
                        self._phc_error = False
                        self._burn_last_ok = now
                    else:
                        self._phc_error = True
                else:
                    self._phc_error = True

                self._phc_pending = False
                self._phc_check_base_time = None

        # Burner running?
        burner_running = state_filtered == STATE_BURN

        # Flow L/h
        flow_lph = self.lph_run if burner_running else 0.0
        flow_filtered = flow_lph if flow_lph >= 0.5 else 0.0

        # Time delta
        if self._last_update is None:
            dt_hours = 0.0
        else:
            dt_hours = (now - self._last_update).total_seconds() / 3600.0
        self._last_update = now

        # Deltas for persistent sensors
        delta_liters = flow_filtered * dt_hours
        delta_energy_kwh = delta_liters * self.kwh_per_liter

        # Absence error logic (>1h no burn)
        if state_filtered in (STATE_ARRET, STATE_NUIT):
            error_absence = False
        else:
            if self._burn_last_ok is None:
                error_absence = True
            else:
                error_absence = (now - self._burn_last_ok) > timedelta(hours=1)

        error_phc = self._phc_error
        error_global = error_phc or error_absence

        return {
            "power": power,
            "state_raw": state_raw,
            "state_filtered": state_filtered,
            "burner_running": burner_running,
            "flow_lph": flow_lph,
            "flow_filtered": flow_filtered,
            "delta_liters": delta_liters,
            "delta_energy_kwh": delta_energy_kwh,
            "error_phc": error_phc,
            "error_absence": error_absence,
            "error_global": error_global,
        }

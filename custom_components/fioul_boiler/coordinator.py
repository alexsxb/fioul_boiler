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
    """Coordinator converting power readings into boiler state, liters and energy.

    Fehlerlogik nach zwei klaren Bedingungen:

    1. PHC-Fehler:

       - Gefilterter Zustand war mindestens 20 Sekunden im Pré-chauffage-Zustand
         (STATE_PRECH).
       - Danach startet eine Prüfphase von 2 Minuten.
       - Wenn nach Ablauf dieser 2 Minuten der gefilterte Zustand nicht im
         Brennerzustand (STATE_BURN) ist **und** dieser Zustandswechsel zum
         Brenner nicht mindestens 20 Sekunden stabil anhält, wird
         ``error_phc = True`` gesetzt.

       Mit anderen Worten: Nach einem ausreichend langen Pré-chauffage erwarten
       wir innerhalb von 2 Minuten einen stabilen Brennerlauf von mindestens
       20 Sekunden.

    2. Abwesenheits-Fehler (>1h kein Brennerlauf):

       - Wenn der Brennerzustand (STATE_BURN) länger als 1 Stunde nicht aktiv
         war, wird ``error_absence = True`` gesetzt.
       - Ausgenommen sind Zustände, in denen die Heizung bewusst nicht laufen
         soll: Arrêt (STATE_ARRET) und Mode nuit / vacances (STATE_NUIT).

    Der globale Fehlerstatus ``error_global`` ist das logische ODER beider
    Fehlerbedingungen.
    """

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        self.power_entity_id: str = entry.data[CONF_POWER_SENSOR]

        opts = entry.options or {}
        self.lph_run: float = opts.get(CONF_LPH_RUN, entry.data.get(CONF_LPH_RUN, DEFAULT_LPH_RUN))
        self.debounce: int = opts.get(CONF_DEBOUNCE, entry.data.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE))
        self.kwh_per_liter: float = opts.get(CONF_KWH_PER_LITER, DEFAULT_KWH_PER_LITER)

        thresholds_opt = opts.get("thresholds") or {}
        self.thresholds: dict[str, float] = {**DEFAULT_THRESHOLDS, **thresholds_opt}

        # Zeit-/Zustands-Tracking (Rohzustand)
        self._last_update: Optional[datetime] = None
        self._last_raw_state: str = STATE_ARRET
        self._last_raw_state_change: Optional[datetime] = None

        # Gefilterter Zustand (Debounce) für die Fehlerlogik
        self._last_state_filtered: str = STATE_ARRET
        self._last_state_filtered_change: Optional[datetime] = None

        # PHC-Fehlerlogik
        self._phc_pending: bool = False
        self._phc_check_base_time: Optional[datetime] = None
        self._phc_error: bool = False

        # Letzter sicherer Brennerlauf für 1h-Abwesenheitsprüfung
        self._burn_last_ok: Optional[datetime] = None

        # Tages/Monats/Jahres-Grenzen für Zählersummen
        self._last_day: Optional[int] = None
        self._last_month: Optional[int] = None
        self._last_year: Optional[int] = None

        super().__init__(
            hass,
            _LOGGER,
            name="Fioul Boiler Coordinator",
            update_interval=timedelta(seconds=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        now = datetime.utcnow()

        # Leistungswert aus dem konfigurierten Sensor lesen
        state_obj = self.hass.states.get(self.power_entity_id)
        if state_obj is None or state_obj.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            power = 0.0
        else:
            try:
                power = float(state_obj.state)
            except (ValueError, TypeError) as err:
                raise UpdateFailed(f"Invalid power value: {state_obj.state}") from err

        t = self.thresholds

        # Rohzustand aus Leistung ableiten
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

        # Änderung des Rohzustands tracken
        if self._last_raw_state_change is None or state_raw != self._last_raw_state:
            self._last_raw_state = state_raw
            self._last_raw_state_change = now

        prev_data = self.data or {}  # type: ignore[assignment]
        prev_filtered = prev_data.get("state_filtered", state_raw)

        # Debounce → gefilterter Zustand
        if self._last_raw_state_change is None:
            state_filtered = state_raw
        else:
            elapsed_raw = (now - self._last_raw_state_change).total_seconds()
            if elapsed_raw >= self.debounce:
                state_filtered = self._last_raw_state
            else:
                state_filtered = prev_filtered

        # Gefilterten Zustandsverlauf für die Fehlerlogik nachhalten
        if self._last_state_filtered_change is None:
            # Initialisierung beim ersten Durchlauf
            self._last_state_filtered = state_filtered
            self._last_state_filtered_change = now
        elif state_filtered != self._last_state_filtered:
            # Zustandswechsel → Dauer des vorherigen gefilterten Zustands bestimmen
            prev_state = self._last_state_filtered
            prev_duration = (now - self._last_state_filtered_change).total_seconds()

            # Ende eines relevanten Pré-chauffage-Zyklus
            if prev_state == STATE_PRECH and prev_duration >= 20.0:
                # PHC war lang genug → wir starten eine 2-Minuten-Prüfphase
                self._phc_pending = True
                self._phc_check_base_time = now
                self._phc_error = False

            # Zustandswechsel protokollieren
            self._last_state_filtered = state_filtered
            self._last_state_filtered_change = now

        # PHC-Prüfung: nach 2 Minuten muss ein stabiler Brennerlauf vorliegen
        if self._phc_pending and self._phc_check_base_time is not None:
            check_time = self._phc_check_base_time + timedelta(minutes=2)
            if now >= check_time:
                # Wir prüfen, ob der Brennerzustand aktiv und stabil genug ist
                if state_filtered == STATE_BURN and self._last_state_filtered_change is not None:
                    burn_duration = (now - self._last_state_filtered_change).total_seconds()
                    if burn_duration >= 20.0:
                        # Brenner läuft stabil → PHC erfolgreich
                        self._phc_error = False
                        self._phc_pending = False
                        self._phc_check_base_time = None
                        # Diesen Zeitpunkt als letzten sicheren Brennerlauf merken
                        self._burn_last_ok = now
                    else:
                        # Brenner läuft, aber noch nicht lange genug → PHC-Fehler
                        self._phc_error = True
                        self._phc_pending = False
                        self._phc_check_base_time = None
                else:
                    # Kein Brennerzustand nach 2 Minuten → PHC-Fehler
                    self._phc_error = True
                    self._phc_pending = False
                    self._phc_check_base_time = None

        # Brennerlaufstatus aus gefiltertem Zustand ableiten
        burner_running = state_filtered == STATE_BURN

        # Unabhängig von der PHC-Logik: jeden stabilen Brennerlauf ≥20s als "OK" zählen
        if burner_running and self._last_state_filtered_change is not None:
            burn_duration_now = (now - self._last_state_filtered_change).total_seconds()
            if burn_duration_now >= 20.0:
                self._burn_last_ok = now

        # Durchsatz
        flow_lph = self.lph_run if burner_running else 0.0
        flow_filtered = flow_lph if flow_lph >= 0.5 else 0.0

        # Zeitdifferenz für Integration
        if self._last_update is None:
            dt_hours = 0.0
        else:
            dt_hours = (now - self._last_update).total_seconds() / 3600.0
        self._last_update = now

        # Litersummen
        prev_liters_total = prev_data.get("liters_total", 0.0)
        prev_liters_daily = prev_data.get("liters_daily", 0.0)
        prev_liters_monthly = prev_data.get("liters_monthly", 0.0)
        prev_liters_yearly = prev_data.get("liters_yearly", 0.0)

        if self._last_day is None:
            self._last_day = now.day
            self._last_month = now.month
            self._last_year = now.year

        liters_increment = flow_filtered * dt_hours  # L/h * h = L

        liters_total = prev_liters_total + liters_increment

        if now.day != self._last_day:
            liters_daily = liters_increment
            self._last_day = now.day
        else:
            liters_daily = prev_liters_daily + liters_increment

        if now.month != self._last_month:
            liters_monthly = liters_increment
            self._last_month = now.month
        else:
            liters_monthly = prev_liters_monthly + liters_increment

        if now.year != self._last_year:
            liters_yearly = liters_increment
            self._last_year = now.year
        else:
            liters_yearly = prev_liters_yearly + liters_increment

        # Energie aus Liter * Brennwert
        energy_total_kwh = liters_total * self.kwh_per_liter
        energy_daily_kwh = liters_daily * self.kwh_per_liter
        energy_monthly_kwh = liters_monthly * self.kwh_per_liter
        energy_yearly_kwh = liters_yearly * self.kwh_per_liter

        # "Thermische" Momentanleistung in kW (L/h * kWh/L = kW)
        thermal_kw = flow_filtered * self.kwh_per_liter

        # Fehlerflags gemäß neuer Logik
        error_phc = self._phc_error

        # Abwesenheits-Fehler: >1h kein Brennerlauf, außer bei Arrêt/Nuit
        if state_filtered in (STATE_ARRET, STATE_NUIT):
            error_absence = False
        else:
            if self._burn_last_ok is None:
                error_absence = True
            else:
                error_absence = (now - self._burn_last_ok) > timedelta(hours=1)

        # Globaler Fehlerstatus
        error_global = error_phc or error_absence

        return {
            "power": power,
            "state_raw": state_raw,
            "state_filtered": state_filtered,
            "burner_running": burner_running,
            "error_global": error_global,
            "error_phc": error_phc,
            "error_absence": error_absence,
            "flow_lph": flow_lph,
            "flow_filtered": flow_filtered,
            "liters_total": liters_total,
            "liters_daily": liters_daily,
            "liters_monthly": liters_monthly,
            "liters_yearly": liters_yearly,
            "energy_total_kwh": energy_total_kwh,
            "energy_daily_kwh": energy_daily_kwh,
            "energy_monthly_kwh": energy_monthly_kwh,
            "energy_yearly_kwh": energy_yearly_kwh,
            "thermal_kw": thermal_kw,
        }

from __future__ import annotations

DOMAIN = "fioul_boiler"

CONF_POWER_SENSOR = "power_sensor"
CONF_LPH_RUN = "lph_run"
CONF_DEBOUNCE = "debounce"
CONF_KWH_PER_LITER = "kwh_per_liter"

DEFAULT_LPH_RUN = 2.1
DEFAULT_DEBOUNCE = 10
DEFAULT_KWH_PER_LITER = 10.0  # Durchschnittlicher Brennwert von Heizöl (~10 kWh/L)

# Default thresholds in Watt
# arret < nuit < pompe < prech < postcirc < burn_max
DEFAULT_THRESHOLDS: dict[str, float] = {
    "arret": 1.0,
    "nuit": 10.0,
    "pompe": 90.0,
    "prechauffage": 150.0,
    "postcirc": 200.0,
    "burn_max": 500.0,
}

STATE_ARRET = "Arrêt"
STATE_NUIT = "Mode nuit / vacances"
STATE_POMPE = "Pompe de circulation"
STATE_PRECH = "Pré-chauffage"
STATE_POST = "Post-circulation"
STATE_BURN = "Brûleur en marche"
STATE_HORS = "Hors plage"

DOMAIN = "fioul_boiler"

CONF_POWER_SENSOR = "power_sensor"
CONF_LPH_RUN = "lph_run"
CONF_DEBOUNCE = "debounce"
CONF_KWH_PER_LITER = "kwh_per_liter"

DEFAULT_LPH_RUN = 2.1
DEFAULT_DEBOUNCE = 3
DEFAULT_KWH_PER_LITER = 10.0

# Zustände
STATE_ARRET = "arret"
STATE_NUIT = "nuit"
STATE_POMPE = "pompe"
STATE_PRECH = "prechauffage"
STATE_POST = "postcirc"
STATE_BURN = "burn"
STATE_HORS = "hors"

DEFAULT_THRESHOLDS = {
    "arret": 10,
    "nuit": 40,
    "pompe": 80,
    "prechauffage": 200,
    "postcirc": 400,
    "burn_max": 2000
}

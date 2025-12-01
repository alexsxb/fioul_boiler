# 🔥 Intégration Home Assistant – Fioul Boiler Monitor  
Surveillance avancée d’une chaudière fioul via mesure de puissance électrique

Cette intégration Home Assistant permet de surveiller précisément une chaudière fioul **uniquement à partir d’un capteur de puissance** (Smart Plug, Shelly, compteur Modbus, etc.).  
Aucun capteur spécifique fioul n’est nécessaire : toute la logique repose sur l’analyse des états électriques du brûleur.

La version **3.x** introduit une architecture entièrement revue, avec :

- des **capteurs persistants** (litres/kWh journaliers, mensuels, annuels…),
- une **intégration par delta** (plus de pertes de données au redémarrage),
- un **coordinator simplifié** et stable,
- une **logique d’erreur robuste** (PHC + absence).

---

# 🧱 Fonctionnement général

L’intégration lit la puissance électrique du brûleur, applique une table de seuils, et en déduit automatiquement l’état de la chaudière :

- `Arrêt`
- `Mode nuit / vacances`
- `Pompe de circulation`
- `Pré-chauffage`
- `Post-circulation`
- `Brûleur en marche`
- `Hors seuils`

Un système de **debounce** stabilise ces états pour éviter les fluctuations rapides.

À partir de l’état filtré :

- le **débit fioul** (L/h) est déterminé,
- des **deltas** de consommation (litres, kWh) sont calculés chaque seconde,
- ces deltas sont ensuite intégrés par des **capteurs persistants**.

Home Assistant stocke ces valeurs dans sa base interne (`recorder`), ce qui assure une continuité totale entre les redémarrages.

---

# ⚙ Architecture interne

## 1) Data Coordinator  
`coordinator.py`

Le coordinator fournit uniquement **des données instantanées** :

### Valeurs directes :
- `power`  
- `state_raw`  
- `state_filtered`  
- `burner_running`  
- `flow_lph`  
- `flow_filtered`  

### Deltas (nouvelle logique) :
- `delta_liters`  
- `delta_energy_kwh`  

> Ces valeurs représentent **la consommation effective depuis la dernière mise à jour**.  
> Elles ne sont jamais accumulées dans le coordinator.

### Erreurs :
- `error_phc` : problème de préchauffage / démarrage du brûleur  
- `error_absence` : plus de brûleur depuis >1h (hors Arrêt/Nuit)  
- `error_global` : `PHC OR absence`

---

## 2) Capteurs persistants  
Les capteurs suivants **intègrent eux-mêmes leur consommation** à partir des deltas du coordinator :

### Litres :
- `sensor.fioul_boiler_liters_total`
- `sensor.fioul_boiler_liters_daily`
- `sensor.fioul_boiler_liters_monthly`
- `sensor.fioul_boiler_liters_yearly`

### Énergie (kWh) :
- `sensor.fioul_boiler_energy_total_kwh`
- `sensor.fioul_boiler_energy_daily_kwh`
- `sensor.fioul_boiler_energy_monthly_kwh`
- `sensor.fioul_boiler_energy_yearly_kwh`

Chaque capteur :

- hérite de `RestoreEntity`,
- restaure sa valeur après redémarrage,
- intègre les deltas en temps réel,
- possède sa propre logique de remise à zéro :

| Capteur | Reset |
|--------|--------|
| Journaliers | 00:00 locale |
| Mensuels | 1er du mois |
| Annuels | 1er janvier |
| Totaux | jamais |

Cette architecture garantit **zéro perte** lors d’un redémarrage de Home Assistant.

---

# 🛠 Logique de détection d’erreur

## 1️⃣ Erreur PHC (pré-chauffage → démarrage raté)
On entre en PHC si :

1. La chaudière reste **≥20 s** en préchauffage.  
2. Dès que le préchauffage se termine, une fenêtre de **2 minutes** s’ouvre.  
3. À son expiration, il doit exister :  
   - un état `Brûleur en marche`,  
   - stable pendant **≥20 s**.

Sinon → **PHC = True**

---

## 2️⃣ Erreur absence (> 1h sans brûleur)
Un défaut est déclaré si :

- aucun brûleur stable depuis **>1h**  
- sauf si l’état filtré est `Arrêt` ou `Mode nuit / vacances`

---

## 3️⃣ Erreur globale
```
error_global = error_phc OR error_absence
```

---

# 📡 Entités créées

## 🔵 Capteurs d’état (live)
- `sensor.fioul_boiler_state`  
- `sensor.fioul_boiler_power`  
- `sensor.fioul_boiler_flow_lph`  
- `sensor.fioul_boiler_flow_filtered`  
- `sensor.fioul_boiler_thermal_kw`

## 🔴 Capteurs d’erreur
- `binary_sensor.fioul_boiler_error_global`
- `binary_sensor.fioul_boiler_error_phc`
- `binary_sensor.fioul_boiler_error_absence`

## 🟧 Capteurs de consommation persistants
(Litres + Énergie, total/journalier/mensuel/annuel)

---

# 🧪 Installation via HACS

1. Ouvrir **HACS → Intégrations**  
2. Ajouter un dépôt personnalisé :  
   ```
   https://github.com/alexsxb/fioul_boiler
   ```
3. Catégorie : **Integration**  
4. Installer  
5. Redémarrer Home Assistant  
6. Ajouter l’intégration via *Paramètres → Appareils & Services*

---

# ⚙️ Configuration

Lors de l’ajout, on choisit :

- capteur de puissance obligatoire  
- options :  
  - **lph_run** : L/h lorsque le brûleur fonctionne  
  - **debounce** : stabilisation d’état (s)  
  - **kwh_per_liter** : pouvoir calorifique du fioul  
  - **thresholds** : seuils de détection des états  

Les valeurs peuvent être ajustées ultérieurement via la configuration de l’intégration.

---

# 📈 Automatisations possibles

- Notification en cas d’erreur PHC  
- Alerte absence de chauffe >1h  
- Estimation du stock de fioul grâce à litres_total  
- Suivi énergétique complet (litres → kWh → €)

---

# 🪪 Licence  
Projet sous licence **MIT**.

---

# 🤝 Contributions  
Les contributions sont les bienvenues :  
corrections, améliorations, nouvelles traductions, optimisation de la logique.

Ouvrez une *issue* ou une *pull request* :  
👉 https://github.com/alexsxb/fioul_boiler

# 🔥 Intégration Home Assistant – Fioul Boiler Monitor

Cette intégration personnalisée pour Home Assistant permet de surveiller une chaudière fioul
en se basant exclusivement sur l’analyse de la puissance électrique consommée par le brûleur.
Elle applique une logique robuste pour détecter les états réels de la chaudière, les cycles du brûleur,
la consommation de fioul, l’énergie thermique estimée, ainsi que plusieurs types de défauts.

L’intégration fonctionne entièrement en local et ne dépend d’aucun service externe.

---

## ⚙️ Principe général

L’intégration lit en continu la puissance d’un capteur configuré (par exemple un `sensor.xxx_power` en W),
et en déduit :

- l’état opérationnel de la chaudière (arrêt, nuit, pompe, préchauffage, brûleur, etc.),
- les cycles de fonctionnement du brûleur,
- le débit fioul estimé (L/h),
- les litres consommés (total, jour, mois, année),
- l’énergie thermique produite (kWh),
- l’apparition de défauts (pré-chauffage qui ne mène pas à un cycle, absence de chauffe prolongée).

Les seuils de puissance et paramètres sont configurables dans l’intégration.

---

## 🧩 États de la chaudière

Les états internes sont dérivés de la puissance instantanée en comparant la valeur aux seuils définis
(dans la configuration / options de l’intégration) :

| État interne        | Constante interne    | Description                                   |
|---------------------|----------------------|-----------------------------------------------|
| Arrêt               | `STATE_ARRET`        | Chaudière complètement arrêtée               |
| Mode nuit/vacances  | `STATE_NUIT`         | Mode réduit, pas de chauffe attendue         |
| Pompe               | `STATE_POMPE`        | Pompe de circulation seule                   |
| Pré-chauffage       | `STATE_PRECH`        | Résistance de préchauffage active            |
| Post-circulation    | `STATE_POST`         | Refroidissement / circulation après chauffe  |
| Brûleur en marche   | `STATE_BURN`         | Combustion active                            |
| Hors seuils         | `STATE_HORS`         | Valeur incohérente / hors plage définie      |

Un mécanisme de **dé-bounce** est appliqué pour éviter que des oscillations rapides de la puissance ne provoquent
des changements d’état instables. L’état « filtré » est utilisé pour tous les calculs de cycle et de défaut.

---

## 🔍 Logique de détection des défauts

Deux familles de défauts sont gérées par le coordinateur (`FioulBoilerCoordinator`).

### 1️⃣ Défaut de préchauffage (PHC)

On considère qu’il y a défaut de préchauffage si :

1. L’état filtré reste au moins **20 secondes** dans `Pré-chauffage` (`STATE_PRECH`),
2. Puis une fenêtre de **2 minutes** est ouverte,
3. À l’issue de ces 2 minutes, les deux conditions suivantes ne sont pas réunies :
   - la chaudière est en état `Brûleur en marche` (`STATE_BURN`),
   - et ce brûleur est resté **au moins 20 secondes** en fonctionnement continu.

Si ces conditions ne sont pas respectées, alors :

- `error_phc = True`

Cela signale typiquement un problème de démarrage du brûleur (manque de fioul, défaut d’allumage, sécurité, etc.).

### 2️⃣ Défaut d’absence de chauffe (> 1 heure)

On considère qu’il y a absence de chauffe si :

- aucun cycle de brûleur stable n’a été détecté depuis plus d’**une heure**,  
- et que l’état filtré **n’est pas** :  
  - `Arrêt` (`STATE_ARRET`),  
  - ni `Mode nuit / vacances` (`STATE_NUIT`).

Dans ce cas :

- `error_absence = True`

Cela permet de détecter un arrêt anormal (sécurité, panne, plus de fioul) alors que la chaudière devrait être en service.

### 3️⃣ Défaut global

L’intégration expose également un défaut global :

```text
error_global = error_phc OR error_absence
```

Ce capteur est pratique pour les notifications et automatisations simplifiées.

---

## 📡 Entités exposées

Les noms exacts peuvent varier légèrement selon la configuration et la langue,
mais typiquement, l’intégration expose :

### 🟦 Capteurs binaires (binary_sensor)

- `binary_sensor.fioul_boiler_global_error`  
  → Défaut global combinant PHC et absence de chauffe.

- `binary_sensor.fioul_boiler_phc_error`  
  → Défaut de préchauffage (PHC).

- `binary_sensor.fioul_boiler_absence_error`  
  → Pas de cycle de brûleur valide depuis plus d’une heure (hors mode Arrêt / Nuit).

- `binary_sensor.fioul_boiler_burner_running`  
  → Indique si le brûleur est actuellement en marche (état filtré = `STATE_BURN`).

### 🟧 Capteurs numériques (sensor)

Selon `sensor.py`, on trouve généralement :

- `sensor.fioul_boiler_power`  
  → Puissance électrique instantanée (W) du capteur source.

- `sensor.fioul_boiler_state`  
  → État filtré de la chaudière (texte).

- `sensor.fioul_boiler_liters_total`  
  → Total des litres consommés depuis l’installation.

- `sensor.fioul_boiler_liters_daily`  
  → Consommation journalière (se réinitialise à minuit).

- `sensor.fioul_boiler_liters_monthly`  
  → Consommation mensuelle.

- `sensor.fioul_boiler_liters_yearly`  
  → Consommation annuelle.

- `sensor.fioul_boiler_energy_total_kwh`  
  → Énergie totale produite (kWh), calculée à partir du volume et du pouvoir calorifique.

- `sensor.fioul_boiler_energy_daily_kwh`  
  → Énergie journalière (kWh).

- `sensor.fioul_boiler_energy_monthly_kwh`  
  → Énergie mensuelle (kWh).

- `sensor.fioul_boiler_energy_yearly_kwh`  
  → Énergie annuelle (kWh).

- `sensor.fioul_boiler_thermal_kw`  
  → Puissance thermique instantanée estimée (kW).

---

## 📥 Installation via HACS

### 1. Ajouter le dépôt personnalisé

1. Ouvrir **HACS → Intégrations**  
2. Cliquer sur les trois points en haut à droite → **Dépôts personnalisés**  
3. Ajouter l’URL du dépôt GitHub :

```text
https://github.com/alexsxb/fioul_boiler
```

4. Catégorie : **Integration**  
5. Valider

### 2. Installer l’intégration

- Revenir à l’onglet **Intégrations** dans HACS  
- Chercher **Fioul Boiler Monitor**  
- Installer l’intégration  
- Redémarrer Home Assistant

### 3. Configurer l’intégration

1. Aller dans **Paramètres → Appareils & Services → Ajouter une intégration**  
2. Rechercher **Fioul Boiler Monitor**  
3. Sélectionner le capteur de puissance (W) existant, par exemple :
   `sensor.chaudiere_fioul_puissance`  
4. Ajuster si besoin :
   - le débit fioul en L/h (`lph_run`),
   - les seuils de puissance pour chaque état,
   - la valeur énergétique du fioul (`kwh_per_liter`).

---

## 🔧 Paramètres principaux

Les options internes incluent notamment :

- `CONF_POWER_SENSOR` : entité source de puissance (W)  
- `CONF_LPH_RUN` : débit fioul (L/h) lorsque le brûleur est en marche  
- `CONF_DEBOUNCE` : durée de stabilisation (s) pour considérer un état comme valide  
- `CONF_KWH_PER_LITER` : pouvoir calorifique du fioul en kWh/L  
- `DEFAULT_THRESHOLDS` : dictionnaire des seuils de puissance par état

Ces valeurs sont généralement configurables via le **config flow** et/ou le panneau des options de l’intégration.

---

## 🧪 Idées d’automatisations

Exemples d’utilisation :

- Envoyer une notification mobile en cas de :  
  `binary_sensor.fioul_boiler_global_error == on`  
- Créer une carte Lovelace affichant :  
  - État actuel de la chaudière  
  - Consommation du jour / mois / année  
  - Dernier défaut détecté  
- Couper d’autres charges électriques si la chaudière consomme trop (mode délestage).

---

## 📄 Licence

Ce projet est distribué sous licence **MIT**.  
Voir le fichier `LICENSE` pour plus de détails.

---

## 🤝 Contributions

Les issues et pull requests sont les bienvenues sur :

- https://github.com/alexsxb/fioul_boiler

Merci d’ouvrir des tickets en français ou en anglais, selon préférence.

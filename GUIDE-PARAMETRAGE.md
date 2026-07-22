# 📍 LocaliserP — Guide de paramétrage (perso)

Doc de référence pour configurer OwnTracks sur les téléphones et fiabiliser le suivi.
**URL du serveur :** `https://web-production-753e55.up.railway.app`
**Endpoint des positions :** `https://web-production-753e55.up.railway.app/pub`

---

## 1. Rappel de l'architecture

```
[Tél. parent] --OwnTracks (HTTP)--> [Railway: Flask /pub] --SQLite--> [Ta carte protégée par mot de passe]
```

- Chaque parent = un couple `identifiant:motdepasse` défini dans la variable Railway `TRACKERS`.
- Toi = mot de passe `VIEW_PASSWORD` pour ouvrir la carte.
- Deux serrures différentes : `TRACKERS` = le téléphone qui dépose ; `VIEW_PASSWORD` = toi qui regardes.

---

## 2. Configurer OwnTracks — ANDROID

1. Installer **OwnTracks** (Play Store).
2. ☰ **Preferences → Connection** :
   - **Mode** : `HTTP` (Private HTTP)
   - **URL** : `https://web-production-753e55.up.railway.app/pub`
   - **Identification** → activer **Authentication** :
     - Username = `maman` (ou `papa`)
     - Password = le mot de passe après `maman:` (ou `papa:`) dans `TRACKERS`
3. **Preferences → (Reporting / Advanced)** :
   - **Mode de suivi (monitoring)** : **Significant** → basse consommation
   - **locatorInterval** : `600` (secondes = 10 min) → rend le bouton on-demand réactif
4. Revenir à la carte → bouton **▲ (publish)** pour envoyer une 1ʳᵉ position.
5. **Autorisation localisation** → **« Toujours autoriser »** + localisation précise.

> ⚠️ OwnTracks affiche une **notification permanente** (« service actif »). C'est **normal et voulu** — ne pas la balayer, ne pas fermer l'appli depuis les récents.

---

## 3. Réglages ANDROID anti-veille (le plus important)

Sans ça, Android tue OwnTracks au bout de quelques heures / après un reboot.

### Tous les Android
- **Paramètres → Applications → OwnTracks → Batterie** → **« Sans restriction »** (ou « Ne pas optimiser »).

### Xiaomi / Redmi / Poco (MIUI / HyperOS) — le plus agressif
1. **Démarrage automatique** : Paramètres → Applications → Gérer les applications → OwnTracks → activer **« Démarrage automatique »**.
2. **Économiseur de batterie** : même écran → **« Aucune restriction »**.
3. **Verrouiller en mémoire** : ouvrir les applis récentes → glisser vers le bas (ou maintenir) sur la vignette OwnTracks → toucher le **cadenas 🔒**.
4. **Localisation** : OwnTracks → Autorisations → Localisation → **« Toujours autoriser »** + localisation précise.
5. (si présent) **« Autoriser l'activité en arrière-plan »**.

### Samsung (Galaxy)
- Paramètres → Applications → OwnTracks → Batterie → **« Sans restriction »**.
- Paramètres → Batterie → **désactiver « Mettre en veille les applis inutilisées »** pour OwnTracks (ou l'ajouter aux apps « jamais en veille »).

### Oppo / Vivo / Honor / Huawei
- Autoriser **démarrage auto** + **exécution en arrière-plan** + batterie non optimisée (menus « Gestion du démarrage » / « Lancement d'applications »).

---

## 4. Configurer OwnTracks — iPHONE (futur, si maman en achète un)

1. Installer OwnTracks (App Store).
2. **Settings** :
   - **Mode** : `HTTP`
   - Champ **URL** (tout en bas) : `https://web-production-753e55.up.railway.app/pub`
     ⚠️ sur iOS, c'est le champ **URL** qui compte, PAS le « Host » du milieu (Host/Port/TLS = réglages MQTT ignorés en HTTP).
   - **UserID** = `maman`, **Authentification** ON, **Mot de passe** = valeur de `TRACKERS`.
3. Onglet **Carte → ▲** pour publier.
4. Localisation → **« Toujours »** + précise.

> iOS relance OwnTracks tout seul après un reboot (dès le 1ᵉʳ déverrouillage) via les événements de localisation. Pas d'« autostart » à gérer comme sur Android.

---

## 5. Le bouton « Demander une position fraîche » (on-demand)

- Sur ta carte, clique un marqueur → **« 🔄 Demander une position fraîche »**.
- Le retour est **instantané** (message de confirmation), mais la **vraie position** arrive **au prochain contact du téléphone** (≤ `locatorInterval`, ~10 min max s'ils sont immobiles ; quasi immédiat s'ils bougent).
- Fonctionne car OwnTracks accepte la commande `reportLocation` renvoyée par le serveur en réponse HTTP (Android + iOS).
- Compromis assumé : ce n'est pas « 0 partage jusqu'à ce que je demande » — le mode *Significant* logue les déplacements en basse conso ; le bouton force juste une position à jour.

---

## 6. Dépannage

| Symptôme | Cause probable | Fix |
|---|---|---|
| Rien n'apparaît sur la carte | URL sans `/pub`, ou mot de passe ≠ `TRACKERS` | Corriger le champ URL / le mot de passe, republier ▲ |
| `401` dans les logs | mot de passe OwnTracks ≠ `TRACKERS` | Aligner les deux |
| Position se fige après quelques heures | veille Android | Refaire la section 3 (autostart + batterie + cadenas) |
| Batterie affichée pas à jour | pas de nouvelle position reçue | Cliquer « Demander une position fraîche » |
| Après reboot, plus rien (Android) | démarrage auto désactivé / appli force-stop | Réactiver démarrage auto, ne pas force-stop |

### Voir les logs serveur en direct
```powershell
cd d:\MesProjetsIA\LocaliserP
railway logs
```
Chercher les lignes `"POST /pub" 200` (accepté) ou `401` (refusé).

---

## 7. Redéployer après une modif de code

```powershell
cd d:\MesProjetsIA\LocaliserP
railway up --detach
```
(On passe par la CLI car l'intégration GitHub de Railway avait un incident ; `railway up` envoie le code en direct.)

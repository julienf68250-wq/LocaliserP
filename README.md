# 📍 LocaliserP

Carte web privée pour localiser ses parents (consentants) **à la demande**, sans
toucher à leurs comptes Google. Chaque parent installe **OwnTracks** (gratuit) ;
son téléphone publie sa position sur un **broker MQTT** ; un petit serveur Flask
stocke la dernière position et sert une carte protégée par mot de passe, avec un
bouton **« position fraîche »** (réponse en ~1 s).

```
[Tél. parent · OwnTracks]  ──MQTT/TLS──▶  [HiveMQ Cloud (broker gratuit)]
        ▲  reportLocation                          │  owntracks/#
        └───────────────── ordre ◀────────  [Flask + client MQTT permanent]
                                                    │  SQLite (dernière position)
                                            [Carte Leaflet HTTPS protégée]
```

- **MQTT = voie principale** : positions en direct + on-demand instantané.
- **HTTP `/pub` = fallback** (OwnTracks en mode HTTP, ex. iPhone).
- **Aucune donnée sensible dans le dépôt** : tout passe par des variables d'environnement.

---

## Architecture

| Brique | Rôle | Où |
|---|---|---|
| **OwnTracks** | publie la position, répond aux ordres `reportLocation` | téléphones des parents |
| **HiveMQ Cloud** | broker MQTT (relais), gratuit | cloud |
| **Flask + paho-mqtt** | client MQTT permanent, stocke, sert la carte, pousse les ordres | serveur always-on |
| **Caddy** | reverse-proxy + HTTPS automatique (Let's Encrypt) | serveur |
| **systemd** | démarrage auto + relance en cas de plantage/reboot | serveur |

> Le serveur doit être **always-on** (le client MQTT reste connecté en permanence).
> Hébergé sur **Oracle Cloud Always Free** (VM gratuite à vie). Voir `GUIDE-PARAMETRAGE.md`.

---

## Variables d'environnement

Voir `.env.example`. Les essentielles :

| Variable | Rôle |
|---|---|
| `VIEW_PASSWORD` | mot de passe pour consulter la carte |
| `TRACKERS` | `maman:mdp,papa:mdp` — le **nom** sert de clé et de topic |
| `SECRET_KEY` | clé de session Flask |
| `MQTT_HOST` / `MQTT_PORT` / `MQTT_USER` / `MQTT_PASS` | broker MQTT (vide = HTTP seul) |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | alertes Telegram (optionnel) |
| `SMTP_*` / `ALERT_EMAILS` | alertes email (optionnel) |
| `BATTERY_ALERT` | seuil batterie faible en % (défaut 15) |
| `DB_PATH` | chemin du fichier SQLite (défaut `positions.db`) |

---

## Fonctionnalités

- **Carte live** (Plan / Satellite), marqueur cliquable → popup (adresse, batterie, lien Google Maps).
- **Bouton « position fraîche »** : le serveur pousse `reportLocation` via MQTT ; le téléphone répond en ~1 s.
- **Interrogation à l'ouverture** de la page (puis simple lecture du serveur, aucune data téléphone).
- **Alertes** (optionnelles) email + Telegram : batterie faible, entrée/sortie de zone (waypoints OwnTracks).

---

## Endpoints

| Route | Auth | Description |
|---|---|---|
| `GET /` | session | la carte |
| `GET /login` · `POST /login` | — | connexion (VIEW_PASSWORD) |
| `GET /api/positions` | session | dernières positions (JSON) |
| `POST /api/request/<parent>` | session | demande une position fraîche (`all` = tous) |
| `POST /api/test-alert` | session | envoie une alerte de test |
| `POST /pub` | Basic (TRACKERS) | ingestion HTTP OwnTracks (fallback) |
| `GET /health` | — | `ok` |

---

## Déploiement & maintenance

Le déploiement complet (VM Oracle, HiveMQ, OwnTracks, HTTPS) est décrit pas à pas
dans **`GUIDE-PARAMETRAGE.md`**. Rappels rapides sur le serveur :

```bash
# se connecter
ssh -i ma-cle.key ubuntu@<IP>

# mettre à jour le code
cd ~/LocaliserP && git pull && sudo systemctl restart localiserp

# logs en direct
sudo journalctl -u localiserp -f

# état / relance
sudo systemctl status localiserp
sudo systemctl restart localiserp
```

---

## Développement local

```bash
python -m venv .venv && . .venv/bin/activate     # (Windows : .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env    # puis renseigner les valeurs
python app.py           # http://localhost:5010
```

Sans `MQTT_HOST`, le serveur tourne en **HTTP seul** (les positions n'arrivent
que via `/pub`). Les alertes restent inactives tant que Telegram/SMTP ne sont pas
configurés.

---

## Sécurité

- Carte et API protégées par `VIEW_PASSWORD` (session).
- `/pub` protégé par Basic Auth (`TRACKERS`).
- HTTPS via Caddy (certificat Let's Encrypt auto-renouvelé).
- Aucun secret dans le dépôt : identifiants du broker, mots de passe et tokens
  sont fournis par variables d'environnement (fichier `.env`, jamais commité).

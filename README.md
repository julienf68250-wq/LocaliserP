# 📍 LocaliserP

Carte web live pour localiser tes parents (consentants), sans jamais toucher à leurs
identifiants Google. Chaque parent installe **OwnTracks** (gratuit) qui envoie sa position
à ton serveur Railway ; ta page affiche les positions en direct, protégée par mot de passe.

```
[Tél. Maman] --OwnTracks HTTP--> \
                                  > [Railway: Flask /pub] -- SQLite --> [Carte Leaflet protégée]
[Tél. Papa]  --OwnTracks HTTP--> /
```

---

## 1. Déployer sur Railway

1. Pousse ce dossier sur un dépôt GitHub (ou déploie directement via `railway up`).
2. Sur [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo**.
3. Railway détecte Python et le `Procfile` automatiquement.
4. Onglet **Variables** → ajoute :
   - `VIEW_PASSWORD` = ton mot de passe pour voir la carte
   - `TRACKERS` = `maman:motdepasseM,papa:motdepasseP`
   - `SECRET_KEY` = une longue chaîne aléatoire
   - *(optionnel)* `DB_PATH` = `/data/positions.db` si tu montes un volume
5. Onglet **Settings** → **Generate Domain** pour obtenir ton URL publique
   (ex. `https://localiserp-production.up.railway.app`).

> ⚠️ Sans volume Railway, le fichier SQLite est réinitialisé à chaque redéploiement.
> Ce n'est pas grave : OwnTracks renvoie une position en quelques minutes.
> Pour de la persistance, monte un volume sur `/data` et mets `DB_PATH=/data/positions.db`.

---

## 2. Configurer OwnTracks sur CHAQUE téléphone (Android)

1. Installer **OwnTracks** depuis le Play Store.
2. Ouvrir l'app → menu ☰ → **Preferences** → **Connection**.
3. **Mode** : `HTTP` (Private HTTP).
4. **Host** : `https://TON-URL-RAILWAY/pub`
5. **Identification** → activer **Authentication** :
   - Maman : Username `maman`, Password `motdepasseM`
   - Papa : Username `papa`, Password `motdepasseP`
   *(exactement les couples mis dans la variable `TRACKERS`)*
6. **Device ID / Tracker ID** : mets `M` pour maman, `P` pour papa (facultatif).
7. Revenir à la carte OwnTracks → bouton **▲ (publish)** pour envoyer une première position.
8. Autoriser la localisation **« Tout le temps »** et **désactiver l'optimisation batterie**
   pour OwnTracks (sinon Android coupe le suivi en arrière-plan).

Régler `moveModeInterval` / `locatorInterval` dans OwnTracks pour la fréquence
(ex. une position toutes les quelques minutes) selon le compromis batterie souhaité.

---

## 3. Utiliser

- Ouvre `https://TON-URL-RAILWAY/` sur ton mobile → saisis `VIEW_PASSWORD`.
- La carte affiche Maman et Papa, rafraîchie toutes les 15 s.
- Touche une carte en haut pour centrer sur la personne.
- Ajoute la page à l'écran d'accueil pour un accès type appli.

---

## Test en local (Windows)

```powershell
cd d:\MesProjetsIA\LocaliserP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # puis édite .env
# charge les variables puis lance :
python app.py
```

Simuler une position (dans un autre terminal) :

```powershell
curl -u maman:motdepasse-maman -H "Content-Type: application/json" `
  -d '{\"_type\":\"location\",\"lat\":48.8566,\"lon\":2.3522,\"acc\":15,\"batt\":88,\"tst\":1700000000}' `
  http://localhost:5010/pub
```

Puis ouvre http://localhost:5010/ .

---

## Sécurité

- La carte et l'API sont protégées par `VIEW_PASSWORD` (session).
- L'endpoint `/pub` exige les identifiants Basic Auth de `TRACKERS`.
- Utilise **HTTPS uniquement** (Railway le fournit) — jamais en clair.
- Données sensibles : ne partage l'URL et le mot de passe avec personne d'autre.

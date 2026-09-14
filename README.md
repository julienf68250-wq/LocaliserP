# 📍 LocaliserP

Petit **lanceur web privé** pour localiser ses parents (consentants) et les 3 enfants
y accèdent depuis **une seule URL**. Chaque parent partage sa position en direct via
**Google Maps – Partage de position** ; l'app présente, derrière un mot de passe, un
bouton **« Localiser »** (ouvre Google Maps sur la position live, itinéraire natif) et
un bouton **« Appeler »**.

```
[Parent · Google Maps "Partage de position"]  ──▶  Google (position en direct)
                                                         │  lien de partage
[Lanceur Flask protégé par mot de passe]  ──bouton──▶  ouvre Google Maps live
        ▲ une seule URL, pour les 3 enfants
```

## Pourquoi cette approche

Après avoir essayé un suivi maison (OwnTracks + MQTT), on a basculé sur **Google
Partage de position** car :
- **Fiable** : les services Google ne sont jamais tués par les surcouches Android agressives (Xiaomi/HyperOS).
- **Économe en data** : le partage Google est bien plus frugal qu'un traceur tiers (rentre dans un forfait 50 Mo).

**Contrepartie assumée** : Google est un système fermé — l'app **ne reçoit aucune
donnée** de position (pas de carte intégrée, pas d'historique). Elle se contente
d'**ouvrir Google Maps** sur la position partagée. C'est un **lanceur**, pas une carte.

> L'historique de trajet Git conserve l'ancienne version « carte OwnTracks » si besoin.

## Ce que fait l'app

- Page **protégée par mot de passe** (`VIEW_PASSWORD`), une URL pour les 3 enfants.
- Une carte par parent (`PARENTS`) avec :
  - **📍 Localiser** → ouvre le lien de partage Google Maps (position live + itinéraire).
  - **📞 Appeler** → `tel:` vers le parent.
- Responsive (mobile d'abord), mode sombre.
- **Aucune donnée collectée ni stockée** (pas de base, pas de MQTT).

## Variables d'environnement

Voir `.env.example`.

| Variable | Rôle |
|---|---|
| `VIEW_PASSWORD` | mot de passe d'accès au lanceur |
| `SECRET_KEY` | clé de session Flask |
| `PARENTS` | `Nom\|lien_google\|téléphone` séparés par `;` (lien et tél. optionnels) |

## Obtenir les liens Google (voir `GUIDE-PARAMETRAGE.md`)

Sur le téléphone de **chaque parent** (connecté à son Gmail) : Google Maps → photo de
profil → **Partage de position** → **Nouveau partage** → durée **« Jusqu'à ce que vous
désactiviez »** → **Copier le lien**. Ce lien permanent ouvre la position en direct
pour **quiconque le possède** → à garder **derrière le mot de passe** (d'où ce lanceur).

## Endpoints

| Route | Auth | Description |
|---|---|---|
| `GET /` | session | le lanceur (cartes parents) |
| `GET/POST /login` | — | connexion (`VIEW_PASSWORD`) |
| `GET /logout` | — | déconnexion |
| `GET /health` | — | `ok` |

## Déploiement (VM Oracle Cloud Always Free)

Hébergé sur une VM Oracle gratuite, servi par **gunicorn** (service systemd
`localiserp`) derrière **Caddy** (HTTPS auto). Rappels sur le serveur :

```bash
ssh -i ma-cle.key ubuntu@<IP>
cd ~/LocaliserP && git pull && sudo systemctl restart localiserp   # mettre à jour
sudo journalctl -u localiserp -f                                    # logs
```
Les liens Google + mots de passe sont dans `~/LocaliserP/.env` (jamais commité).

## Développement local

```bash
python -m venv .venv && . .venv/Scripts/activate   # (Linux/Mac : .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env    # renseigner VIEW_PASSWORD, SECRET_KEY, PARENTS
python app.py           # http://localhost:5010
```

## Sécurité

- Accès protégé par `VIEW_PASSWORD` (session), HTTPS via Caddy.
- Les liens de partage Google sont « publics pour qui les a » → gardés **derrière le
  mot de passe**, à ne partager qu'entre les 3 enfants.
- Aucun secret dans le dépôt (`.env` git-ignoré).

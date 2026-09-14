# 📍 LocaliserP — Guide de paramétrage (perso)

Approche actuelle : **partage de position Google Maps** + un **lanceur web** protégé
par mot de passe, pour que les **3 enfants** accèdent depuis **une seule URL**.

- **Lanceur (vous 3)** : `https://89-168-58-160.sslip.io/` → mot de passe = `VIEW_PASSWORD`
- **Serveur** : VM Oracle Cloud Always Free (IP `89.168.58.160`) — gratuit à vie

---

## 1. Principe

```
[Parent · Google Maps "Partage de position"] → Google (position en direct)
[Lanceur Flask protégé] → boutons → ouvre Google Maps sur la position live + itinéraire
```

- **Fiable** (Google jamais tué par HyperOS) et **économe en data** (rentre dans un forfait 50 Mo).
- **Contrepartie** : Google est fermé → le lanceur **n'affiche pas de carte** ni d'historique, il **ouvre Google Maps**. C'est un **lanceur**, pas une carte.

---

## 2. Activer le partage de position sur chaque téléphone parent

À faire **une fois** sur le téléphone de **chaque parent** (connecté à SON Gmail). Ça
nécessite le téléphone (impossible depuis le web seul).

1. Ouvre **Google Maps**.
2. Touche la **photo de profil** (en haut à droite).
3. **Partage de position** → **Nouveau partage**.
4. Règle la durée sur **« Jusqu'à ce que vous désactiviez cette option »** (touche la durée pour la changer).
5. Touche **« Copier dans le presse-papiers »** (le **lien**) — pas besoin de choisir un contact.
6. Envoie ce lien (ex. par SMS à toi-même).

→ Tu obtiens **2 liens permanents** (`https://maps.app.goo.gl/...`), un par parent.
Note aussi les **2 numéros de téléphone** (pour le bouton Appeler).

> ⚠️ Ces liens sont « publics pour qui les a » → on les garde **derrière le mot de passe** du lanceur, à ne partager qu'entre vous 3.

---

## 3. Réserver la data mobile à Google (Redmi / HyperOS)

Le partage en arrière-plan est géré par **UN seul composant** : **Services Google Play**.

### Indispensable
- **Services Google Play** (Google Play services) doit avoir **Données mobiles + Wi-Fi + Arrière-plan** autorisés.
  - Paramètres → **Applications** → **Gérer les applications** → ⋮ **« Afficher toutes les applications »** (c'est une appli système) → **Services Google Play** → **Restreindre l'utilisation des données** → tout cocher.

### Pas nécessaire (économie)
- **Gmail** : inutile pour la position → laisse-le sans data mobile.
- **Google Maps** : pas besoin sur le tel du parent (ce sont les enfants qui ouvrent Maps sur LEURS téléphones). Sert juste à activer le partage (§2).

### Bonus
- Couper la **data mobile** des gourmandes (Chrome, Play Store, YouTube, réseaux sociaux).

> La data doit être **activée sur la ligne** : si « 0/50 Mo + rien hors wifi », va sur
> mobile.free.fr → Espace abonné → Gérer mes options → **activer les Services de
> données**, puis redémarrer le téléphone. La Freebox (maison) n'a aucun rôle en 4G.

---

## 4. Configurer le lanceur (le serveur)

Sur la VM Oracle, éditer `~/LocaliserP/.env` avec les 2 liens + téléphones :

```
VIEW_PASSWORD=<mot de passe d'accès>
SECRET_KEY=<longue chaîne aléatoire>
PARENTS=Maman|https://maps.app.goo.gl/xxx|+336xxxxxxxx;Papa|https://maps.app.goo.gl/yyy|+336yyyyyyyy
```

Puis appliquer :
```bash
cd ~/LocaliserP && git pull && sudo systemctl restart localiserp
```

---

## 5. Utilisation (les 3 enfants)

1. Chacun met **`https://89-168-58-160.sslip.io/`** en favori (ou sur l'écran d'accueil).
2. Ouvre → **mot de passe** → 2 cartes (Maman / Papa).
3. **📍 Localiser** → ouvre Google Maps sur la position en direct.
4. Dans Maps, **« Itinéraire »** → trajet depuis SA propre position (chaque enfant).
5. **📞 Appeler** → appel direct du parent.

---

## 6. Maintenance serveur (Oracle Cloud Always Free)

- App : gunicorn via service **systemd `localiserp`** ; **Caddy** pour le HTTPS auto.
- ⚠️ Ne **jamais** cliquer « Upgrade to Pay As You Go » (reste gratuit à vie).

```bash
ssh -i <ta-cle.key> ubuntu@89.168.58.160
sudo systemctl status localiserp        # état
sudo systemctl restart localiserp       # relancer
sudo journalctl -u localiserp -f        # logs
cd ~/LocaliserP && git pull && sudo systemctl restart localiserp   # mettre à jour
```

---

## 7. Dépannage

| Symptôme | Cause | Fix |
|---|---|---|
| Bouton « Lien à configurer » | `PARENTS` vide/mal formé | remplir `.env` (§4) + restart |
| « Localiser » ouvre une carte vide / expiré | partage Google désactivé | refaire §2 (durée « jusqu'à désactivation ») |
| Position pas à jour hors wifi | data Google Play services coupée / data ligne inactive | §3 |
| Lanceur inaccessible (HTTPS) | serveur/Caddy arrêté | `sudo systemctl restart localiserp caddy` |

---

## 8. Limites (à connaître)

- **Pas de carte intégrée** ni d'**historique** : Google ne fournit aucune donnée à l'app (système fermé). Le lanceur ouvre Google Maps.
- **Aucune connexion (ni wifi ni data) = pas de position en direct** : vrai pour tout système. Avec la data activée + Google frugal, le parent est couvert partout.
- Pour retrouver un jour carte + historique, il faudrait un **traceur GPS dédié** alimentant un serveur (hors périmètre « gratuit avec l'existant »). L'ancienne version OwnTracks reste dans l'historique Git.

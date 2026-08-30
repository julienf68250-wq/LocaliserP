# 📍 LocaliserP — Guide de paramétrage (perso)

Doc de référence : configurer les téléphones, le broker, le serveur, et fiabiliser
le suivi. Tout ce qui a coûté des heures est noté ici pour ne plus jamais chercher.

- **Carte (toi)** : `https://89-168-58-160.sslip.io/` → mot de passe = `VIEW_PASSWORD`
- **Serveur** : VM Oracle Cloud Always Free (IP `89.168.58.160`) — gratuit à vie
- **Broker MQTT** : HiveMQ Cloud (gratuit) — `1f410b576ef543d8820fb7b1ce041b3e.s1.eu.hivemq.cloud:8883`

---

## 1. Architecture

```
[OwnTracks Android/iOS] ⇄ MQTT/TLS ⇄ [HiveMQ Cloud] ⇄ MQTT ⇄ [Flask sur VM Oracle] ⇄ Caddy(HTTPS) → carte
```

- **MQTT = voie principale** : positions + bouton « position fraîche » quasi instantané.
- **HTTP `/pub` = fallback** (OwnTracks en mode HTTP).
- Le serveur tourne **en permanence** (systemd) sur une **VM Oracle gratuite à vie**, derrière **Caddy** (HTTPS auto).

---

## ⭐ CHECKLIST — configurer le téléphone d'un parent (Android)

> 🚀 **RACCOURCI** : les réglages OwnTracks (2, 3, 4) sont pénibles à trouver.
> Édite `config-<parent>.otrc` (mets-y le mot de passe HiveMQ du parent), envoie-le
> sur son téléphone, **ouvre-le → OwnTracks importe tout d'un coup** (connexion MQTT +
> `cmd` + `allowRemoteLocation` + mode Significant + intervalles).

1. **Play Store → installer OwnTracks.**
2. **Connexion (MQTT)** : Host `1f410b576ef543d8820fb7b1ce041b3e.s1.eu.hivemq.cloud`, Port `8883`, **TLS ON**, Username `maman`/`papa`, Password = credential HiveMQ, DeviceID `phone`.
3. **Commandes distantes** (Advanced) : **`cmd` ON** ET **`allowRemoteLocation` ON** (sinon le bouton 🔄 ne marche pas).
4. **Suivi** : mode **Significant** (PAS Move), `locatorDisplacement` 500, `locatorInterval` 600.
5. **Autorisations** : localisation **« Toujours »** + précise.
6. **Anti-veille** (§6) : **Batterie « Aucune restriction »** (LE réglage décisif) + Démarrage auto.
7. **Data mobile** (§7) : la **data doit être activée sur la ligne Free** (sinon rien hors wifi).
8. **Publier** : onglet Carte → **▲**.
9. **(Optionnel) Zones** : onglet Zones → « Maison » (pour les alertes arrivée/départ).

> Tester **1 téléphone d'abord**, valider (dont hors wifi), puis le 2ᵉ.

---

## 2. Broker HiveMQ Cloud (déjà créé)

- **Overview → Connection Details** : URL (host) + port `8883`.
- **Access Management → Credentials** (tous en **Publish and Subscribe**) :
  `server` (le backend), `maman`, `papa` (les téléphones).

---

## 3. OwnTracks — ANDROID

### Connexion (Preferences → Connection)
Mode **MQTT** · Host (broker) · Port `8883` · **TLS ON** · WebSocket OFF ·
Username `maman`/`papa` · Password = credential HiveMQ · DeviceID `phone` · TrackerID `M`/`P`.

### Commandes distantes (Preferences → Advanced) — INDISPENSABLE pour le bouton 🔄
- **`cmd`** (Enable remote commands) : **ON**
- **`allowRemoteLocation`** : **ON**

### Basse conso / économie de data
- **Mode de suivi : Significant** (surtout PAS **Move**, qui publie en continu et vide la data).
- **locatorDisplacement `500`** (ne publie qu'après 500 m) · **locatorInterval `600`** (10 min).
- ⚠️ Pas de mode « 100 % à la demande » dans OwnTracks : les modes qui répondent
  aux demandes publient aussi sur déplacement. **Significant = le bon compromis.**
- ✅ **Le bouton 🔄 FONCTIONNE en mode Significant** — à condition que l'appli soit **vivante et connectée** au moment de la demande (voir §6 persistance).

---

## 4. OwnTracks — iPHONE (test / futur)

Mêmes réglages (Mode MQTT, Host, 8883, TLS ON, Username/Password, DeviceID).
Commandes distantes → **Settings → From Endpoint** : `cmd` ON + `allowRemoteLocation` ON.

⚠️ **Limite iOS** : appli fermée/arrière-plan, iOS coupe la connexion MQTT → le bouton
ne réveille pas l'iPhone. Ne marche qu'appli ouverte. **Sur Android, pas ce problème.**

---

## 5. Anti-veille (le nerf de la guerre)

Sans ça, Android tue OwnTracks → plus aucune position, et le bouton échoue.

### ⭐ Le réglage DÉCISIF (HyperOS / Xiaomi-Redmi)
**Paramètres → Applications → Gérer les applications → OwnTracks → Économiseur de batterie → « Aucune restriction »** (pas « Équilibré », pas « Économie »).
> Testé : avec ce réglage, OwnTracks **survit à l'écran verrouillé ET à « Tout fermer »**.
> Le **cadenas dans les récents n'est PAS nécessaire** (inutile de s'acharner à le trouver).

### Les autres
- **Démarrage automatique** : Paramètres → Applications → Autorisations → Démarrage auto → OwnTracks. *(survit au reboot)*
- **Localisation « Toujours autoriser »** + précise.
- Ne pas balayer la **notification permanente** d'OwnTracks (= le service actif).

### Limite honnête
Un téléphone **totalement immobile plusieurs heures** (la nuit sur le chargeur) finit
par se déconnecter malgré tout. **En journée, dès que le parent bouge/utilise son
téléphone, OwnTracks se reconnecte** → le bouton marche. Le creux, c'est le long repos.

**Samsung** : Batterie → « Sans restriction » + retirer des apps mises en veille.

---

## 6. Data mobile — forfait Free 2 € (piège majeur)

Le forfait Free 2 € inclut ~50 Mo. **En mode Significant, OwnTracks consomme quasi rien.**

### ⚠️ La data doit être ACTIVÉE sur la ligne
Symptôme vécu : **« 0/50 Mo utilisé » + rien ne marche hors wifi + OwnTracks Status = « unknown host »**.
→ La **data était désactivée** sur la ligne. Fix : **[mobile.free.fr](https://mobile.free.fr) → Espace abonné de la ligne → Gérer mes options → activer les Services de données** (retirer tout blocage). Puis **redémarrer le téléphone**.
> La Freebox (box maison) n'a **aucun rôle** dans la data mobile hors wifi.

### Réserver la data à OwnTracks (Redmi/HyperOS)
- **OwnTracks → Utilisation des données** : Données mobiles ✅ + Wi-Fi ✅ + Arrière-plan ✅.
- Apps gourmandes (Chrome, Play Store, réseaux sociaux) → **décoche « Données mobiles »** (garde Wi-Fi).
> Ne JAMAIS restreindre la data d'OwnTracks lui-même.

---

## 7. Alertes (email + Telegram)

Deux alertes automatiques, sur **tous les canaux configurés** :
- 🔋 **Batterie faible** (< `BATTERY_ALERT` %, défaut 15).
- 📍 **Zones** : entrée/sortie d'un waypoint (onglet **Zones** d'OwnTracks).

### Email (multi-destinataires, idéal iPhone)
Variables (exemple Gmail — mot de passe d'application sur myaccount.google.com/apppasswords) :
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=toncompte@gmail.com
SMTP_PASS=<mot de passe d'application>
SMTP_FROM=toncompte@gmail.com
ALERT_EMAILS=enfant1@x.com,enfant2@y.com
```

### Telegram (groupe = tous les enfants)
1. **@BotFather** → `/newbot` → TOKEN.
2. Créer un **groupe** + y ajouter le bot via `https://t.me/<nom_du_bot>?startgroup=true`.
3. ID du groupe : `https://api.telegram.org/bot<TOKEN>/getUpdates` → `"chat":{"id":-100…}` (bloc `my_chat_member`).
```
TELEGRAM_TOKEN=<token>
TELEGRAM_CHAT_ID=<id négatif>
```
> Test : `POST https://89-168-58-160.sslip.io/api/test-alert` (connecté à la carte).

---

## 8. Le bouton « position fraîche » (on-demand)

- Clique 🔄 sur une ligne → le serveur pousse `reportLocation` via MQTT → réponse en ~1 s.
- **Conditions** : `cmd` + `allowRemoteLocation` ON, et l'appli **vivante/connectée** (§5).
- La page interroge aussi **à l'ouverture** ; ensuite elle lit juste le serveur (0 data téléphone).

---

## 9. Le serveur — Oracle Cloud Always Free (gratuit à vie)

Le serveur est une **VM Ubuntu** sur **Oracle Cloud Always Free**. Plus de Railway payant.

- **VM** : shape `VM.Standard.E2.1.Micro` (Always-Free), IP publique `89.168.58.160`.
- **App** : gunicorn lancé par le service **systemd `localiserp`** (démarrage auto + relance).
- **HTTPS** : **Caddy** en reverse-proxy (certificat Let's Encrypt via hostname `sslip.io`, auto-renouvelé).
- **Fichier `.env`** : `~/LocaliserP/.env` (variables/secrets).

### ⚠️ Rester gratuit
Ne **JAMAIS** cliquer « Upgrade to Pay As You Go ». Ne créer que des ressources
**« Always Free eligible »**. Si dépassement → Oracle bloque au lieu de facturer.

### Se connecter en SSH
```bash
ssh -i <ta-cle.key> ubuntu@89.168.58.160
```

### Maintenance
```bash
sudo systemctl status localiserp          # état
sudo systemctl restart localiserp         # relancer
sudo journalctl -u localiserp -f          # logs en direct
cd ~/LocaliserP && git pull && sudo systemctl restart localiserp   # mettre à jour le code
sudo systemctl restart caddy              # relancer le HTTPS
```
> Repères logs : `[MQTT] connecté au broker ✓` · `[MQTT] position reçue de <parent>` · `[MQTT] ordre reportLocation envoyé…`

---

## 10. Dépannage

| Symptôme | Cause probable | Fix |
|---|---|---|
| Rien sur la carte | mauvais Host/port/TLS ou permission HiveMQ « Subscribe only » | §2 / §3 |
| Bouton 🔄 sans effet | `cmd` OFF, ou appli tuée par la veille | activer `cmd`+`allowRemoteLocation` ; §5 batterie |
| Position se fige (Android) | veille / batterie restreinte | §5 « Aucune restriction » |
| Marche en wifi, pas en 4G | **data désactivée sur la ligne Free** | §6 activer Services de données + reboot |
| OwnTracks Status « unknown host » | pas de data (DNS échoue) | §6 (data) |
| 🔄 KO appli fermée (iPhone) | limite iOS | normal ; Android OK |
| Carte inaccessible (HTTPS) | serveur/Caddy arrêté | `sudo systemctl restart localiserp caddy` |

### Diagnostic broker (depuis un PC)
Scripts perso (scratchpad) : `listen_mqtt.py` (écoute) et `diag_mqtt.py` (envoie
`reportLocation` + écoute) — pour voir si un téléphone publie/répond, indépendamment
du serveur. **Toujours vérifier que l'appli est VIVANTE avant de conclure.**

---

## 11. Fichiers de config OwnTracks

`config-maman.otrc` / `config-papa.otrc` (à la racine, **git-ignorés** car ils
contiennent les mots de passe HiveMQ). Contenu : `mode:0` (MQTT), host, port, tls,
username, password, `cmd:true`, `allowRemoteLocation:true`, `monitoring:1`
(Significant), `locatorInterval:600`, `locatorDisplacement:500`. Import : ouvrir le
fichier sur le téléphone → OwnTracks applique tout.

"""
LocaliserP — cockpit de localisation des parents.

Reçoit les positions envoyées par OwnTracks (mode HTTP) sur /pub,
les stocke en SQLite, et affiche une carte Leaflet live protégée
par mot de passe.

Deux voies d'ingestion des positions :
  - HTTP  : OwnTracks poste sur /pub (fallback, iPhone).
  - MQTT  : OwnTracks publie sur un broker (HiveMQ Cloud). Réactivité quasi
            instantanée du bouton "position fraîche" (le serveur pousse l'ordre).

Variables d'environnement attendues (voir .env.example) :
  VIEW_PASSWORD   Mot de passe pour consulter la carte.
  TRACKERS        Identifiants OwnTracks : "maman:motdepasse1,papa:motdepasse2"
  SECRET_KEY      Clé de session Flask (générée aléatoirement si absente).
  DB_PATH         Chemin du fichier SQLite (défaut : positions.db).
  MQTT_HOST       Hôte du broker MQTT (ex. xxxx.s1.eu.hivemq.cloud). Vide = MQTT off.
  MQTT_PORT       Port TLS du broker (défaut 8883).
  MQTT_USER       Utilisateur du broker.
  MQTT_PASS       Mot de passe du broker.
"""

import json
import os
import secrets
import sqlite3
import ssl
import threading
import time
from functools import wraps

try:
    import paho.mqtt.client as mqtt
except ImportError:  # le module peut être absent en dev sans MQTT
    mqtt = None

from flask import (
    Flask,
    Response,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DB_PATH = os.environ.get("DB_PATH", "positions.db")
VIEW_PASSWORD = os.environ.get("VIEW_PASSWORD", "change-moi")


def parse_trackers():
    """Transforme "maman:pass1,papa:pass2" en {"maman": "pass1", ...}."""
    raw = os.environ.get("TRACKERS", "")
    trackers = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user, _, pwd = pair.partition(":")
        trackers[user.strip()] = pwd.strip()
    return trackers


TRACKERS = parse_trackers()

# Libellés affichés sur la carte, dérivés du nom d'utilisateur du tracker.
DISPLAY_NAMES = {name: name.capitalize() for name in TRACKERS}

# Config broker MQTT (optionnel : si MQTT_HOST vide, on reste en HTTP seul).
MQTT_HOST = os.environ.get("MQTT_HOST", "").strip()
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = os.environ.get("MQTT_USER", "").strip()
MQTT_PASS = os.environ.get("MQTT_PASS", "")
_mqtt_client = None  # client MQTT global (initialisé au démarrage)


# --------------------------------------------------------------------------- #
# Base de données
# --------------------------------------------------------------------------- #
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (
            person      TEXT PRIMARY KEY,
            lat         REAL,
            lon         REAL,
            accuracy    REAL,
            battery     INTEGER,
            batt_status INTEGER,          -- 1 déchargé, 2 en charge, 3 plein
            altitude    REAL,             -- mètres
            velocity    INTEGER,          -- km/h
            conn        TEXT,             -- w=wifi, m=mobile, o=hors-ligne
            tst         INTEGER,          -- timestamp GPS (epoch s)
            received_at INTEGER,           -- réception serveur (epoch s)
            mqtt_topic  TEXT               -- topic source MQTT (pour router les ordres)
        )
        """
    )
    # Migrations de sécurité si la table existait déjà sans ces colonnes.
    for col, coltype in (
        ("batt_status", "INTEGER"),
        ("altitude", "REAL"),
        ("velocity", "INTEGER"),
        ("conn", "TEXT"),
        ("mqtt_topic", "TEXT"),
    ):
        try:
            db.execute(f"ALTER TABLE positions ADD COLUMN {col} {coltype}")
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    # File d'attente des demandes "reporte ta position" (on-demand).
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS commands (
            person           TEXT PRIMARY KEY,
            report_requested INTEGER DEFAULT 0
        )
        """
    )
    db.commit()
    db.close()


def save_location(db, person, payload, topic=None):
    """Enregistre une position OwnTracks (voie HTTP ou MQTT). True si enregistrée."""
    if payload.get("_type") != "location":
        return False
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        return False
    db.execute(
        """
        INSERT INTO positions
            (person, lat, lon, accuracy, battery, batt_status, altitude, velocity,
             conn, tst, received_at, mqtt_topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(person) DO UPDATE SET
            lat=excluded.lat, lon=excluded.lon, accuracy=excluded.accuracy,
            battery=excluded.battery, batt_status=excluded.batt_status,
            altitude=excluded.altitude, velocity=excluded.velocity, conn=excluded.conn,
            tst=excluded.tst, received_at=excluded.received_at,
            mqtt_topic=COALESCE(excluded.mqtt_topic, positions.mqtt_topic)
        """,
        (
            person,
            lat,
            lon,
            payload.get("acc"),
            payload.get("batt"),
            payload.get("bs"),
            payload.get("alt"),
            payload.get("vel"),
            payload.get("conn"),
            payload.get("tst", int(time.time())),
            int(time.time()),
            topic,
        ),
    )
    db.commit()
    return True


# --------------------------------------------------------------------------- #
# MQTT (réactivité quasi instantanée du bouton "position fraîche")
# --------------------------------------------------------------------------- #
def _mqtt_on_connect(client, userdata, flags, rc, properties=None):
    # On s'abonne à toutes les positions OwnTracks (owntracks/<user>/<device>).
    client.subscribe("owntracks/#", qos=1)


def _mqtt_on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        return
    if payload.get("_type") != "location":
        return
    # Le topic est owntracks/<user>/<device> ; <user> = nom du parent.
    parts = msg.topic.split("/")
    person = parts[1] if len(parts) >= 2 else None
    if not person or person not in TRACKERS:
        return
    # Connexion SQLite dédiée (thread réseau MQTT distinct de Flask).
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        save_location(db, person, payload, topic=msg.topic)
    finally:
        db.close()


def init_mqtt():
    """Démarre le client MQTT si un broker est configuré."""
    global _mqtt_client
    if not MQTT_HOST or mqtt is None:
        return
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)  # HiveMQ Cloud = TLS obligatoire
    client.on_connect = _mqtt_on_connect
    client.on_message = _mqtt_on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
        _mqtt_client = client
    except Exception:
        _mqtt_client = None


def publish_report(person):
    """Pousse un ordre reportLocation au téléphone via MQTT (réponse en ~1 s)."""
    if not _mqtt_client:
        return False
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        row = db.execute(
            "SELECT mqtt_topic FROM positions WHERE person=?", (person,)
        ).fetchone()
    finally:
        db.close()
    if not row or not row["mqtt_topic"]:
        return False
    cmd_topic = row["mqtt_topic"] + "/cmd"
    payload = json.dumps({"_type": "cmd", "action": "reportLocation"})
    try:
        _mqtt_client.publish(cmd_topic, payload, qos=1)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Authentification
# --------------------------------------------------------------------------- #
def check_basic_auth(auth):
    """Valide les identifiants OwnTracks. Renvoie le nom du parent ou None."""
    if not auth:
        return None
    expected = TRACKERS.get(auth.username)
    if expected and secrets.compare_digest(expected, auth.password or ""):
        return auth.username
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------------------------------- #
# Endpoint OwnTracks
# --------------------------------------------------------------------------- #
@app.route("/pub", methods=["POST"])
def pub():
    """Reçoit une position OwnTracks (mode HTTP)."""
    person = check_basic_auth(request.authorization)
    if not person:
        return Response(
            "Identifiants invalides",
            401,
            {"WWW-Authenticate": 'Basic realm="LocaliserP"'},
        )

    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}

    db = get_db()
    if not save_location(db, person, payload):
        return jsonify([])

    # On-demand (voie HTTP) : si une position fraîche a été demandée pour ce parent,
    # on renvoie la commande reportLocation ; OwnTracks republie aussitôt.
    row = db.execute(
        "SELECT report_requested FROM commands WHERE person=?", (person,)
    ).fetchone()
    if row and row["report_requested"]:
        db.execute(
            "UPDATE commands SET report_requested=0 WHERE person=?", (person,)
        )
        db.commit()
        return jsonify([{"_type": "cmd", "action": "reportLocation"}])

    # OwnTracks attend une réponse JSON (liste, éventuellement vide).
    return jsonify([])


# --------------------------------------------------------------------------- #
# Interface web
# --------------------------------------------------------------------------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), VIEW_PASSWORD):
            session["logged_in"] = True
            session.permanent = True
            return redirect(request.args.get("next") or url_for("index"))
        error = "Mot de passe incorrect."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("map.html")


@app.route("/api/positions")
@login_required
def api_positions():
    db = get_db()
    rows = db.execute("SELECT * FROM positions").fetchall()
    pending = {
        r["person"]
        for r in db.execute(
            "SELECT person FROM commands WHERE report_requested=1"
        ).fetchall()
    }
    known = set(DISPLAY_NAMES) or {r["person"] for r in rows}
    by_person = {r["person"]: r for r in rows}

    result = []
    for person in sorted(known):
        row = by_person.get(person)
        entry = {
            "person": person,
            "name": DISPLAY_NAMES.get(person, person.capitalize()),
            "pending": person in pending,
        }
        if row:
            entry.update(
                {
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "accuracy": row["accuracy"],
                    "battery": row["battery"],
                    "batt_status": row["batt_status"],
                    "altitude": row["altitude"],
                    "velocity": row["velocity"],
                    "conn": row["conn"],
                    "tst": row["tst"],
                    "received_at": row["received_at"],
                    "has_data": True,
                }
            )
        else:
            entry["has_data"] = False
        result.append(entry)

    return jsonify({"now": int(time.time()), "positions": result})


@app.route("/api/request/<person>", methods=["POST"])
@login_required
def request_location(person):
    """Met en file une demande de position fraîche (délivrée au prochain contact)."""
    targets = list(TRACKERS) if person == "all" else [person]
    if person != "all" and person not in TRACKERS:
        return jsonify({"ok": False, "error": "parent inconnu"}), 404
    db = get_db()
    delivered = {}
    for t in targets:
        # Voie MQTT : push immédiat (réponse en ~1 s si le téléphone est en ligne).
        mqtt_ok = publish_report(t)
        delivered[t] = "mqtt" if mqtt_ok else "http"
        # Fallback HTTP : on met aussi en file (délivré au prochain contact HTTP).
        db.execute(
            """
            INSERT INTO commands (person, report_requested) VALUES (?, 1)
            ON CONFLICT(person) DO UPDATE SET report_requested=1
            """,
            (t,),
        )
    db.commit()
    return jsonify({"ok": True, "requested": targets, "via": delivered})


@app.route("/health")
def health():
    return "ok"


# Initialise la base et le client MQTT au chargement (compatible gunicorn/Railway).
init_db()
init_mqtt()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5010))
    app.run(host="0.0.0.0", port=port, debug=True)

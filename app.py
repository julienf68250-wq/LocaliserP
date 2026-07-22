"""
LocaliserP — cockpit de localisation des parents.

Reçoit les positions envoyées par OwnTracks (mode HTTP) sur /pub,
les stocke en SQLite, et affiche une carte Leaflet live protégée
par mot de passe.

Variables d'environnement attendues (voir .env.example) :
  VIEW_PASSWORD   Mot de passe pour consulter la carte.
  TRACKERS        Identifiants OwnTracks : "maman:motdepasse1,papa:motdepasse2"
  SECRET_KEY      Clé de session Flask (générée aléatoirement si absente).
  DB_PATH         Chemin du fichier SQLite (défaut : positions.db).
"""

import json
import os
import secrets
import sqlite3
import time
from functools import wraps

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
            tst         INTEGER,          -- timestamp GPS (epoch s)
            received_at INTEGER            -- réception serveur (epoch s)
        )
        """
    )
    db.commit()
    db.close()


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

    # OwnTracks envoie plusieurs types de messages ; seul "location" nous intéresse.
    if payload.get("_type") != "location":
        return jsonify([])

    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        return jsonify([])

    db = get_db()
    db.execute(
        """
        INSERT INTO positions (person, lat, lon, accuracy, battery, tst, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(person) DO UPDATE SET
            lat=excluded.lat, lon=excluded.lon, accuracy=excluded.accuracy,
            battery=excluded.battery, tst=excluded.tst, received_at=excluded.received_at
        """,
        (
            person,
            lat,
            lon,
            payload.get("acc"),
            payload.get("batt"),
            payload.get("tst", int(time.time())),
            int(time.time()),
        ),
    )
    db.commit()

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
    known = set(DISPLAY_NAMES) or {r["person"] for r in rows}
    by_person = {r["person"]: r for r in rows}

    result = []
    for person in sorted(known):
        row = by_person.get(person)
        entry = {"person": person, "name": DISPLAY_NAMES.get(person, person.capitalize())}
        if row:
            entry.update(
                {
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "accuracy": row["accuracy"],
                    "battery": row["battery"],
                    "tst": row["tst"],
                    "received_at": row["received_at"],
                    "has_data": True,
                }
            )
        else:
            entry["has_data"] = False
        result.append(entry)

    return jsonify({"now": int(time.time()), "positions": result})


@app.route("/health")
def health():
    return "ok"


# Initialise la base au chargement du module (compatible gunicorn/Railway).
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5010))
    app.run(host="0.0.0.0", port=port, debug=True)

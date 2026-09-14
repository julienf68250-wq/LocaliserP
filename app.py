"""
LocaliserP — lanceur de localisation des parents (via Google Maps).

Page protégée par mot de passe qui liste les parents. Chaque parent a :
  - un bouton "Localiser" qui ouvre Google Maps sur sa position partagée en
    direct (lien de partage Google Maps « jusqu'à désactivation »), d'où
    l'itinéraire est accessible nativement en un tap ;
  - un bouton "Appeler".

Aucune position n'est collectée ni stockée ici : Google gère tout le suivi.
L'app ne fait que présenter, derrière un mot de passe, les liens de partage
pour les 3 enfants, sur une seule URL.

Variables d'environnement (voir .env.example) :
  VIEW_PASSWORD   Mot de passe pour accéder au lanceur.
  SECRET_KEY      Clé de session Flask (aléatoire si absente).
  PARENTS         Liste "Nom|lien_google|téléphone" séparés par des ';'.
                  Ex : "Maman|https://maps.app.goo.gl/xxx|+33600000000;Papa|https://maps.app.goo.gl/yyy|+33600000001"
                  Le lien et le téléphone sont optionnels (boutons masqués si absents).
"""

import os
import secrets
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

VIEW_PASSWORD = os.environ.get("VIEW_PASSWORD", "change-moi")

# Palette d'avatars (couleur attribuée à chaque parent dans l'ordre).
COLORS = ["#4c7dff", "#ff6b6b", "#2ecc71", "#f7b731", "#a55eea"]


def parse_parents():
    """Transforme la variable PARENTS en liste de dicts prêts pour le template."""
    raw = os.environ.get("PARENTS", "")
    parents = []
    for i, entry in enumerate(p for p in raw.split(";") if p.strip()):
        parts = [x.strip() for x in entry.split("|")]
        name = parts[0] if parts else ""
        if not name:
            continue
        parents.append(
            {
                "name": name,
                "link": parts[1] if len(parts) > 1 else "",
                "tel": parts[2] if len(parts) > 2 else "",
                "initial": name[0].upper(),
                "color": COLORS[i % len(COLORS)],
            }
        )
    return parents


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


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
    return render_template("launcher.html", parents=parse_parents())


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5010))
    app.run(host="0.0.0.0", port=port, debug=True)

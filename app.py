"""Flask web app. Run:  python app.py  then open http://127.0.0.1:5000"""
import os
from flask import Flask, jsonify, render_template
from medishare.service import build_dashboard

DATA_DIR = os.environ.get("DATA_DIR", "data")


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/dashboard")
    def dashboard():
        return jsonify(build_dashboard(DATA_DIR))

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

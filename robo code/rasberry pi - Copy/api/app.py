"""
api/app.py  –  Flask application factory.
Creates the app and registers all blueprints.
Adding a new group of endpoints = new file in routes/ + one line here.
"""

from flask import Flask
from flask_cors import CORS
from api.routes.control import control_bp
from api.routes.data    import data_bp
from api.routes.stream  import stream_bp


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(control_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(stream_bp)
    return app


app = create_app()

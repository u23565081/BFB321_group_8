import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

from config import CONFIGS
from .extensions import db, login_manager, migrate


def create_app(config_name=None):
    """Application factory used by development, tests and production."""
    load_dotenv()
    environment = config_name or os.getenv("FLASK_ENV", "development")
    config_class = CONFIGS.get(environment, CONFIGS["development"])
    if environment == "production":
        config_class.validate()

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."

    @login_manager.unauthorized_handler
    def unauthorised():
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorised", "message": "Please sign in to continue."}), 401
        return redirect(url_for("auth.login", next=request.full_path))

    from .blueprints.auth import auth_bp
    from .blueprints.api import api_bp
    from .blueprints.web import web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(web_bp)

    register_error_handlers(app)
    configure_logging(app)

    @app.cli.command("seed")
    def seed_command():
        from .services.seed import seed_database

        seed_database()
        print("Demo data loaded.")

    return app


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "not_found", "message": "Resource not found."}), 404
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error", exc_info=error)
        if request.path.startswith("/api/"):
            return jsonify({"error": "server_error", "message": "The request could not be completed."}), 500
        return render_template(
            "error.html", code=500, message="Something went wrong. Please try again."
        ), 500


def configure_logging(app):
    if app.testing:
        return
    log_dir = Path(app.root_path).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(getattr(logging, app.config["LOG_LEVEL"].upper(), logging.INFO))
    app.logger.addHandler(handler)

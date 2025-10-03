import logging
from flask import Flask, jsonify
from config import Config

from .models import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # initialize logging
    logging.basicConfig(level=logging.INFO)

    # Initialize DB (adds db client to app.extensions['db'])
    try:
        init_db(app)
        app.logger.info("MySQL initialized")
    except Exception as e:
        app.logger.warning(f"Failed to initialize DB: {e}")

    # register blueprints
    from .routes import bp as routes_bp

    app.register_blueprint(routes_bp)

    # Generic JSON error handler
    @app.errorhandler(Exception)
    def handle_exception(err):
        # If it's an HTTPException, use its code, otherwise 500
        code = getattr(err, "code", 500)
        message = getattr(err, "description", str(err))
        app.logger.exception(err)
        return jsonify({"success": False, "error": message}), code

    return app

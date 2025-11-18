# main.py
import os
from datetime import timedelta
from flask import Flask

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Secret key: use env var in production (set on Render)
    app.secret_key = os.environ.get("SECRET_KEY", "replace_this_with_a_random_secret")
    app.permanent_session_lifetime = timedelta(minutes=30)

    # Register blueprints (import inside function to avoid circular imports on import-time)
    try:
        from app.routes import main_blueprint
        app.register_blueprint(main_blueprint)
    except Exception as e:
        # If blueprint import fails, raise so logs show the cause
        raise

    # Optional: API blueprint if present
    try:
        from app.routes_api import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
    except ImportError:
        # It's fine if api_bp doesn't exist yet
        pass

    return app

# Application instance for gunicorn: "gunicorn main:app"
app = create_app()

if __name__ == "__main__":
    # Useful for local dev; Render/Gunicorn will use "app"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

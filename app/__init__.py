from flask import Flask

def create_app():
    app = Flask(__name__)

    from .routes import main
    from .routes_api import api_bp

    app.register_blueprint(main)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

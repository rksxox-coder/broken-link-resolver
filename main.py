from flask import Flask
from app.routes import main_blueprint

app.secret_key = "replace_with_a_random_key"
app.permanent_session_lifetime = timedelta(minutes=30)


def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_blueprint)
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

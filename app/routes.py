from flask import Blueprint, render_template, request
from .utils import process_single_url

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@main_blueprint.route("/check", methods=["POST"])
def check_url():
    url = request.form.get("url")
    result = process_single_url(url)
    return render_template("result.html", result=result)

@main_blueprint.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    results = process_bulk_file(file)
    return render_template("result.html", results=results)

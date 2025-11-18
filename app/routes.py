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

@main_blueprint.route("/api/find", methods=["GET"])
def api_find():
    url = request.args.get("url")

    if not url:
        return jsonify({
            "success": False,
            "error": "Missing ?url= parameter"
        }), 400

    result = process_single_url(url)

    return jsonify({
        "success": True,
        "data": result
    }), 200


@main_blueprint.route("/api/bulk", methods=["POST"])
def api_bulk():
    body = request.get_json(silent=True)

    if not body or "urls" not in body:
        return jsonify({
            "success": False,
            "error": "POST JSON must contain a 'urls' list"
        }), 400

    results = [process_single_url(u) for u in body["urls"]]

    return jsonify({
        "success": True,
        "count": len(results),
        "results": results
    }), 200


@main_blueprint.after_request
def add_headers(response):
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


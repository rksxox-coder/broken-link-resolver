from flask import Blueprint, render_template, request
from .utils import process_single_url
from flask import send_file, session
from datetime import timedelta
import csv
import io

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

    if not file:
        return render_template("result.html", error="No file uploaded")

    results = process_bulk_file(file)

    # store results in session
    session["bulk_results"] = results

    return render_template("result.html", results=results, download_ready=True)



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


from flask import jsonify

@api_bp.route("/find", methods=["GET"])
def api_find():
    url = request.args.get("url")
    if not url:
        return jsonify({"success": False, "error": "Missing ?url"}), 400

    result = process_single_url(url)
    return jsonify({"success": True, "data": result}), 200


@main_blueprint.route("/download", methods=["POST"])
def download_csv():
    """
    Accepts JSON data of results from frontend
    and returns a CSV file for download
    """
    import json
    data = request.form.get("results")
    if not data:
        return {"error": "No results provided"}, 400

    results = json.loads(data)

    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Input URL", "Working", "Alternative", "Error"])

    for item in results:
        writer.writerow([
            item.get("input", ""),
            "Yes" if item.get("working") else "No",
            item.get("alternative", ""),
            item.get("error", "")
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="broken_link_results.csv"
    )


@main_blueprint.route("/api/bulk", methods=["POST"])
def api_bulk():
    file = request.files.get("file")

    if not file:
        return {"error": "No file uploaded"}, 400

    from app.utils import read_bulk_file, async_process_bulk

    urls = read_bulk_file(file)
    if not urls:
        return {"error": "No valid URLs found"}, 400

    results = asyncio.run(async_process_bulk(urls))
    return {"results": results}

@main_blueprint.route("/healthz", methods=["GET"])
def health_check():
    """
    Simple health check for load balancers / uptime monitors.
    Returns 200 OK when server is running.
    """
    return {"status": "ok"}, 200


# keep CORS headers, do NOT override Content-Type for HTML pages
@main_blueprint.after_request
def add_headers(response):
    # Allow JS frontends to call the API
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response



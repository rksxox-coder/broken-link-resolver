from flask import Blueprint, request, jsonify
from .utils import process_single_url

api_bp = Blueprint("api", __name__)

@api_bp.route("/find", methods=["GET"])
def api_find():
    """
    /api/find?url=https://example.com/page
    Returns JSON with best alternative + candidates list.
    """

    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "url parameter is required"}), 400

    result = process_single_url(url)

    return jsonify(result), 200

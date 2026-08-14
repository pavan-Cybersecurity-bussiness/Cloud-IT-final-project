"""
API gateway — the single entry point the frontend talks to.

Routes /api/auth/*      -> auth-service
       /api/listings/*  -> listings-service
       /api/inquiries/* -> messaging-service

Each backend service exposes root-relative routes (e.g. listings-service
has "/", "/<id>", "/mine" — not "/listings/mine"). The gateway is what adds
the "/api/<service>" prefix the outside world sees, then strips it back off
before forwarding. This is what lets each service be built, tested, and
deployed on its own, with the gateway as the only thing that knows how
they're all wired together.
"""
import os

import requests
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

AUTH_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001")
LISTINGS_URL = os.environ.get("LISTINGS_SERVICE_URL", "http://listings-service:5002")
MESSAGING_URL = os.environ.get("MESSAGING_SERVICE_URL", "http://messaging-service:5003")

app = Flask(__name__)
CORS(app)  # scoped to this class project: open CORS so the static frontend
           # can be hosted anywhere without a matching-origin requirement.

SERVICE_MAP = {
    "auth": AUTH_URL,
    "listings": LISTINGS_URL,
    "inquiries": MESSAGING_URL,
}

# Headers that must not be blindly forwarded between hops (RFC 7230 §6.1,
# plus content-length/host which get recalculated by the HTTP client).
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length", "host",
}


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "gateway"})


@app.route("/api/<service>", methods=["GET", "POST"], defaults={"subpath": ""})
@app.route("/api/<service>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(service, subpath):
    base_url = SERVICE_MAP.get(service)
    if base_url is None:
        return jsonify({"error": f"Unknown service '{service}'."}), 404

    target = f"{base_url}/{subpath}"

    files = {k: (f.filename, f.stream, f.mimetype) for k, f in request.files.items()}
    has_form_payload = bool(request.form) or bool(files)

    forward_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS
    }
    if has_form_payload:
        # requests will build its own multipart boundary (or urlencode the
        # dict) from data=/files= below — forwarding the original
        # Content-Type here would ship the OLD boundary with a body encoded
        # against a NEW one, and the receiving service fails to parse
        # anything out of it. Let requests set the correct header itself.
        forward_headers = {k: v for k, v in forward_headers.items() if k.lower() != "content-type"}
        body_kwargs = dict(data=request.form, files=files or None)
    else:
        body_kwargs = dict(data=request.get_data())

    upstream = requests.request(
        method=request.method,
        url=target,
        headers=forward_headers,
        params=request.args,
        timeout=15,
        stream=True,
        **body_kwargs,
    )

    response_headers = [
        (k, v) for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS
    ]
    return Response(upstream.content, upstream.status_code, response_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

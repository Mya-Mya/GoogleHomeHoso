import argparse
import base64
import threading
from pathlib import Path

from flask import Flask, render_template, jsonify, request, Response
from nanoid import generate as generate_nanoid

from googlehomes import GoogleHomePlayer, discover_devices
from ttsutils import text_to_speech_bytes

AUDIO_CACHE_DIR = Path(__file__).parent / "audio_cache"
EXPIRE_SECONDS = 60  # 数秒で失効


def _ensure_storage_dir() -> None:
    AUDIO_CACHE_DIR.mkdir(exist_ok=True)


def save_audio(audio_bytes: bytes) -> str:
    _ensure_storage_dir()

    audio_id = generate_nanoid()
    path = _path_for(audio_id)
    assert path
    path.write_bytes(audio_bytes)

    timer = threading.Timer(EXPIRE_SECONDS, _delete_audio, args=(audio_id,))
    timer.daemon = True
    timer.start()

    return audio_id


def load_audio(audio_id: str) -> bytes | None:
    path = _path_for(audio_id)
    if path is None or not path.exists():
        return None
    return path.read_bytes()


def _delete_audio(audio_id: str) -> None:
    path = AUDIO_CACHE_DIR / f"{audio_id}.mp3"
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _path_for(audio_id: str) -> Path | None:
    if not audio_id or any(not (c.isalnum() or c in "_-") for c in audio_id):
        return None
    return AUDIO_CACHE_DIR / f"{audio_id}.mp3"


googlehome_player: GoogleHomePlayer | None = None
server_address: str | None = None
server_port: int | None = None


def let_googlehome_play_audio(
    url: str | None = None,
    base64_data: str | None = None,
    audio_bytes: bytes | None = None,
    content_type: str = "audio/mpeg",
) -> tuple[bool, str]:
    assert googlehome_player, "Google Home player is not initiated."
    assert server_address and server_port, "Server address/port not set."

    # Decode base64 if provided
    if base64_data:
        try:
            audio_bytes = base64.b64decode(base64_data)
        except Exception as e:
            return False, str(e)

    # Generate URL from audio_bytes if available
    if audio_bytes:
        try:
            audio_id = save_audio(audio_bytes)
            url = f"http://{server_address}:{server_port}/api/audio/{audio_id}"
        except Exception as e:
            return False, str(e)

    # Play media if URL is available
    if url:
        return googlehome_player.play_media(url, content_type=content_type)

    return False, "Either url, base64_data, or audio_bytes is required."


app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        googlehome_address=googlehome_player.address if googlehome_player else None,
        googlehome_port=googlehome_player.port if googlehome_player else None,
        server_address=server_address,
        server_port=server_port,
    )


@app.route("/api/speak", methods=["POST"])
def api_speak():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "The text is empty."}), 400

    try:
        audio_bytes = text_to_speech_bytes(text)
        success, message = let_googlehome_play_audio(audio_bytes=audio_bytes)
        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"status": "Success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/play", methods=["POST"])
def api_play():
    data = request.get_json()
    url = data.get("url")
    base64_data = data.get("base64")
    content_type = data.get("content_type", "audio/mpeg")

    if not url and not base64_data:
        return jsonify({"error": "Either url or base64 is required."}), 400

    try:
        success, message = let_googlehome_play_audio(
            url=url, base64_data=base64_data, content_type=content_type
        )
        if not success:
            return jsonify({"error": message}), 400
        return jsonify({"status": "Success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/audio/<audio_id>", methods=["GET"])
def api_audio(audio_id: str):
    audio_bytes = load_audio(audio_id)
    if audio_bytes is None:
        return (
            jsonify({"error": f"The audio {audio_id} not found."}),
            404,
        )

    return Response(audio_bytes, mimetype="audio/mpeg")


@app.route("/api/devices", methods=["GET"])
def api_devices():
    try:
        devices = discover_devices(timeout=5)
        return jsonify({"devices": devices})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def main():
    global googlehome_player, server_address, server_port

    parser = argparse.ArgumentParser(description="Google Home Hoso Server")
    parser.add_argument("--gh-address", help="Google Home address", required=True)
    parser.add_argument(
        "--gh-port",
        type=int,
        default=8009,
        help="Google Home port (Default: 8009)",
    )
    parser.add_argument(
        "--address",
        default="0.0.0.0",
        help="Server bind address (Default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=9000, help="Server port (Default: 9000)"
    )
    parser.add_argument(
        "--server-address",
        help="The server address as seen by the Google Home device",
        required=True,
    )

    args = parser.parse_args()
    server_address = args.server_address
    server_port = args.port

    googlehome_player = GoogleHomePlayer(address=args.gh_address, port=args.gh_port)

    print("Connecting Google Home device...", end=" ")
    success, message = googlehome_player.connect()
    if success:
        print("✅")
    else:
        print("❌", message)
        exit(-1)

    app.run(debug=False, host=args.address, port=args.port)


if __name__ == "__main__":
    main()

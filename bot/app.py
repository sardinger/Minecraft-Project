from flask import Flask, jsonify, request
from bot import BuilderBot
from bot_skills import build_from_json
import json

app = Flask(__name__)

BOT_INSTANCE = None  # global bot instance


def complete_schematic(data):
    # in case data is a str
    if not isinstance(data, dict):
        # Find the last completed object
        last_brace = data.rfind("}")
        if last_brace == -1:
            return None

        trimmed = data[: last_brace + 1]
        # Close blocks array and top-level object if missing
        trimmed = trimmed.rstrip()

        if not trimmed.endswith("]}"):
            trimmed += "]}"

        return json.loads(trimmed)

    return data  # already complete


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/bot")
def bot():
    global BOT_INSTANCE
    username = request.args.get("username")

    if BOT_INSTANCE is None:
        BOT_INSTANCE = BuilderBot(username)

        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"})


@app.route("/build", methods=["POST"])
def build():
    if BOT_INSTANCE is None:
        return jsonify({"error": "no_bot"}), 400

    data = request.get_json()

    # Build the Pisa schematic if json is not valid
    data = complete_schematic(data)
    if data is None:
        with open("../schematics/pisa-2.json", "r") as f:
            data = json.load(f)
    # TODO: Make build_from_json a function in bot class so I can call chat
    build_from_json(BOT_INSTANCE.bot, data)
    num_blocks = len(data.get("blocks", []))
    return jsonify({"status": "built", "blocks": num_blocks})


if __name__ == "__main__":
    app.run()

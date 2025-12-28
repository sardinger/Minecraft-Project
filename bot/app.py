from flask import Flask, jsonify, request
from bot import BuilderBot
from bot_skills import build_from_json
import json

app = Flask(__name__)

BOT_INSTANCE = None  # global bot instance


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/bot")
def bot():
    global BOT_INSTANCE

    if BOT_INSTANCE is None:
        BOT_INSTANCE = BuilderBot()

        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"})


@app.route("/build", methods=["POST"])
def build():
    if BOT_INSTANCE is None:
        return jsonify({"error": "no_bot"}), 400

    data = request.get_json()

    # TODO: Build the triangle schematic if json is not valid
    with open("../schematics/triangle-1.json", "r") as f:
        data = json.load(f)
    # TODO: Make build_from_json a function in bot class so I can call chat
    build_from_json(BOT_INSTANCE.bot, data)
    return jsonify({"status": "built"})

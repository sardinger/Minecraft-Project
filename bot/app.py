from flask import Flask
from bot import BuilderBot

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/bot")
def bot():
    bot = BuilderBot()
    return {"success": 1}

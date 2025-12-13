from javascript import require, On
from dotenv import load_dotenv
import os
import socket

load_dotenv(override=True)
claude_key = os.getenv("ANTHROPIC_API_KEY")

mineflayer = require("mineflayer")


class BuilderBot:
    def __init__(self):
        """
        Initializes a bot in Minecraft
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        try:
            print(ip)
            host = ip
            port = 54569
            username = "R2D2"  # Replace with the desired bot username
            self.bot = mineflayer.createBot(
                {
                    "host": host,
                    "port": port,
                    "username": username,
                }
            )
            self.setup_listeners()
        except Exception as e:
            print("Failed to start bot")
            return

    def setup_listeners(self):
        @On(self.bot, "spawn")
        def handle_spawn(*args):
            """
            Spawns the bot next to you (need player coords)
            """
            self.bot.chat(f"/tp AustinMinty")  # TODO: don't hard code this

            # TODO: give the bot context
            # self.codeGen = MinecraftCodeGenerator()

        @On(self.bot, "chat")
        def on_chat(this, sender, message, *args):
            """
            Handles chats
            :param sender: The sender of the message
            :param message: The message that got sent
            """
            if sender == self.bot.username:
                return

            message = str(message)

            if message.lower() == "come":
                self.bot.chat(f"/tp AustinMinty")

        @On(self.bot, "end")
        def on_end(*args):
            """
            Ends the bot
            """
            print("Bot disconnected.")

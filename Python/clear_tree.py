import discord
from discord import app_commands
import os
from dotenv import load_dotenv



dotenv_path = os.path.join(os.path.dirname(__file__), '..','..', '.env')
load_dotenv(dotenv_path)
guild_ids_str = str(os.getenv('guildIDs'))
guild_ids = guild_ids_str.split(',')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)




@client.event
async def on_ready():
    print("Synchronisiere neue Befehle...")
    i = 1
    for guild_id in guild_ids:
            await tree.sync(guild=discord.Object(id=int(guild_id)))
            print(f"synchronisiert für Server {i}")
            i += 1 
    print("Befehle wurden Synchronisiert! \n============================== \nDer Bot ist Bereit!")


client.run(os.getenv('bot_token'))


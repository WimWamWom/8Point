import discord
from discord import app_commands
import logging
import os
from dotenv import load_dotenv
from bot_def import create_clan_embed, create_list_embed
from bot_def_clan import get_clan_info, get_clan_name_and_tag, refresh_rolls, load_rolls
from eight_point_json import load_clans, save_clans
import json



dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)
guild_ids_str = str(os.getenv('guildIDs'))
guild_ids = guild_ids_str.split(',')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


log_dir = os.path.join(os.path.dirname(__file__), 'Logs')
if not os.path.exists(log_dir):
        os.makedirs(log_dir)

# Zählt die bestehenden Logdateien und bestimmt den nächsten Namen
log_files = [f for f in os.listdir(log_dir) if f.startswith('log-') and f.endswith('.txt')]
log_files.sort()

# Wenn keine Log-Dateien existieren, starte bei log-01
if not log_files:
    log_path = os.path.join(log_dir, 'log-01.txt')
else:
    # Hole die höchste Zahl und erhöhe sie um 1
    highest_number = max([int(f.split('-')[1].split('.')[0]) for f in log_files])
    log_path = os.path.join(log_dir, f'log-{highest_number + 1:02d}.txt')



logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)





# Speichert Kanal- und Nachrichten-ID in einer JSON-Datei
def save_channel_message_info(channel_id, message_id):
    data = {}
    # Versuche, bestehende Daten zu laden
    if os.path.exists('channel_message_data.json'):
        with open('channel_message_data.json', 'r') as f:
            data = json.load(f)

    # Füge Kanal- und Nachrichten-ID hinzu
    data[channel_id] = message_id

    # Speichere die aktualisierten Daten
    with open('channel_message_data.json', 'w') as f:
        json.dump(data, f)

# Lädt die Kanal- und Nachrichten-ID aus der JSON-Datei
def load_channel_message_info():
    if os.path.exists('channel_message_data.json'):
        with open('channel_message_data.json', 'r') as f:
            return json.load(f)
    return {}

class ClanSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Wähle einen Clan", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        clan_tag = self.values[0]

        # Logge den Befehl
        logging.info(f'Befehl "ClanSelect" ausgeführt mit Clan: {clan_tag}')
        
        # Erhalte die Kanal- und Nachrichten-ID aus der gespeicherten Datei
        channel_message_info = load_channel_message_info()
        channel_id = interaction.channel.id
        if channel_id in channel_message_info:
            message_id = channel_message_info[channel_id]
            message = await interaction.channel.fetch_message(message_id)
        else:
            message = interaction.message
        
        if clan_tag == "all":
            embeds = []
            for option in self.options[1:]:
                embed = create_clan_embed(get_clan_info(option.value))
                embeds.append(embed)
            
            if embeds:
                await message.edit(embeds=embeds, view=self.view)    
            else:
                await interaction.followup.send("Keine Clan-Informationen gefunden.", ephemeral=True)

            self.placeholder = "Alle Clans anzeigen"
            await message.edit(view=self.view)
        else:
            clan_info = get_clan_info(clan_tag)
            if clan_info:
                embed = create_clan_embed(clan_info)
                await message.edit(embed=embed, view=self.view)

                self.placeholder = f"Ausgewählter Clan: {clan_info['name']}"
                await message.edit(view=self.view)  
            else:
                await interaction.followup.send("Clan-Information nicht gefunden.", ephemeral=True)

class ClanView(discord.ui.View):
    def __init__(self, clans, droplist_options):
        super().__init__()
        self.clans = clans
        self.add_item(ClanSelect(droplist_options))

class MemberSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Alle Mitglieder", value="Alle"),
            discord.SelectOption(label="Anführer", value="Anführer"),
            discord.SelectOption(label="Vize Anführer", value="Vize Anführer"),
            discord.SelectOption(label="Älteste", value="Älteste"),
            discord.SelectOption(label="Mitglieder", value="Mitglieder")
        ]
        super().__init__(placeholder="Wähle eine Rolle", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = self.values[0]

        # Logge den Befehl
        logging.info(f'Befehl "MemberSelect" ausgeführt mit Rolle: {role}')
        
        # Erhalte die Kanal- und Nachrichten-ID aus der gespeicherten Datei
        channel_message_info = load_channel_message_info()
        channel_id = interaction.channel.id
        if channel_id in channel_message_info:
            message_id = channel_message_info[channel_id]
            message = await interaction.channel.fetch_message(message_id)
        else:
            message = interaction.message
        
        if role == "Alle":
            embeds = []
            roles = ["leader", "vize", "elders", "members"]
            for role in roles:
                members = load_rolls(role)
                embed = create_list_embed(role.capitalize(), members)
                embeds.append(embed)

            await message.edit(embeds=embeds)

        elif role == "Anführer":
            member = load_rolls("leader")
            embed = create_list_embed("Anführer", member)
            await message.edit(embed=embed)

        elif role == "Vize Anführer":
            member = load_rolls("vize")
            embed = create_list_embed("Vize Anführer", member)
            await message.edit(embed=embed)

        elif role == "Älteste":
            member = load_rolls("elders")
            embed = create_list_embed("Älteste", member)
            await message.edit(embed=embed)

        elif role == "Mitglieder":
            member = load_rolls("members")
            embed = create_list_embed("Mitglieder", member)
            await message.edit(embed=embed)

        self.placeholder = f"Ausgewählte Rolle: {role}"
        await message.edit(view=self.view)

class MemberView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(MemberSelect())

for guild_id in guild_ids:
    @tree.command(name="clan-übersicht", description="Zeige ein Übersicht der Clan Informationen an.", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(clan_option="Wähle entweder '8Point Clans' oder gib eigene Kürzel ein")
    @app_commands.choices(clan_option=[
        app_commands.Choice(name="8Point Clans", value="8point"),
        app_commands.Choice(name="Kürzel eingeben (mit  , seperieren)", value="custom")
    ])
    async def clan_infos(interaction: discord.Interaction, clan_option: app_commands.Choice[str], clan_tags: str = None):
        logging.info(f'Befehl "clan-übersicht" ausgeführt mit clan_option: {clan_option.value} und clan_tags: {clan_tags}')
        
        await interaction.response.defer()

        if clan_option.value == "8point":
            clan_list = load_clans()
        elif clan_option.value == "custom":
            if not clan_tags:
                await interaction.followup.send("Bitte gib mindestens ein Clan-Kürzel ein!", ephemeral=True)
                return
            clan_list = [tag.strip() for tag in clan_tags.split(",")]

        logging.info(f'Befehl "clan-übersicht" ausgeführt mit {clan_option.value} und {clan_list}')
        print(f'Befehl "clan-übersicht" ausgeführt mit {clan_option.value} und {clan_list}')

        embeds = []
        droplist_options = []
        if len(clan_list) > 1:
            droplist_options.append(discord.SelectOption(label="Alle Clans anzeigen", value="all"))

        for tag in clan_list:
            clan_info = get_clan_info(tag)
            if clan_info:
                embeds.append(create_clan_embed(clan_info))
                name = get_clan_name_and_tag(tag)
                droplist_options.append(discord.SelectOption(label=name, value=tag))

        if len(clan_list) > 1:
            if embeds:
                view = ClanView(clan_list, droplist_options)
                await interaction.followup.send(embeds=embeds, view=view)
            else:
                await interaction.followup.send("Kein gültiges Clan-Kürzel gefunden. Bitte überprüfe deine Eingabe.", ephemeral=True)
        elif len(clan_list) == 1:
            if embeds:
                await interaction.followup.send(embeds=embeds)
            else:
                await interaction.followup.send("Kein gültiges Clan-Kürzel gefunden. Bitte überprüfe deine Eingabe.", ephemeral=True)
        else:
            await interaction.followup.send("Kein gültiges Clan-Kürzel gefunden. Bitte überprüfe deine Eingabe.", ephemeral=True)


    @tree.command(name="8point-clans", description="Clan-Management für 8Point Clans.", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(
        action="Wähle eine Aktion", 
        clan_tag="Gib das Clan-Kürzel an", 
        position="An welcher Stelle soll der Clan hinzugefügt werden? (1 für Anfang, 0 für Ende)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Anzeigen", value="show"),
        app_commands.Choice(name="Hinzufügen", value="add"),
        app_commands.Choice(name="Entfernen", value="remove")
    ])
    async def manage_8point_clans(
        interaction: discord.Interaction, 
        action: app_commands.Choice[str], 
        clan_tag: str = None, 
        position: int = 0
    ):
        logging.info(f'Befehl "8point-clans" ausgeführt mit action: {action.value}, clan_tag: {clan_tag} und position: {position}')
        await interaction.response.defer()
        
        clans = load_clans()
        guild = interaction.guild
        user = interaction.user
        role = discord.utils.get(guild.roles, name="8P Vize")

        if action.value == "show":
            if not clans:
                await interaction.followup.send("Es sind keine Clans gespeichert.", ephemeral=True)
                return

            clan_list = []
            for tag in clans:
                clan_name_and_tag = get_clan_name_and_tag(tag)  # Holt den Clan-Namen anhand des Tags
                if clan_name_and_tag:
                    clan_list.append(clan_name_and_tag  )  # Format: Name (#Kürzel)
                else:
                    clan_list.append(tag)  # Falls kein Name gefunden wird, nur das Kürzel anzeigen

            emded = create_list_embed("Aktuelle Clans", clan_list)
            await interaction.followup.send(embed=emded)

        
        elif action.value == "add":

            if role not in user.roles:
                await interaction.followup.send("❌ Du hast keine Berechtigung, die Befehl zu verwenden.", ephemeral=True)
                return
            
            if not clan_tag:
                await interaction.followup.send("Bitte gib ein Clan-Kürzel zum Hinzufügen an.", ephemeral=True)
                return

            if clan_tag in clans:
                await interaction.followup.send(f"Clan {clan_tag} ist bereits gespeichert.", ephemeral=True)
                return

            # Standard: Clan wird ans Ende eingefügt
            if position <= 0 or position > len(clans):
                clans.append(clan_tag)
                pos_text = "am Ende"
            else:
                clans.insert(position - 1, clan_tag)  # -1 wegen Index-Verschiebung
                pos_text = f"an Position {position}"

            save_clans(clans)
            await interaction.followup.send(f"Clan {clan_tag} wurde {pos_text} eingefügt.")

        elif action.value == "remove":

            if role not in user.roles:
                await interaction.followup.send("❌ Du hast keine Berechtigung, die Befehl zu verwenden.", ephemeral=True)
                return
                 
            if not clan_tag:
                await interaction.followup.send("Bitte gib ein Clan-Kürzel zum Entfernen an.", ephemeral=True)
                return

            if clan_tag in clans:
                clans.remove(clan_tag)
                save_clans(clans)
                await interaction.followup.send(f"Clan {clan_tag} wurde entfernt.")
            else:
                await interaction.followup.send(f"Clan {clan_tag} wurde nicht gefunden.", ephemeral=True)


    @tree.command(name="mitglieder", description="Zeige ein Übersicht 8Point Mitglieder.", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(mitglieder="Wähle aus welche rolle angezeigt werden soll. Und ob die liste vor der Ausgabe aktualisiert werden soll.[Ja / Nein]")
    @app_commands.choices(mitglieder=[
        app_commands.Choice(name="Alle Mitlglieder", value="all"),
        app_commands.Choice(name="Anführer", value="leader"),
        app_commands.Choice(name="Vize", value="vize"),
        app_commands.Choice(name="Älteser", value="elder"),
        app_commands.Choice(name="Mitlgied", value="member"),
    ],
        aktualisieren =[
        app_commands.Choice(name="Ja", value="Ja"),
        app_commands.Choice(name="Nein", value="Nein")
    ])
    async def clan_infos(interaction: discord.Interaction, mitglieder: app_commands.Choice[str], aktualisieren: str = "Nein"):

        logging.info(f'Befehl "mitglieder" ausgeführt mit Rolle: {mitglieder.value} und aktualisieren: {aktualisieren}')
        print(f'Befehl "mitglieder" ausgeführt mit Rolle: {mitglieder.value} und aktualisieren: {aktualisieren}')

        await interaction.response.defer()
        view = MemberView()
        if aktualisieren.lower() == "ja":
            clans = load_clans()
            refresh_rolls(clans)

        if mitglieder.value == "all":
            embeds = []
            roles = ["leader", "vize", "elders", "members"]
            for role in roles:
                mitglieder = load_rolls(role)
                embed = create_list_embed(role.capitalize(), mitglieder)
                embeds.append(embed)


            await interaction.followup.send(embeds=embeds, view= view)

        elif mitglieder.value == "leader":
            member = load_rolls("leader")
            embed = create_list_embed("Anführer", member)
            await interaction.followup.send(embed=embed, view= view)

        elif mitglieder.value == "vize":
            member = load_rolls("vize")
            embed = create_list_embed("Vize Anführer", member)
            await interaction.followup.send(embed=embed, view= view)

        elif mitglieder.value == "elder":
            member = load_rolls("elders")
            embed = create_list_embed("Älteste", member)
            await interaction.followup.send(embed=embed, view= view)

        elif mitglieder.value == "member":
            member = load_rolls("members")
            embed = create_list_embed("Mitglieder", member)
            await interaction.followup.send(embed=embed, view= view)


@client.event
async def on_ready():

    logging.info(f'Eingeloggt als {client.user}  \nSynchronisiere neue Befehle...')
    print(f'Eingeloggt als {client.user}  \nSynchronisiere neue Befehle...')

    i = 1
    for guild_id in guild_ids:
            await tree.sync(guild=discord.Object(id=int(guild_id)))
            logging.info(f"Synchronisiert für Server {i}")
            print(f"Synchronisiert für Server {i}")
            i += 1 

    logging.info("Befehle wurden Synchronisiert! \n============================== \nDer Bot ist Bereit!")
    print("Befehle wurden Synchronisiert! \n============================== \nDer Bot ist Bereit!")

client.run(os.getenv('bot_token'))

import discord
from discord import app_commands
import logging
import os
from dotenv import load_dotenv
from bot_def import create_clan_embed, create_list_embed
from bot_def_clan import get_clan_info, get_clan_name_and_tag, refresh_rolls, load_rolls
from eight_point_json import load_clans, save_clans
import json
import asyncio



dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)
guild_ids_str = str(os.getenv('guildIDs'))
guild_ids = guild_ids_str.split(',')

intents = discord.Intents.default()
# Benötigt, damit Mitglieder- und Rollenlisten verfügbar sind
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# IDs der relevanten Rollen
NEULING_ROLE_ID = 1426115963073335357
VERKNY_ROLE_ID = 1426121677904810014  # "Verknüpft"

# Limits, um Rate Limits zu vermeiden (pro Gilde und Zyklus)
MAX_ADD_NEULING_PER_CYCLE = 50  # maximale Anzahl an 'Neuling'-Vergaben je 30s
MAX_REMOVE_NEULING_PER_CYCLE = 200  # Sicherheitslimit für Entfernen (typisch klein)

# Persistenz-Datei für per-Gilde Einstellungen
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'link_check_settings.json')
JOIN_ROLE_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'join_role_settings.json')

def load_link_check_settings():
    """Lädt die IDs der Gilden, für die der Check aktiviert ist."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(int(x) for x in data)
    except Exception as e:
        logging.error(f"Fehler beim Laden der Verknüpfungs-Check Einstellungen: {e}")
    return set()

def save_link_check_settings(enabled_guilds: set):
    """Speichert die IDs der Gilden, für die der Check aktiviert ist."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(enabled_guilds)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Verknüpfungs-Check Einstellungen: {e}")


def load_join_role_settings():
    """Lädt die Join-Rolle pro Gilde. Rückgabe: Dict[int guild_id -> int role_id]"""
    try:
        if os.path.exists(JOIN_ROLE_SETTINGS_FILE):
            with open(JOIN_ROLE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Keys/Gilden als int sicherstellen
                return {int(g): int(r) for g, r in data.items()}
    except Exception as e:
        logging.error(f"Fehler beim Laden der Join-Rollen Einstellungen: {e}")
    return {}

def save_join_role_settings(join_roles: dict):
    """Speichert die Join-Rolle pro Gilde."""
    try:
        with open(JOIN_ROLE_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            # Keys als Strings für JSON Speichern
            json.dump({str(g): int(r) for g, r in join_roles.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Join-Rollen Einstellungen: {e}")

# Pro-Server-Schalter für die periodische Überprüfung (standardmäßig aus)
link_check_enabled_guilds = set()
_background_task_started = False
join_role_by_guild: dict[int, int] = {}


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

# Zusätzlich auch in die Konsole (cmd) loggen
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_formatter)
root_logger = logging.getLogger()
# Doppeltes Hinzufügen vermeiden (z.B. bei Reloads)
if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
    root_logger.addHandler(console_handler)





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
        logging.info(f'Befehl "ClanSelect" ausgefuehrt mit Clan: {clan_tag}')
        
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
        logging.info(f'Befehl "MemberSelect" ausgefuehrt mit Rolle: {role}')
        
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


async def _run_link_check_once():
    """Prüft auf allen konfigurierten Servern: Wenn ein Nutzer die Rolle 'Neuling' und 'Verknüpft' hat, entferne 'Neuling'."""
    try:
        for gid in guild_ids:
            guild = client.get_guild(int(gid))
            if guild is None:
                continue

            # Überspringen, wenn diese Gilde nicht aktiviert ist
            if guild.id not in link_check_enabled_guilds:
                continue

            await _run_link_check_for_guild(guild)
    except Exception as e:
        logging.error(f"Unerwarteter Fehler im Verknüpfungs-Check: {e}")


async def _link_check_loop():
    """Hintergrund-Task, der alle 30 Sekunden den Check ausführt, wenn aktiviert."""
    await client.wait_until_ready()
    while True:
        try:
            await _run_link_check_once()
        finally:
            # Immer schlafen, auch wenn ein Fehler auftrat
            await asyncio.sleep(30)


async def _run_link_check_for_guild(guild: discord.Guild) -> int:
    """Führt den Verknüpfungs-Check für eine einzelne Gilde aus.

    - Entfernt 'Neuling' bei Mitgliedern, die bereits 'Verknüpft' haben
    - Vergibt 'Neuling' an alle Nicht-Bot-Mitglieder, die NICHT 'Verknüpft' haben

    Rückgabe: Anzahl der entfernten 'Neuling'-Rollen (Kompatibilität für bestehende Ausgaben).
    """
    removed = 0
    added = 0
    neuling_role = guild.get_role(NEULING_ROLE_ID)
    verkn_role = guild.get_role(VERKNY_ROLE_ID)

    if not neuling_role or not verkn_role:
        logging.warning(f"Rollen nicht gefunden in Gilde {guild.name}: Neuling={bool(neuling_role)} Verknüpft={bool(verkn_role)}")
        return 0

    # Prüfen, ob der Bot diese Rolle verwalten darf (Hierarchie)
    try:
        me = guild.me or await guild.fetch_member(client.user.id)
        if me.top_role <= neuling_role:
            logging.error(f"Kann Rolle '{neuling_role.name}' in {guild.name} nicht verwalten (Rollen-Hierarchie).")
            # Wir versuchen trotzdem das Entfernen (falls erlaubt), aber kein Hinzufügen.
            can_add_neuling = False
        else:
            can_add_neuling = True
    except Exception as e:
        logging.error(f"Fehler beim Prüfen der Rollen-Hierarchie in {guild.name}: {e}")
        can_add_neuling = False

    # 1) 'Neuling' entfernen, wenn 'Verknüpft' vorhanden ist
    for member in list(neuling_role.members):
        try:
            if verkn_role in member.roles:
                await member.remove_roles(neuling_role, reason="Auto-Check: 'Verknüpft' vorhanden, 'Neuling' entfernt")
                removed += 1
                logging.info(f"Entferne 'Neuling' von {member} in Gilde {guild.name} (hat 'Verknüpft')")
        except Exception as e:
            logging.error(f"Fehler beim Entfernen der Rolle 'Neuling' von {member} in {guild.name}: {e}")
    if removed:
        logging.info(f"{removed} Mitglied(er) in {guild.name}: 'Neuling' entfernt.")

    # 2) 'Neuling' vergeben an alle Nicht-Bots ohne 'Verknüpft'
    if can_add_neuling:
        try:
            for member in guild.members:
                # Bots nicht berücksichtigen
                if getattr(member, 'bot', False):
                    continue
                # Wenn keine 'Verknüpft'-Rolle vorhanden ist
                if verkn_role not in member.roles:
                    # Nur hinzufügen, wenn noch nicht vorhanden
                    if neuling_role not in member.roles:
                        try:
                            await member.add_roles(neuling_role, reason="Auto-Check: Keine 'Verknüpft'-Rolle, 'Neuling' vergeben")
                            added += 1
                            logging.info(f"Vergebe 'Neuling' an {member} in Gilde {guild.name} (ohne 'Verknüpft')")
                        except Exception as e:
                            logging.error(f"Fehler beim Vergeben der Rolle 'Neuling' an {member} in {guild.name}: {e}")
        except Exception as e:
            logging.error(f"Fehler beim Durchlauf zum Vergeben von 'Neuling' in {guild.name}: {e}")
        if added:
            logging.info(f"{added} Mitglied(er) in {guild.name}: 'Neuling' vergeben (ohne 'Verknüpft').")
    return removed

for guild_id in guild_ids:
    @tree.command(name="clan-übersicht", description="Zeige ein Übersicht der Clan Informationen an.", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(clan_option="Wähle entweder '8Point Clans' oder gib eigene Kürzel ein")
    @app_commands.choices(clan_option=[
        app_commands.Choice(name="8Point Clans", value="8point"),
        app_commands.Choice(name="Kürzel eingeben (mit  , seperieren)", value="custom")
    ])
    async def clan_infos(interaction: discord.Interaction, clan_option: app_commands.Choice[str], clan_tags: str = None):
        logging.info(f'Befehl "clan-übersicht" ausgefuehrt mit clan_option: {clan_option.value} und clan_tags: {clan_tags}')
        # Sofortiges Defer mit thinking=True, um Zeitüberschreitungen zu vermeiden
        await interaction.response.defer(thinking=True)

        if clan_option.value == "8point":
            clan_list = load_clans()
        elif clan_option.value == "custom":
            if not clan_tags:
                await interaction.followup.send("Bitte gib mindestens ein Clan-Kürzel ein!", ephemeral=True)
                return
            clan_list = [tag.strip() for tag in clan_tags.split(",")]

        logging.info(f'Befehl "clan-übersicht" ausgefuehrt mit {clan_option.value} und {clan_list}')
        print(f'Befehl "clan-übersicht" ausgefuehrt mit {clan_option.value} und {clan_list}')

        embeds = []
        droplist_options = []
        invalid_tags: list[str] = []
        if len(clan_list) > 1:
            droplist_options.append(discord.SelectOption(label="Alle Clans anzeigen", value="all"))

        for tag in clan_list:
            clan_info = get_clan_info(tag)
            if clan_info:
                embeds.append(create_clan_embed(clan_info))
                name = get_clan_name_and_tag(tag) or f"{clan_info['name']} ({clan_info['tag']})"
                droplist_options.append(discord.SelectOption(label=name, value=tag))
            else:
                invalid_tags.append(tag)

        if len(clan_list) > 1:
            if embeds:
                view = ClanView(clan_list, droplist_options)
                await interaction.followup.send(embeds=embeds, view=view)
            else:
                msg = "Kein gültiges Clan-Kürzel gefunden."
                if invalid_tags:
                    msg += f" Ungültig/Fehler: {', '.join(invalid_tags)}"
                await interaction.followup.send(msg + " Bitte überprüfe deine Eingabe.", ephemeral=True)
        elif len(clan_list) == 1:
            if embeds:
                await interaction.followup.send(embeds=embeds)
            else:
                msg = "Kein gültiges Clan-Kürzel gefunden."
                if invalid_tags:
                    msg += f" Ungültig/Fehler: {', '.join(invalid_tags)}"
                await interaction.followup.send(msg + " Bitte überprüfe deine Eingabe.", ephemeral=True)
        else:
            msg = "Kein gültiges Clan-Kürzel gefunden."
            if invalid_tags:
                msg += f" Ungültig/Fehler: {', '.join(invalid_tags)}"
            await interaction.followup.send(msg + " Bitte überprüfe deine Eingabe.", ephemeral=True)


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
        logging.info(f'Befehl "8point-clans" ausgefuehrt mit action: {action.value}, clan_tag: {clan_tag} und position: {position}')
        await interaction.response.defer(thinking=True)
        
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
                    clan_list.append(clan_name_and_tag )  # Format: Name (#Kürzel)
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
        app_commands.Choice(name="Mitglied", value="member"),
    ],
        aktualisieren =[
        app_commands.Choice(name="Ja", value="Ja"),
        app_commands.Choice(name="Nein", value="Nein")
    ])
    async def clan_infos(interaction: discord.Interaction, mitglieder: app_commands.Choice[str], aktualisieren: str = "Nein"):

        logging.info(f'Befehl "mitglieder" ausgefuehrt mit Rolle: {mitglieder.value} und aktualisieren: {aktualisieren}')
        print(f'Befehl "mitglieder" ausgefuehrt mit Rolle: {mitglieder.value} und aktualisieren: {aktualisieren}')

        await interaction.response.defer(thinking=True)
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

            await interaction.followup.send(embeds=embeds, view=view)

        elif mitglieder.value == "leader":
            member = load_rolls("leader")
            embed = create_list_embed("Anführer", member)
            await interaction.followup.send(embed=embed, view=view)

        elif mitglieder.value == "vize":
            member = load_rolls("vize")
            embed = create_list_embed("Vize Anführer", member)
            await interaction.followup.send(embed=embed, view=view)

        elif mitglieder.value == "elder":
            member = load_rolls("elders")
            embed = create_list_embed("Älteste", member)
            await interaction.followup.send(embed=embed, view=view)

        elif mitglieder.value == "member":
            member = load_rolls("members")
            embed = create_list_embed("Mitglieder", member)
            await interaction.followup.send(embed=embed, view=view)


    @tree.command(name="verknuepfungs-check", description="Aktiviere oder deaktiviere die automatische Rollenprüfung (alle 30 Sekunden).", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(aktiv="'Ja' aktiviert, 'Nein' deaktiviert")
    @app_commands.choices(aktiv=[
        app_commands.Choice(name="Ja", value="Ja"),
        app_commands.Choice(name="Nein", value="Nein")
    ])
    async def verknuepfungs_check(interaction: discord.Interaction, aktiv: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Dieser Befehl kann nur auf einem Server verwendet werden.", ephemeral=True)
            return

        enable = (aktiv.value.lower() == "ja")
        if enable:
            link_check_enabled_guilds.add(guild.id)
            # Sofort einmal ausführen, damit man nicht 2 Minuten warten muss
            removed = await _run_link_check_for_guild(guild)
        else:
            link_check_enabled_guilds.discard(guild.id)
            removed = 0

        # Persistiere Änderung
        save_link_check_settings(link_check_enabled_guilds)

        status = "aktiviert" if enable else "deaktiviert"
        logging.info(f"Befehl 'verknüpfungs-check' auf {guild.name} ausgeführt: {status} (sofort entfernt: {removed})")
        await interaction.followup.send(f"Verknüpfungs-Check für diesen Server wurde {status}. Sofort entfernt: {removed} Rolle(n)", ephemeral=True)


    @tree.command(name="rolle-bei-beitritt", description="Setzt oder entfernt die Rolle, die neue Mitglieder beim Beitritt automatisch erhalten.", guild=discord.Object(id=int(guild_id)))
    @app_commands.describe(rolle="Die Rolle, die neue Mitglieder automatisch erhalten sollen. Leer lassen zum Deaktivieren.")
    async def rolle_bei_beitritt(interaction: discord.Interaction, rolle: discord.Role | None = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Dieser Befehl kann nur auf einem Server verwendet werden.", ephemeral=True)
            return

        # Optional: Berechtigungen einschränken (z.B. Administratoren)
        # if not interaction.user.guild_permissions.manage_roles:
        #     await interaction.followup.send("❌ Du benötigst die Berechtigung 'Rollen verwalten'.", ephemeral=True)
        #     return

        global join_role_by_guild
        if rolle is None:
            # Deaktivieren
            if guild.id in join_role_by_guild:
                del join_role_by_guild[guild.id]
                save_join_role_settings(join_role_by_guild)
            logging.info(f"Join-Rolle auf {guild.name} deaktiviert")
            await interaction.followup.send("Automatische Rolle beim Beitritt wurde deaktiviert.", ephemeral=True)
            return

        # Plausibilitätsprüfung: Bot darf diese Rolle vergeben (Rollen-Hierarchie)
        me = guild.me or await guild.fetch_member(client.user.id)
        if me.top_role <= rolle:
            await interaction.followup.send("❌ Ich kann diese Rolle nicht vergeben (Rollen-Hierarchie). Bitte setze meine Bot-Rolle über die gewünschte Rolle.", ephemeral=True)
            return

        join_role_by_guild[guild.id] = rolle.id
        save_join_role_settings(join_role_by_guild)
        logging.info(f"Join-Rolle auf {guild.name} gesetzt: {rolle.name} ({rolle.id})")
        await interaction.followup.send(f"Neue Mitglieder erhalten künftig automatisch die Rolle: {rolle.mention}", ephemeral=True)


@client.event
async def on_ready():

    logging.info(f'Eingeloggt als {client.user}  \nSynchronisiere neue Befehle...')
    print(f'Eingeloggt als {client.user}  \nSynchronisiere neue Befehle...')

    i = 1
    for guild_id in guild_ids:
            await tree.sync(guild=discord.Object(id=int(guild_id)))
            logging.info(f"Synchronisiert Server {i}")
            print(f"Synchronisiert Server {i}")
            i += 1 

    logging.info("Befehle wurden Synchronisiert! \n============================== \nDer Bot ist Bereit!")
    print("Befehle wurden Synchronisiert! \n============================== \nDer Bot ist Bereit!")

    # Persistierte Einstellungen laden
    global link_check_enabled_guilds
    link_check_enabled_guilds = load_link_check_settings()
    if link_check_enabled_guilds:
        logging.info(f"Verknüpfungs-Check aktiv für Gilden: {sorted(list(link_check_enabled_guilds))}")

    # Join-Rollen Einstellungen laden
    global join_role_by_guild
    join_role_by_guild = load_join_role_settings()
    if join_role_by_guild:
        logging.info(f"Join-Rolle aktiv in Gilden: { {g: r for g, r in join_role_by_guild.items()} }")

    global _background_task_started
    if not _background_task_started:
        client.loop.create_task(_link_check_loop())
        _background_task_started = True

@client.event
async def on_member_join(member: discord.Member):
    try:
        guild = member.guild
        role_id = join_role_by_guild.get(guild.id)
        if not role_id:
            return

        role = guild.get_role(role_id)
        if role is None:
            logging.warning(f"Join-Rolle existiert nicht mehr in {guild.name}: {role_id}. Entferne Einstellung.")
            # Auto-Cleanup: Setting entfernen
            join_role_by_guild.pop(guild.id, None)
            save_join_role_settings(join_role_by_guild)
            return

        # Prüfen, ob der Bot die Rolle vergeben darf
        me = guild.me or await guild.fetch_member(client.user.id)
        if me.top_role <= role:
            logging.error(f"Kann Join-Rolle {role.name} in {guild.name} nicht vergeben (Rollen-Hierarchie).")
            return

        await member.add_roles(role, reason="Auto: Rolle beim Beitritt")
        logging.info(f"Neue(r) Nutzer(in) {member} hat beim Beitritt die Rolle '{role.name}' erhalten.")
    except Exception as e:
        logging.error(f"Fehler in on_member_join für {member if 'member' in locals() else '?'}: {e}")

client.run(os.getenv('bot_token'))

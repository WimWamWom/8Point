import discord
from datetime import datetime
import pytz


def create_clan_embed(clan_info):
    level = clan_info['clan_level']
    if 1 <= level <= 5:
        farbe = '715a30'
    elif 6 <= level <= 9:
        farbe = '505c72'
    elif 10 <= level <= 11:
        farbe = 'f6a100'
    elif 12 <= level <= 13:
        farbe = 'c32ec7'
    elif 14 <= level <= 15:
        farbe = '343233'
    elif 16 <= level <= 17:
        farbe = '8d1100'
    elif 18 <= level <= 19:
        farbe = 'ca8a00'
    else:
        farbe = '2f007a'
    
    embed = discord.Embed(
        title=f"{clan_info['name']} ({clan_info['tag']})",
        url=clan_info["link"],
        color=discord.Color(int(farbe, 16))
    )
    embed.set_thumbnail(url=clan_info["badge"])

    embed.add_field(name=f"{clan_info['location']}:shield: {clan_info['clan_level']}     :trophy: {clan_info['clan_points']}     :hammer: {clan_info['clan_builder_base_points']}     :homes: {clan_info['capital_points']}", value="", inline=False)
    embed.add_field(name="", value=f"**{clan_info['description']}**", inline=False)
    embed.add_field(name=f"{clan_info['members']} Mitglieder :man_raising_hand:", value="", inline=False)
    embed.add_field(name=f"Anführer: {clan_info['leader']} :crown:", value="", inline=False)
    embed.add_field(name="Clan-Label", value=f"{clan_info['tags'][0]}\n{clan_info['tags'][1]}\n{clan_info['tags'][2]}", inline=False)
    embed.add_field(name="Vorraussetzungen", value=f":gear: {clan_info['beitritt']} \n:trophy: {clan_info['trophies']} \n:hut: Rathaus {clan_info['townhall']}", inline=False)

    if clan_info['warlogpublic']:
        embed.add_field(name="Kriegsstatistik | Verlauf Öffentlich", value=f"Siege: {clan_info['war_wins']} | Niederlagen: {clan_info['war_losses']} \nUnentschieden: {clan_info['war_ties']}  | Siegesrate: {clan_info['siegesrate']}\n Kriegshäufigkeit: {clan_info['warfrequency']}", inline=False)
    else:
        embed.add_field(name="Kriegsstatistik | Verlauf Privat", value=f"Siege: {clan_info['war_wins']}\n Kriegshäufigkeit: {clan_info['warfrequency']}", inline=False)


    timestamp = datetime.now(pytz.timezone('Europe/Berlin'))
    embed.set_footer(text="Aktualisiert" )
    embed.timestamp = timestamp 



    return embed

def create_list_embed(title: str, items: list) -> discord.Embed:

    embed = discord.Embed(title=title, color=discord.Color(int('2f007a', 16)))

    if not items:
        embed.add_field(name="Keine Einträge vorhanden.", value="", inline=False)
    else:
        list_text = "\n".join(items)  # Elemente untereinander auflisten
        embed.add_field(name="", value=list_text, inline=False)

    return embed

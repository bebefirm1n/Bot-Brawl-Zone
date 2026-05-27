import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import random
import io
import os
import time
import logging
from PIL import Image
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

try:
    from keep_alive import keep_alive
    KEEP_ALIVE_AVAILABLE = True
except ImportError:
    KEEP_ALIVE_AVAILABLE = False

load_dotenv()
TOKEN = os.getenv("TOKEN_BOT")

# ═══════════════════════════════════════════════════════════
#  101 BRAWLERS (avril 2026)
# ═══════════════════════════════════════════════════════════
BRAWLERS = [
    # ── Brawler de Départ ──────────────────────────────────
    {"name": "Shelly", "aliases": ["shelly"], "rarete": "Brawler de Départ", "role": "Dégâts Bruts"},
    # ── Rare ───────────────────────────────────────────────
    {"name": "Nita", "aliases": ["nita"], "rarete": "Rare", "role": "Dégâts Bruts"},
    {"name": "Colt", "aliases": ["colt"], "rarete": "Rare", "role": "Dégâts Bruts"},
    {"name": "Bull", "aliases": ["bull"], "rarete": "Rare", "role": "Tank"},
    {"name": "Brock", "aliases": ["brock"], "rarete": "Rare", "role": "Tireur d'élite"},
    {"name": "El Primo", "aliases": ["el primo", "primo", "elprim"], "rarete": "Rare", "role": "Tank"},
    {"name": "Barley", "aliases": ["barley"], "rarete": "Rare", "role": "Artillerie"},
    {"name": "Poco", "aliases": ["poco"], "rarete": "Rare", "role": "Soutien"},
    {"name": "Rosa", "aliases": ["rosa"], "rarete": "Rare", "role": "Tank"},
    # ── Super Rare ─────────────────────────────────────────
    {"name": "Jessie", "aliases": ["jessie"], "rarete": "Super Rare", "role": "Contrôle"},
    {"name": "Dynamike", "aliases": ["dynamike", "mike", "dyna"], "rarete": "Super Rare", "role": "Artillerie"},
    {"name": "Tick", "aliases": ["tick"], "rarete": "Super Rare", "role": "Artillerie"},
    {"name": "8-Bit", "aliases": ["8-bit", "8bit", "eightbit"], "rarete": "Super Rare", "role": "Dégâts Bruts"},
    {"name": "Rico", "aliases": ["rico"], "rarete": "Super Rare", "role": "Dégâts Bruts"},
    {"name": "Darryl", "aliases": ["darryl"], "rarete": "Super Rare", "role": "Tank"},
    {"name": "Penny", "aliases": ["penny"], "rarete": "Super Rare", "role": "Artillerie"},
    {"name": "Carl", "aliases": ["carl"], "rarete": "Super Rare", "role": "Dégâts Bruts"},
    {"name": "Jacky", "aliases": ["jacky"], "rarete": "Super Rare", "role": "Tank"},
    {"name": "Gus", "aliases": ["gus"], "rarete": "Super Rare", "role": "Soutien"},
    # ── Épique ─────────────────────────────────────────────
    {"name": "Bo", "aliases": ["bo"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Emz", "aliases": ["emz"], "rarete": "Épique", "role": "Contrôle"},
    {"name": "Stu", "aliases": ["stu"], "rarete": "Épique", "role": "Assassin"},
    {"name": "Piper", "aliases": ["piper"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Pam", "aliases": ["pam"], "rarete": "Épique", "role": "Soutien"},
    {"name": "Frank", "aliases": ["frank"], "rarete": "Épique", "role": "Tank"},
    {"name": "Bibi", "aliases": ["bibi"], "rarete": "Épique", "role": "Tank"},
    {"name": "Bea", "aliases": ["bea"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Nani", "aliases": ["nani"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Edgar", "aliases": ["edgar"], "rarete": "Épique", "role": "Assassin"},
    {"name": "Griff", "aliases": ["griff"], "rarete": "Épique", "role": "Contrôle"},
    {"name": "Grom", "aliases": ["grom"], "rarete": "Épique", "role": "Artillerie"},
    {"name": "Bonnie", "aliases": ["bonnie"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Gale", "aliases": ["gale"], "rarete": "Épique", "role": "Soutien"},
    {"name": "Colette", "aliases": ["colette"], "rarete": "Épique", "role": "Dégâts Bruts"},
    {"name": "Belle", "aliases": ["belle"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Ash", "aliases": ["ash"], "rarete": "Épique", "role": "Tank"},
    {"name": "Lola", "aliases": ["lola"], "rarete": "Épique", "role": "Dégâts Bruts"},
    {"name": "Sam", "aliases": ["sam"], "rarete": "Épique", "role": "Tank"},
    {"name": "Mandy", "aliases": ["mandy"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Maisie", "aliases": ["maisie"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Hank", "aliases": ["hank"], "rarete": "Épique", "role": "Tank"},
    {"name": "Pearl", "aliases": ["pearl"], "rarete": "Épique", "role": "Dégâts Bruts"},
    {"name": "Larry & Lawrie", "aliases": ["larry & lawrie", "larry et lawrie", "larry lawrie", "larry", "lawrie"], "rarete": "Épique", "role": "Artillerie"},
    {"name": "Angelo", "aliases": ["angelo"], "rarete": "Épique", "role": "Tireur d'élite"},
    {"name": "Berry", "aliases": ["berry"], "rarete": "Épique", "role": "Soutien"},
    {"name": "Shade", "aliases": ["shade"], "rarete": "Épique", "role": "Assassin"},
    {"name": "Meeple", "aliases": ["meeple"], "rarete": "Épique", "role": "Contrôle"},
    {"name": "Trunk", "aliases": ["trunk"], "rarete": "Épique", "role": "Tank"},
    # ── Mythique ───────────────────────────────────────────
    {"name": "Mortis", "aliases": ["mortis"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Tara", "aliases": ["tara"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Gene", "aliases": ["gene"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Max", "aliases": ["max"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Mr. P", "aliases": ["mr. p", "mr p", "mrp", "mr.p"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Sprout", "aliases": ["sprout"], "rarete": "Mythique", "role": "Artillerie"},
    {"name": "Byron", "aliases": ["byron"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Squeak", "aliases": ["squeak"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Lou", "aliases": ["lou"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Ruffs", "aliases": ["ruffs"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Buzz", "aliases": ["buzz"], "rarete": "Mythique", "role": "Tank"},
    {"name": "Fang", "aliases": ["fang"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Eve", "aliases": ["eve"], "rarete": "Mythique", "role": "Tireur d'élite"},
    {"name": "Janet", "aliases": ["janet"], "rarete": "Mythique", "role": "Tireur d'élite"},
    {"name": "Otis", "aliases": ["otis"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Buster", "aliases": ["buster"], "rarete": "Mythique", "role": "Tank"},
    {"name": "Gray", "aliases": ["gray", "grey"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "R-T", "aliases": ["r-t", "rt"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Willow", "aliases": ["willow"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Doug", "aliases": ["doug"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Chuck", "aliases": ["chuck"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Charlie", "aliases": ["charlie"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Mico", "aliases": ["mico"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Melodie", "aliases": ["melodie", "melody"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Clancy", "aliases": ["clancy"], "rarete": "Mythique", "role": "Dégâts Bruts"},
    {"name": "Moe", "aliases": ["moe"], "rarete": "Mythique", "role": "Dégâts Bruts"},
    {"name": "Juju", "aliases": ["juju"], "rarete": "Mythique", "role": "Artillerie"},
    {"name": "Ollie", "aliases": ["ollie"], "rarete": "Mythique", "role": "Tank"},
    {"name": "Finx", "aliases": ["finx"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Lumi", "aliases": ["lumi"], "rarete": "Mythique", "role": "Tireur d'élite"},
    {"name": "Jae-Yong", "aliases": ["jae-yong", "jaeyong", "jae yong"], "rarete": "Mythique", "role": "Soutien"},
    {"name": "Alli", "aliases": ["alli"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Mina", "aliases": ["mina"], "rarete": "Mythique", "role": "Dégâts Bruts"},
    {"name": "Ziggy", "aliases": ["ziggy"], "rarete": "Mythique", "role": "Contrôle"},
    {"name": "Gigi", "aliases": ["gigi"], "rarete": "Mythique", "role": "Assassin"},
    {"name": "Glowbert", "aliases": ["glowbert"], "rarete": "Mythique", "role": "Soutien"},
    # ── Légendaire ─────────────────────────────────────────
    {"name": "Spike", "aliases": ["spike"], "rarete": "Légendaire", "role": "Artillerie"},
    {"name": "Crow", "aliases": ["crow"], "rarete": "Légendaire", "role": "Assassin"},
    {"name": "Leon", "aliases": ["leon"], "rarete": "Légendaire", "role": "Assassin"},
    {"name": "Sandy", "aliases": ["sandy"], "rarete": "Légendaire", "role": "Contrôle"},
    {"name": "Amber", "aliases": ["amber"], "rarete": "Légendaire", "role": "Contrôle"},
    {"name": "Meg", "aliases": ["meg"], "rarete": "Légendaire", "role": "Tank"},
    {"name": "Surge", "aliases": ["surge"], "rarete": "Légendaire", "role": "Dégâts Bruts"},
    {"name": "Chester", "aliases": ["chester"], "rarete": "Légendaire", "role": "Dégâts Bruts"},
    {"name": "Cordelius", "aliases": ["cordelius"], "rarete": "Légendaire", "role": "Assassin"},
    {"name": "Kit", "aliases": ["kit"], "rarete": "Légendaire", "role": "Soutien"},
    {"name": "Draco", "aliases": ["draco"], "rarete": "Légendaire", "role": "Tank"},
    {"name": "Lily", "aliases": ["lily"], "rarete": "Légendaire", "role": "Assassin"},
    {"name": "Kenji", "aliases": ["kenji"], "rarete": "Légendaire", "role": "Assassin"},
    {"name": "Pierce", "aliases": ["pierce"], "rarete": "Légendaire", "role": "Tireur d'élite"},
    {"name": "Najia", "aliases": ["najia"], "rarete": "Légendaire", "role": "Dégâts Bruts"},
    # ── Ultra Légendaire ───────────────────────────────────
    {"name": "Sirius", "aliases": ["sirius"], "rarete": "Ultra Légendaire", "role": "Contrôle"},
    {"name": "Kaze", "aliases": ["kaze"], "rarete": "Ultra Légendaire", "role": "Assassin"},
]

COULEURS_RARETE = {
    "Brawler de Départ": 0xB0BEC5,
    "Rare": 0x42A5F5,
    "Super Rare": 0x26C6DA,
    "Épique": 0xAB47BC,
    "Mythique": 0xEF5350,
    "Légendaire": 0xFFD600,
    "Ultra Légendaire": 0xFF6D00,
}

EMOJI_RARETE = {
    "Brawler de Départ": "⚪",
    "Rare": "🔵",
    "Super Rare": "🩵",
    "Épique": "🟣",
    "Mythique": "🔴",
    "Légendaire": "🟡",
    "Ultra Légendaire": "🔶",
}

LABELS_NIVEAUX = [
    "🌫️  Indice 1/4 — Très pixelisé...",
    "🔍  Indice 2/4 — Un peu plus net...",
    "👀  Indice 3/4 — Presque là !",
    "🏆  Indice 4/4 — Image complète !",
]

# ═══════════════════════════════════════════════════════════
#  UTILITAIRES IMAGE
# ═══════════════════════════════════════════════════════════



def nom_en_slug(nom):
    return (
        nom.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("_", "-")
        .replace("&", "and")
        .replace("'", "")
    )


async def telecharger_image(nom):
    slug = nom_en_slug(nom)
    url = f"https://media.brawltime.ninja/brawlers/{slug}/avatar.png"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.read()
                    img = Image.open(io.BytesIO(data)).convert("RGBA")
                    return img.resize((256, 256), Image.LANCZOS)
    except Exception:
        pass
    return None



def pixeliser(img, niveau):
    tailles = {1: 28, 2: 14, 3: 5, 4: 1}
    t = tailles[niveau]
    if t <= 1:
        return img
    w, h = img.size
    small = img.resize((max(1, w // t), max(1, h // t)), Image.NEAREST)
    return small.resize((w, h), Image.NEAREST)


def vers_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def creer_embed(brawler, niveau, gagne=False, perdu=False):
    couleur = COULEURS_RARETE.get(brawler["rarete"], 0xFFD700)
    if gagne:
        titre = "🎉 Bonne réponse !"
        desc = f"C'était bien **{brawler['name']}** !"
        couleur = 0x00FF88
    elif perdu:
        titre = "⏰ Temps écoulé !"
        desc = f"C'était **{brawler['name']}** ! Meilleure chance la prochaine fois."
        couleur = 0xFF4444
    else:
        titre = "🎮 Devine le Brawler !"
        desc = LABELS_NIVEAUX[niveau - 1]

    embed = discord.Embed(title=titre, description=desc, color=couleur)
    embed.set_image(url="attachment://brawler.png")

    if gagne or perdu:
        emoji = EMOJI_RARETE.get(brawler["rarete"], "•")
        embed.add_field(name="Rareté", value=f"{emoji} {brawler['rarete']}", inline=True)
        embed.add_field(name="Rôle", value=brawler["role"], inline=True)

    if not gagne and not perdu:
        embed.set_footer(text="Tape le nom du brawler dans le chat • La partie s'arrête automatiquement")

    return embed


# ═══════════════════════════════════════════════════════════
#  ÉTAT DE JEU
# ═══════════════════════════════════════════════════════════
class PartieEnCours:
    def __init__(self, brawler, image, message):
        self.brawler = brawler
        self.image = image
        self.message = message
        self.niveau = 1
        self.trouve = False
        self.tache = None


parties_actives = {}

# ═══════════════════════════════════════════════════════════
#  BOT
# ═══════════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
arbre = bot.tree


@bot.event
async def on_ready():
    await arbre.sync()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Brawl Stars 🎮 | /brawler"
        )
    )
    print(f"[✓] {bot.user} connecté — Slash commands synchronisées.")
    print(f"[✓] {len(BRAWLERS)} brawlers chargés.")


# ═══════════════════════════════════════════════════════════
#  BOUCLE DE RÉVÉLATION PROGRESSIVE
# ═══════════════════════════════════════════════════════════
async def boucle_revelation(channel_id):
    try:
        for niveau in range(1, 5):
            await asyncio.sleep(20)

            if channel_id not in parties_actives:
                return
            partie = parties_actives[channel_id]
            if partie.trouve:
                return

            partie.niveau = niveau
            fichier = discord.File(
                vers_bytes(pixeliser(partie.image, niveau)),
                filename="brawler.png"
            )
            try:
                await partie.message.edit(
                    embed=creer_embed(partie.brawler, niveau),
                    attachments=[fichier]
                )
            except discord.NotFound:
                parties_actives.pop(channel_id, None)
                return

        # Niveau 4 affiché — on attend encore 20s avant forfait
        await asyncio.sleep(20)
        if channel_id not in parties_actives:
            return
        partie = parties_actives.pop(channel_id)
        if partie.trouve:
            return

        fichier = discord.File(vers_bytes(partie.image), filename="brawler.png")
        try:
            await partie.message.edit(
                embed=creer_embed(partie.brawler, 4, perdu=True),
                attachments=[fichier]
            )
        except discord.NotFound:
            pass

    except asyncio.CancelledError:
        pass


# ═══════════════════════════════════════════════════════════
#  COMMANDES DE BASE
# ═══════════════════════════════════════════════════════════

@arbre.command(name="ping", description="Affiche la latence du bot")
async def ping_cmd(interaction: discord.Interaction):
    lat = round(bot.latency * 1000)
    if lat < 100:
        couleur, statut = 0x00FF88, "🟢 Excellent"
    elif lat < 200:
        couleur, statut = 0xFFD700, "🟡 Correct"
    else:
        couleur, statut = 0xFF4444, "🔴 Élevé"
    embed = discord.Embed(title="🏓 Pong !", color=couleur)
    embed.add_field(name="Latence", value=f"`{lat} ms`", inline=True)
    embed.add_field(name="Statut", value=statut, inline=True)
    embed.set_footer(text="Brawl Zone")
    await interaction.response.send_message(embed=embed)


@arbre.command(name="help", description="Affiche l'aide du bot")
@app_commands.describe(commande="Nom d'une commande spécifique (optionnel)")
async def help_cmd(interaction: discord.Interaction, commande: str = None):

    # Dictionnaire de toutes les commandes
    CMDS = {
        "brawler": {
            "emoji": "🎮",
            "titre": "/brawler",
            "desc": "Lance une partie de devinette de brawler.",
            "details": (
                "Un brawler est choisi aléatoirement et affiché **très pixelisé**.\n"
                "Toutes les **20 secondes**, l'image se précise (4 niveaux).\n"
                "Tape le nom dans le chat pour répondre.\n"
                "La partie s'arrête automatiquement à la fin du timer.\n\n"
                "**Variantes acceptées :** `el primo` → `primo`, accents non obligatoires."
            ),
        },
        "brawler_liste": {
            "emoji": "📋",
            "titre": "/brawler_liste",
            "desc": "Affiche les 101 brawlers disponibles, triés par rareté.",
            "details": "Liste complète des brawlers avec leur rareté et rôle.",
        },
        "draft": {
            "emoji": "🏆",
            "titre": "/draft",
            "desc": "Lance une simulation de draft ranked Brawl Stars.",
            "details": (
                "Une situation de ranked est générée : map, bans, picks ennemis et alliés.\n"
                "Tu as **30 secondes** pour taper le meilleur last pick.\n"
                "Le bot révèle ensuite le meilleur pick, son explication et le top 10 avec winrates.\n"
                "Ton **ELO** monte ou descend selon la qualité de ta réponse."
            ),
        },
        "draft-elo": {
            "emoji": "📊",
            "titre": "/draft-elo",
            "desc": "Affiche ton ELO et ton rang actuel en Draft Ranked.",
            "details": "Montre ton rang, ton ELO, ta position dans le classement serveur et le barème de gains/pertes.",
        },
        "draft-classement": {
            "emoji": "🏅",
            "titre": "/draft-classement",
            "desc": "Affiche le top 10 des joueurs en Draft Ranked sur le serveur.",
            "details": "Classement par ELO avec rang affiché pour chaque joueur.",
        },
        "ping": {
            "emoji": "🏓",
            "titre": "/ping",
            "desc": "Affiche la latence du bot.",
            "details": "Indique si la connexion est 🟢 Excellente, 🟡 Correcte ou 🔴 Élevée.",
        },
        "help": {
            "emoji": "❓",
            "titre": "/help [commande]",
            "desc": "Affiche l'aide générale ou le détail d'une commande.",
            "details": "Sans argument → liste toutes les commandes.\nAvec un nom → détail de cette commande spécifique.",
        },
        "info-serveur": {
            "emoji": "📋",
            "titre": "/info-serveur",
            "desc": "Affiche les informations du serveur.",
            "details": "Propriétaire, nombre de membres, salons, rôles, niveau de vérification et date de création.",
        },
        "info-user": {
            "emoji": "👤",
            "titre": "/info-user [membre]",
            "desc": "Affiche les informations d'un membre.",
            "details": "Sans argument → tes propres infos.\nAvec mention → infos du membre ciblé.",
        },
        "avatar": {
            "emoji": "🖼️",
            "titre": "/avatar [membre]",
            "desc": "Affiche l'avatar d'un membre en grand.",
            "details": "Sans argument → ton avatar.\nAvec mention → avatar du membre ciblé.",
        },
    }

    # ── Aide spécifique ──────────────────────────────────────
    if commande:
        cle = commande.lower().replace("/", "").replace("-", "-")
        info = CMDS.get(cle)
        if not info:
            await interaction.response.send_message(
                f"❌ Commande `/{commande}` introuvable. Utilise `/help` pour voir toutes les commandes.",
                ephemeral=True
            )
            return
        embed = discord.Embed(
            title=f"{info['emoji']} {info['titre']}",
            description=info["desc"],
            color=0xFFD700,
        )
        embed.add_field(name="📖 Détails", value=info["details"], inline=False)
        embed.set_footer(text="Brawl Zone • /help pour la liste complète")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # ── Aide générale ────────────────────────────────────────
    embed = discord.Embed(
        title="❓ Aide — Brawl Zone",
        description=(
            "Bienvenue sur **Brawl Zone**, le bot de mini-jeux Brawl Stars !\n"
            "💡 Utilise `/help <commande>` pour le détail d'une commande."
        ),
        color=0xFFD700,
    )
    embed.add_field(
        name="🎮 Mini-jeux",
        value=(
            "`/brawler` — Devine le brawler caché !\n"
            "`/brawler_liste` — Liste des 101 brawlers\n"
            "`/draft` — Entraîne-toi au draft ranked !\n"
            "`/draft-elo` — Ton ELO et ton rang\n"
            "`/draft-classement` — Top joueurs du serveur"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛠️ Utilitaires",
        value=(
            "`/ping` — Latence du bot\n"
            "`/help` — Cette aide\n"
            "`/info-serveur` — Infos sur le serveur\n"
            "`/info-user` — Infos sur un membre\n"
            "`/avatar` — Avatar d'un membre"
        ),
        inline=False,
    )
    embed.set_footer(text="Brawl Zone • 101 brawlers disponibles")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@arbre.command(name="info-serveur", description="Affiche les informations du serveur")
async def info_serveur_cmd(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(
        title=f"📋 {g.name}",
        description=g.description or "Aucune description.",
        color=0x4FC3F7,
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="👑 Propriétaire", value=str(g.owner), inline=True)
    embed.add_field(name="👥 Membres", value=str(g.member_count), inline=True)
    embed.add_field(name="📁 Salons", value=str(len(g.channels)), inline=True)
    embed.add_field(name="🎭 Rôles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="🔒 Vérification", value=str(g.verification_level).title(), inline=True)
    embed.add_field(name="📅 Créé le", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
    embed.set_footer(text="Brawl Zone")
    await interaction.response.send_message(embed=embed)


@arbre.command(name="info-user", description="Affiche les informations d'un membre")
@app_commands.describe(membre="Le membre à inspecter (optionnel)")
async def info_user_cmd(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    roles = [r.mention for r in m.roles if r.name != "@everyone"]
    embed = discord.Embed(
        title=f"👤 {m.display_name}",
        description=f"**Tag :** {m}\n**ID :** `{m.id}`",
        color=0x4FC3F7,
    )
    embed.set_thumbnail(url=m.display_avatar.url)
    embed.add_field(name="📅 Compte créé", value=f"<t:{int(m.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="📥 A rejoint le", value=f"<t:{int(m.joined_at.timestamp())}:D>", inline=True)
    embed.add_field(name="🎭 Rôles", value=" ".join(roles) if roles else "Aucun", inline=False)
    embed.set_footer(text="Brawl Zone")
    await interaction.response.send_message(embed=embed)


@arbre.command(name="avatar", description="Affiche l'avatar d'un membre")
@app_commands.describe(membre="Le membre (optionnel)")
async def avatar_cmd(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    embed = discord.Embed(
        title=f"🖼️ Avatar de {m.display_name}",
        description=f"[Ouvrir en plein écran]({m.display_avatar.url})",
        color=0x4FC3F7,
    )
    embed.set_image(url=m.display_avatar.url)
    embed.set_footer(text="Brawl Zone")
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════
#  SLASH COMMANDS — BRAWLER
# ═══════════════════════════════════════════════════════════
@arbre.command(name="brawler", description="Lance une partie : devine le brawler caché !")
async def slash_brawler(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id in parties_actives:
        await interaction.response.send_message(
            "❌ Une partie est déjà en cours dans ce salon ! Attends la fin du timer.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    choix = random.choice(BRAWLERS)
    image = await telecharger_image(choix["name"])

    if image is None:
        await interaction.followup.send(
            f"❌ Impossible de charger l'image de **{choix['name']}**, réessaie !",
            ephemeral=True
        )
        return

    fichier = discord.File(vers_bytes(pixeliser(image, 1)), filename="brawler.png")
    msg = await interaction.followup.send(embed=creer_embed(choix, 1), file=fichier)

    partie = PartieEnCours(choix, image, msg)
    parties_actives[channel_id] = partie
    partie.tache = asyncio.create_task(boucle_revelation(channel_id))


@arbre.command(name="brawler_liste", description="Affiche tous les brawlers disponibles dans le jeu.")
async def slash_brawler_liste(interaction: discord.Interaction):
    par_rarete = {}
    for b in BRAWLERS:
        par_rarete.setdefault(b["rarete"], []).append(b["name"])

    embed = discord.Embed(
        title="📋 Brawlers disponibles — Brawl Zone",
        description=f"**{len(BRAWLERS)} brawlers** dans la base de données",
        color=0xFFD700,
    )
    ordre = [
        "Brawler de Départ", "Rare", "Super Rare",
        "Épique", "Mythique", "Légendaire", "Ultra Légendaire",
    ]
    for rarete in ordre:
        if rarete in par_rarete:
            noms = ", ".join(sorted(par_rarete[rarete]))
            emoji = EMOJI_RARETE.get(rarete, "•")
            embed.add_field(
                name=f"{emoji} {rarete} ({len(par_rarete[rarete])})",
                value=noms,
                inline=False,
            )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════
#  ÉCOUTE DES RÉPONSES DANS LE CHAT
# ═══════════════════════════════════════════════════════════
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    channel_id = message.channel.id
    if channel_id not in parties_actives:
        await bot.process_commands(message)
        return

    partie = parties_actives[channel_id]
    if partie.trouve:
        await bot.process_commands(message)
        return

    reponse = message.content.strip().lower()
    if reponse in partie.brawler["aliases"]:
        partie.trouve = True
        if partie.tache:
            partie.tache.cancel()
        parties_actives.pop(channel_id)

        fichier = discord.File(vers_bytes(partie.image), filename="brawler.png")
        embed = creer_embed(partie.brawler, partie.niveau, gagne=True)
        embed.description += (
            f"\n\n🥇 Trouvé par {message.author.mention} "
            f"à l'indice **{partie.niveau}/4** !"
        )

        try:
            await partie.message.edit(embed=embed, attachments=[fichier])
        except discord.NotFound:
            await message.channel.send(embed=embed, file=fichier)
        try:
            await message.add_reaction("🎉")
        except Exception:
            pass

    await bot.process_commands(message)



# ═══════════════════════════════════════════════════════════
#  MINI-JEU : DRAFT RANKED
# ═══════════════════════════════════════════════════════════

# Système ELO par serveur/utilisateur
draft_elo: dict[int, dict[int, int]] = {}
active_draft_games: dict[int, bool] = {}

RANGS_ELO = [
    (0,    "🥉 Bronze I"),
    (100,  "🥉 Bronze II"),
    (200,  "🥉 Bronze III"),
    (300,  "🥈 Silver I"),
    (400,  "🥈 Silver II"),
    (500,  "🥈 Silver III"),
    (600,  "🏅 Gold I"),
    (700,  "🏅 Gold II"),
    (800,  "🏅 Gold III"),
    (900,  "💎 Diamond I"),
    (1000, "💎 Diamond II"),
    (1100, "💎 Diamond III"),
    (1200, "💜 Mythic I"),
    (1300, "💜 Mythic II"),
    (1400, "💜 Mythic III"),
    (1500, "🌟 Legendary I"),
    (1600, "🌟 Legendary II"),
    (1700, "🌟 Legendary III"),
    (1800, "👑 Masters"),
]


def get_rang(elo: int) -> str:
    rang = RANGS_ELO[0][1]
    for seuil, nom in RANGS_ELO:
        if elo >= seuil:
            rang = nom
    return rang


def get_elo(guild_id: int, user_id: int) -> int:
    return draft_elo.get(guild_id, {}).get(user_id, 0)


def set_elo(guild_id: int, user_id: int, valeur: int):
    if guild_id not in draft_elo:
        draft_elo[guild_id] = {}
    draft_elo[guild_id][user_id] = max(0, valeur)


SCENARIOS = [
    {
        "map": "Dry Season", "mode": "Gem Grab", "emoji_mode": "💎",
        "img": "https://media.brawltime.ninja/maps/dry-season/map.png",
        "enemy": ["Leon", "Crow", "Piper"],
        "ally": ["Nani", "Bo"],
        "bans": ["Spike", "Sandy", "Tara", "Bea", "Jessie", "Gene"],
        "top10": [
            ("Max", 61.2), ("Byron", 58.7), ("Poco", 57.4),
            ("Gale", 55.1), ("Frank", 54.8), ("Bull", 53.9),
            ("8-Bit", 53.2), ("Pam", 52.7), ("Rosa", 51.8), ("Darryl", 51.3),
        ],
        "best": "Max",
        "explication": (
            "**Max** est le meilleur pick ici pour plusieurs raisons :\n"
            "• Son super booste toute l'équipe (Nani + Bo), crucial sur une map ouverte\n"
            "• Elle contre Leon et Crow grâce à sa mobilité et son aura de vitesse\n"
            "• Piper est peu dangereuse si Max se déplace constamment\n"
            "• Elle sécurise les gemmes et roam facilement sur Dry Season"
        ),
    },
    {
        "map": "Hard Rock Mine", "mode": "Gem Grab", "emoji_mode": "💎",
        "img": "https://media.brawltime.ninja/maps/hard-rock-mine/map.png",
        "enemy": ["Spike", "Poco", "Frank"],
        "ally": ["8-Bit", "Pam"],
        "bans": ["Sandy", "Gene", "Tara", "Max", "Byron", "Squeak"],
        "top10": [
            ("Gale", 62.3), ("Emz", 60.1), ("Jessie", 58.4),
            ("Bo", 57.2), ("Tick", 55.8), ("Nani", 54.6),
            ("Rico", 53.9), ("Carl", 53.1), ("Dynamike", 52.7), ("Brock", 52.0),
        ],
        "best": "Gale",
        "explication": (
            "**Gale** est parfait sur Hard Rock Mine :\n"
            "• Son super repousse Frank hors de la mine, empêchant les gemmes\n"
            "• Il counter Poco en zone centrale grâce à son push\n"
            "• Synergy avec 8-Bit (range + zone control)\n"
            "• Spike est déjà ennemi donc Gale peut bloquer ses attaques en piquant"
        ),
    },
    {
        "map": "Kaboom Canyon", "mode": "Brawl Ball", "emoji_mode": "⚽",
        "img": "https://media.brawltime.ninja/maps/kaboom-canyon/map.png",
        "enemy": ["El Primo", "Bull", "Frank"],
        "ally": ["Bibi", "Stu"],
        "bans": ["Leon", "Mortis", "Edgar", "Fang", "Buzz", "Sam"],
        "top10": [
            ("Rosa", 63.5), ("Darryl", 61.2), ("Jacky", 59.8),
            ("Carl", 58.3), ("Surge", 57.1), ("Rico", 56.4),
            ("Brock", 55.9), ("Dynamike", 55.2), ("Tick", 54.7), ("Grom", 53.8),
        ],
        "best": "Rosa",
        "explication": (
            "**Rosa** est le meilleur last pick sur Kaboom Canyon :\n"
            "• Son super la rend invincible 3 secondes — parfait face à El Primo + Bull + Frank\n"
            "• Elle peut porter le ballon seule grâce à sa résistance\n"
            "• Synergy avec Bibi (combo mêlée robuste) et Stu (vitesse + fuite)\n"
            "• Les couloirs étroits avantagent les tanks, et Rosa est la meilleure option disponible"
        ),
    },
    {
        "map": "Super Beach", "mode": "Brawl Ball", "emoji_mode": "⚽",
        "img": "https://media.brawltime.ninja/maps/super-beach/map.png",
        "enemy": ["Piper", "Brock", "Nani"],
        "ally": ["Leon", "Mortis"],
        "bans": ["Sandy", "Spike", "Crow", "Carl", "Rico", "Surge"],
        "top10": [
            ("Darryl", 64.1), ("Bull", 62.7), ("El Primo", 61.3),
            ("Rosa", 59.8), ("Bibi", 58.4), ("Jacky", 57.6),
            ("Frank", 56.9), ("Buzz", 55.3), ("Fang", 54.8), ("Stu", 53.7),
        ],
        "best": "Darryl",
        "explication": (
            "**Darryl** est idéal pour compléter cette compo :\n"
            "• Son roll permet de passer sous les tirs de Piper, Brock et Nani\n"
            "• Combo parfait avec Leon et Mortis : trois assassins rapides\n"
            "• Super chargeable rapidement pour enchaîner les attaques au but\n"
            "• Super Beach est une map ouverte — Darryl peut rouler en diagonale et surprendre"
        ),
    },
    {
        "map": "Shooting Star", "mode": "Bounty", "emoji_mode": "⭐",
        "img": "https://media.brawltime.ninja/maps/shooting-star/map.png",
        "enemy": ["Piper", "Bea", "Belle"],
        "ally": ["Leon", "Crow"],
        "bans": ["Spike", "Sandy", "Bo", "Nani", "Janet", "Angelo"],
        "top10": [
            ("Carl", 63.8), ("Gale", 61.5), ("Emz", 60.2),
            ("Dynamike", 58.9), ("Tick", 57.4), ("Brock", 56.8),
            ("8-Bit", 55.3), ("Rico", 54.7), ("Stu", 53.9), ("Edgar", 52.6),
        ],
        "best": "Carl",
        "explication": (
            "**Carl** est le meilleur last pick en Bounty ici :\n"
            "• Son attaque perce et touche Piper/Bea/Belle derrière les buissons\n"
            "• Il résiste mieux que la plupart face aux snipers avec ses 4400 PV\n"
            "• Combo avec Leon + Crow : Carl occupe le centre pendant qu'ils flanquent\n"
            "• Son super lui permet de fuir quand il est ciblé, préservant l'étoile bonus"
        ),
    },
    {
        "map": "Snake Prairie", "mode": "Bounty", "emoji_mode": "⭐",
        "img": "https://media.brawltime.ninja/maps/snake-prairie/map.png",
        "enemy": ["Crow", "Leon", "Mortis"],
        "ally": ["Spike", "Sandy"],
        "bans": ["Tara", "Gene", "Max", "Poco", "Byron", "Gale"],
        "top10": [
            ("Bo", 64.5), ("Tick", 62.1), ("Dynamike", 60.8),
            ("Sprout", 59.3), ("Jessie", 57.9), ("Penny", 56.4),
            ("Bea", 55.8), ("Piper", 55.1), ("Nani", 54.3), ("8-Bit", 53.6),
        ],
        "best": "Bo",
        "explication": (
            "**Bo** est le choix parfait sur Snake Prairie :\n"
            "• Ses mines cachées dans les buissons contrent Leon/Crow/Mortis qui s'en approchent\n"
            "• Il révèle les ennemis cachés avec son super, parfait contre Leon\n"
            "• Synergy Spike + Sandy + Bo : zone control totale du terrain\n"
            "• Snake Prairie a beaucoup de buissons — les mines de Bo sont dévastatrices"
        ),
    },
    {
        "map": "Belle's Rock", "mode": "Hot Zone", "emoji_mode": "🔥",
        "img": "https://media.brawltime.ninja/maps/belles-rock/map.png",
        "enemy": ["Emz", "Gale", "Frank"],
        "ally": ["Max", "Poco"],
        "bans": ["Sandy", "Tara", "Spike", "Gene", "Byron", "Squeak"],
        "top10": [
            ("Pam", 62.9), ("Rosa", 60.4), ("Jacky", 58.7),
            ("Bull", 57.3), ("Darryl", 56.1), ("Bibi", 55.4),
            ("Ash", 54.8), ("Sam", 53.7), ("Buzz", 52.9), ("Buster", 52.1),
        ],
        "best": "Pam",
        "explication": (
            "**Pam** est le meilleur last pick sur Belle's Rock :\n"
            "• Sa tourelle soigne Max et Poco en permanence sur la zone à tenir\n"
            "• Elle résiste aux dégâts de zone d'Emz et Gale grâce à ses 7200 PV\n"
            "• Son attaque à dispersion nettoie la zone rapidement\n"
            "• La synergie Pam + Poco + Max crée une équipe quasi inarrêtable sur zone"
        ),
    },
    {
        "map": "Open Zone", "mode": "Hot Zone", "emoji_mode": "🔥",
        "img": "https://media.brawltime.ninja/maps/open-zone/map.png",
        "enemy": ["Sandy", "Spike", "Amber"],
        "ally": ["Leon", "Crow"],
        "bans": ["Tara", "Gene", "Max", "Pam", "Poco", "Gale"],
        "top10": [
            ("Emz", 63.2), ("Squeak", 61.8), ("Tick", 60.5),
            ("Dynamike", 58.9), ("Sprout", 57.4), ("Bo", 56.8),
            ("Penny", 55.3), ("Jessie", 54.6), ("Brock", 53.9), ("Rico", 52.7),
        ],
        "best": "Emz",
        "explication": (
            "**Emz** est excellente sur Open Zone contre cette compo :\n"
            "• Son attaque zone ralentit Sandy/Spike/Amber qui veulent tenir la zone\n"
            "• Super instantané qui couvre toute une zone et contre le sommeil de Sandy\n"
            "• Synergy Leon + Crow + Emz : les trois contrôlent le terrain\n"
            "• Elle peut charger son super très vite sur la zone centrale ouverte"
        ),
    },
    {
        "map": "Parallel Plays", "mode": "Heist", "emoji_mode": "💰",
        "img": "https://media.brawltime.ninja/maps/parallel-plays/map.png",
        "enemy": ["Brock", "Piper", "Dynamike"],
        "ally": ["Bull", "El Primo"],
        "bans": ["Spike", "Leon", "Crow", "Sandy", "Amber", "Surge"],
        "top10": [
            ("Darryl", 64.8), ("Jacky", 62.3), ("Rosa", 60.9),
            ("Frank", 59.4), ("Ash", 58.1), ("Sam", 57.6),
            ("Bibi", 56.2), ("Buzz", 55.8), ("Edgar", 54.3), ("Mortis", 53.7),
        ],
        "best": "Darryl",
        "explication": (
            "**Darryl** est parfait pour cette compo Heist :\n"
            "• Son roll lui permet de traverser le terrain et atteindre le coffre rapidement\n"
            "• Il résiste aux snipers (Brock/Piper) grâce à sa mobilité\n"
            "• Combo dévastateur avec Bull + El Primo : trois tanks sur le coffre\n"
            "• Sur Parallel Plays, les couloirs avantagent les rush — Darryl excelle"
        ),
    },
    {
        "map": "Safe Zone", "mode": "Heist", "emoji_mode": "💰",
        "img": "https://media.brawltime.ninja/maps/safe-zone/map.png",
        "enemy": ["Sprout", "Penny", "Jessie"],
        "ally": ["Surge", "Brock"],
        "bans": ["Leon", "Crow", "Amber", "Sandy", "Bull", "Darryl"],
        "top10": [
            ("Dynamike", 63.1), ("Tick", 61.4), ("Grom", 60.2),
            ("Barley", 58.9), ("Emz", 57.3), ("Rico", 56.1),
            ("8-Bit", 55.4), ("Nani", 54.8), ("Carl", 53.9), ("Piper", 52.7),
        ],
        "best": "Dynamike",
        "explication": (
            "**Dynamike** est le meilleur last pick ici :\n"
            "• Il détruit les murs de Sprout pour ouvrir le chemin au coffre\n"
            "• Ses bombes passent par-dessus les tourelles de Penny et Jessie\n"
            "• Combo avec Surge + Brock : triple zone de dégâts à distance\n"
            "• Son super hyper bombe peut éliminer plusieurs tourelles en une fois"
        ),
    },
    {
        "map": "Flaring Phoenix", "mode": "Knockout", "emoji_mode": "💀",
        "img": "https://media.brawltime.ninja/maps/flaring-phoenix/map.png",
        "enemy": ["Leon", "Buzz", "Edgar"],
        "ally": ["Piper", "Brock"],
        "bans": ["Crow", "Sandy", "Spike", "Mortis", "Fang", "Sam"],
        "top10": [
            ("Belle", 65.3), ("Nani", 63.8), ("Bo", 62.1),
            ("Bea", 60.7), ("Janet", 59.4), ("Angelo", 58.8),
            ("Carl", 57.3), ("Gale", 56.9), ("Rico", 55.4), ("8-Bit", 54.2),
        ],
        "best": "Belle",
        "explication": (
            "**Belle** est le meilleur last pick en Knockout :\n"
            "• Son super marque les ennemis pour +30% dégâts — parfait avec Piper + Brock\n"
            "• Elle contre Leon avec ses ricochets qui révèlent sa position\n"
            "• Buzz et Edgar sont trop mobiles pour Piper seule — Belle les ralentit\n"
            "• Triple sniper (Piper + Brock + Belle) = domination totale à distance"
        ),
    },
    {
        "map": "New Horizons", "mode": "Knockout", "emoji_mode": "💀",
        "img": "https://media.brawltime.ninja/maps/new-horizons/map.png",
        "enemy": ["Piper", "Bea", "Nani"],
        "ally": ["Edgar", "Crow"],
        "bans": ["Leon", "Sandy", "Buzz", "Sam", "Fang", "Mortis"],
        "top10": [
            ("Darryl", 64.7), ("Bull", 62.9), ("El Primo", 61.4),
            ("Buzz", 60.1), ("Stu", 58.6), ("Carl", 57.3),
            ("Jacky", 56.8), ("Rosa", 55.4), ("Bibi", 54.1), ("Frank", 52.9),
        ],
        "best": "Darryl",
        "explication": (
            "**Darryl** est idéal pour counter cette compo sniper :\n"
            "• Son roll peut traverser toute la map et one-shot Piper/Bea/Nani\n"
            "• Synergy Edgar + Crow + Darryl : trois assassins rapides\n"
            "• Avec deux assassins déjà dans la compo, les snipers ennemis sont en danger\n"
            "• Son bouclier naturel lui permet de survivre au burst initial de Nani"
        ),
    },
    {
        "map": "Double Swoosh", "mode": "Brawl Ball", "emoji_mode": "⚽",
        "img": "https://media.brawltime.ninja/maps/double-swoosh/map.png",
        "enemy": ["Sandy", "Emz", "Gale"],
        "ally": ["Frank", "Jacky"],
        "bans": ["Leon", "Mortis", "Buzz", "Edgar", "Sam", "Surge"],
        "top10": [
            ("Bibi", 63.4), ("El Primo", 61.9), ("Bull", 60.3),
            ("Darryl", 58.7), ("Rosa", 57.4), ("Ash", 56.1),
            ("Buster", 55.8), ("Stu", 54.3), ("Carl", 53.7), ("Rico", 52.1),
        ],
        "best": "Bibi",
        "explication": (
            "**Bibi** complète parfaitement cette compo :\n"
            "• Son bouclier personnel la protège du contrôle de masse de Sandy/Emz/Gale\n"
            "• Elle peut repousser les ennemis avec son swing pour dégager la voie au but\n"
            "• Combo Frank + Jacky + Bibi = trois tanks durs à arrêter\n"
            "• Son super balle rebondissante traverse les zones de contrôle ennemies"
        ),
    },
    {
        "map": "Minecart Madness", "mode": "Gem Grab", "emoji_mode": "💎",
        "img": "https://media.brawltime.ninja/maps/minecart-madness/map.png",
        "enemy": ["Tara", "Gene", "Poco"],
        "ally": ["Spike", "Emz"],
        "bans": ["Sandy", "Max", "Byron", "Squeak", "Gale", "Bo"],
        "top10": [
            ("Leon", 64.2), ("Crow", 62.7), ("Mortis", 61.1),
            ("Buzz", 59.8), ("Fang", 58.4), ("Edgar", 57.6),
            ("Sam", 56.3), ("Stu", 55.7), ("Carl", 54.1), ("Darryl", 52.9),
        ],
        "best": "Leon",
        "explication": (
            "**Leon** est excellent ici pour counter Tara + Gene :\n"
            "• Invisible, il peut voler les gemmes au gemeur de Tara sans risque\n"
            "• Gene ne peut pas l'attraper facilement si Leon est camouflé\n"
            "• Il contre Poco en l'éliminant rapidement avant les soins\n"
            "• Synergy Spike + Emz + Leon : dégâts zone + assassin invisible"
        ),
    },
    {
        "map": "Layer Cake", "mode": "Hot Zone", "emoji_mode": "🔥",
        "img": "https://media.brawltime.ninja/maps/layer-cake/map.png",
        "enemy": ["Bull", "Rosa", "Jacky"],
        "ally": ["Piper", "Belle"],
        "bans": ["Sandy", "Tara", "Gene", "Max", "Poco", "Emz"],
        "top10": [
            ("Brock", 63.9), ("Dynamike", 62.4), ("Tick", 60.8),
            ("Sprout", 59.3), ("Grom", 58.1), ("Penny", 56.7),
            ("Nani", 55.4), ("Angelo", 54.8), ("Gale", 53.2), ("Bo", 52.6),
        ],
        "best": "Brock",
        "explication": (
            "**Brock** complète parfaitement ce triple sniper :\n"
            "• Ses fusées détruisent les murs pour empêcher Bull/Rosa/Jacky de se couvrir\n"
            "• Il peut tenir la zone à distance sans jamais s'approcher des tanks\n"
            "• Triple longue portée (Piper + Belle + Brock) = les tanks ne peuvent pas avancer\n"
            "• Son super Rocktoberfest nettoie une zone entière quand les tanks s'amassent"
        ),
    },
    {
        "map": "Center Stage", "mode": "Hot Zone", "emoji_mode": "🔥",
        "img": "https://media.brawltime.ninja/maps/center-stage/map.png",
        "enemy": ["Max", "Byron", "Poco"],
        "ally": ["Emz", "Squeak"],
        "bans": ["Sandy", "Tara", "Gene", "Spike", "Gale", "Pam"],
        "top10": [
            ("Frank", 62.8), ("Rosa", 61.3), ("Jacky", 59.7),
            ("Bull", 58.4), ("Ash", 57.1), ("Darryl", 56.3),
            ("Buster", 55.8), ("Sam", 54.2), ("Buzz", 53.6), ("El Primo", 52.9),
        ],
        "best": "Frank",
        "explication": (
            "**Frank** est le meilleur last pick ici :\n"
            "• Son super étourdit toute l'équipe Max/Byron/Poco groupée sur la zone\n"
            "• Il résiste aux dégâts continus de ce trio grâce à ses 10200 PV\n"
            "• Synergy Emz + Squeak + Frank : zone control + tank indestructible\n"
            "• Une fois étourdi, Max ne peut plus booster l'équipe ennemie"
        ),
    },
    {
        "map": "Goldarm Gulch", "mode": "Heist", "emoji_mode": "💰",
        "img": "https://media.brawltime.ninja/maps/goldarm-gulch/map.png",
        "enemy": ["Jacky", "Rosa", "Darryl"],
        "ally": ["Brock", "Dynamike"],
        "bans": ["Leon", "Crow", "Amber", "Sandy", "Bull", "El Primo"],
        "top10": [
            ("Piper", 63.7), ("Nani", 62.1), ("Belle", 60.8),
            ("Angelo", 59.4), ("Janet", 58.2), ("Grom", 57.6),
            ("Tick", 56.3), ("Penny", 55.1), ("Sprout", 53.8), ("8-Bit", 52.4),
        ],
        "best": "Piper",
        "explication": (
            "**Piper** est le meilleur last pick sur Goldarm Gulch :\n"
            "• Elle peut sniper Jacky/Rosa/Darryl dès qu'ils sortent de leur base\n"
            "• Triple artillerie (Brock + Dynamike + Piper) = le coffre ennemi s'effondre\n"
            "• Son super lui permet de fuir les charges de Darryl\n"
            "• Les longues lignes droites de Goldarm Gulch maximisent sa portée"
        ),
    },
    {
        "map": "Dueling Beetles", "mode": "Bounty", "emoji_mode": "⭐",
        "img": "https://media.brawltime.ninja/maps/dueling-beetles/map.png",
        "enemy": ["Mortis", "Leon", "Buzz"],
        "ally": ["Bo", "Tick"],
        "bans": ["Sandy", "Spike", "Crow", "Emz", "Gale", "Carl"],
        "top10": [
            ("Piper", 64.3), ("Belle", 62.8), ("Nani", 61.4),
            ("Janet", 60.1), ("Angelo", 58.7), ("Brock", 57.3),
            ("Bea", 56.8), ("8-Bit", 55.2), ("Rico", 54.6), ("Dynamike", 53.1),
        ],
        "best": "Piper",
        "explication": (
            "**Piper** est parfaite pour counter Mortis + Leon + Buzz :\n"
            "• Elle peut éliminer Leon/Buzz en 2 tirs avant qu'ils approchent\n"
            "• Mortis ne peut pas la rush facilement avec les mines de Bo partout\n"
            "• Synergy Bo + Tick + Piper : zone control + sniper = triple protection\n"
            "• Sur Dueling Beetles, les buissons de Bo bloquent les approches des assassins"
        ),
    },
    {
        "map": "Feast or Famine", "mode": "Bounty", "emoji_mode": "⭐",
        "img": "https://media.brawltime.ninja/maps/feast-or-famine/map.png",
        "enemy": ["Dynamike", "Tick", "Sprout"],
        "ally": ["Mortis", "Crow"],
        "bans": ["Sandy", "Spike", "Bo", "Leon", "Piper", "Brock"],
        "top10": [
            ("Buzz", 63.9), ("Edgar", 62.4), ("Fang", 61.1),
            ("Sam", 59.7), ("Stu", 58.3), ("Darryl", 57.6),
            ("El Primo", 56.2), ("Bull", 54.8), ("Carl", 53.4), ("Bibi", 52.1),
        ],
        "best": "Buzz",
        "explication": (
            "**Buzz** est le meilleur last pick ici :\n"
            "• Son super instantané lui permet de plonger sur Dynamike/Tick/Sprout sans risque\n"
            "• Il charge son super très vite en attaquant les bombes de Tick\n"
            "• Synergy Mortis + Crow + Buzz : trois assassins qui éliminent les lanceurs\n"
            "• Sur Feast or Famine, les ressources centrales attirent les ennemis — Buzz punit ça"
        ),
    },
    {
        "map": "Chill Cave", "mode": "Gem Grab", "emoji_mode": "💎",
        "img": "https://media.brawltime.ninja/maps/chill-cave/map.png",
        "enemy": ["Pam", "Frank", "Rosa"],
        "ally": ["Byron", "Squeak"],
        "bans": ["Sandy", "Tara", "Gene", "Max", "Poco", "Gale"],
        "top10": [
            ("Spike", 65.1), ("Amber", 63.6), ("Emz", 62.2),
            ("Dynamike", 60.8), ("Tick", 59.3), ("Sprout", 58.1),
            ("Brock", 56.7), ("Grom", 55.4), ("Penny", 54.2), ("Bo", 52.8),
        ],
        "best": "Spike",
        "explication": (
            "**Spike** est imbattable sur Chill Cave contre ce trio :\n"
            "• Ses épines ralentissent Pam/Frank/Rosa qui veulent tenir la mine\n"
            "• Il empoisonne la zone, rendant impossible de garder les gemmes\n"
            "• Synergy Byron + Squeak + Spike : dégâts persistants + zone control\n"
            "• Son super crée une barrière d'épines qui bloque les tanks de la mine"
        ),
    },
]


def normaliser_draft(texte: str) -> str:
    texte = texte.lower().strip()
    texte = "".join(c for c in texte if c.isalnum() or c in " -.")
    return texte.strip()


def trouver_brawler_draft(reponse: str, scenario: dict) -> int:
    """Retourne la position dans le top10 (0-indexé), ou -1 si absent."""
    rep = normaliser_draft(reponse)
    for i, (nom, _) in enumerate(scenario["top10"]):
        if normaliser_draft(nom) == rep:
            return i
        # Alias simples
        if rep in normaliser_draft(nom) or normaliser_draft(nom) in rep:
            return i
    return -1


def barre_winrate(wr: float) -> str:
    """Génère une barre visuelle pour le winrate."""
    filled = round((wr - 50) / 20 * 8)
    filled = max(0, min(8, filled))
    return "█" * filled + "░" * (8 - filled)


def embed_scenario(scenario: dict, user: discord.Member, elo: int) -> discord.Embed:
    """Crée l'embed de la situation de draft."""
    embed = discord.Embed(
        title=f"🏆 Draft Ranked — {scenario['map']}",
        description=(
            f"**Mode :** {scenario['emoji_mode']} {scenario['mode']}\n"
            f"**Ton rang :** {get_rang(elo)} `({elo} ELO)`\n\n"
            "Quel est le **meilleur last pick** pour ton équipe ?\n"
            "Tape le nom dans le chat. Tu as **30 secondes** !"
        ),
        color=0xFFD700,
    )
    embed.add_field(
        name="🔴 Équipe ennemie",
        value=" • ".join(f"`{b}`" for b in scenario["enemy"]),
        inline=False,
    )
    ally_str = " • ".join(f"`{b}`" for b in scenario["ally"]) + " • `❓ Last pick`"
    embed.add_field(name="🔵 Ton équipe", value=ally_str, inline=False)
    embed.add_field(
        name="🚫 Bans",
        value=" • ".join(f"~~{b}~~" for b in scenario["bans"]),
        inline=False,
    )
    embed.set_footer(
        text=f"Brawl Zone • Draft Ranked | Bonne chance {user.display_name} !"
    )
    return embed


def embed_resultat(scenario: dict, reponse: str, position: int, delta_elo: int, nouvel_elo: int) -> discord.Embed:
    """Crée l'embed du résultat après la réponse."""
    best = scenario["top10"][0][0]

    if position == 0:
        couleur = 0x00FF88
        titre = "🎯 Pick parfait !"
        desc = f"Tu as trouvé le meilleur pick : **{best}** ! `+{delta_elo} ELO`"
    elif 0 < position <= 2:
        couleur = 0x4FC3F7
        titre = f"✅ Bon pick ! (Top {position + 1})"
        desc = f"Tu as joué **{reponse}** (#{position + 1}) ! Le meilleur était **{best}**. `+{delta_elo} ELO`"
    elif 0 < position <= 4:
        couleur = 0xFFD700
        titre = f"🟡 Pick correct (Top {position + 1})"
        desc = f"Tu as joué **{reponse}** (#{position + 1}). Le meilleur était **{best}**. `+{delta_elo} ELO`"
    elif position > 4:
        couleur = 0xFF7043
        titre = f"🟠 Pick discutable (Top {position + 1})"
        desc = f"Tu as joué **{reponse}** (#{position + 1}). Le meilleur était **{best}**. `{delta_elo} ELO`"
    elif position == -2:
        couleur = 0xFF4444
        titre = "⏰ Temps écoulé !"
        desc = f"Le meilleur pick était **{best}**. `{delta_elo} ELO`"
    else:
        couleur = 0xFF4444
        titre = "❌ Pick non reconnu"
        desc = f"**{reponse}** n'est pas dans le top 10. Le meilleur était **{best}**. `{delta_elo} ELO`"

    embed = discord.Embed(title=titre, description=desc, color=couleur)

    # Explication
    embed.add_field(
        name=f"💡 Pourquoi {best} ?",
        value=scenario["explication"],
        inline=False,
    )

    # Top 10
    top_lines = []
    for i, (nom, wr) in enumerate(scenario["top10"]):
        medaille = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`#{i + 1}`"
        barre = barre_winrate(wr)
        top_lines.append(f"{medaille} **{nom}** `{barre}` {wr}%")
    embed.add_field(
        name="📊 Top 10 — Winrates (Power League)",
        value="\n".join(top_lines),
        inline=False,
    )

    embed.add_field(
        name="📈 Ton ELO",
        value=f"{get_rang(nouvel_elo)} — `{nouvel_elo} ELO`",
        inline=False,
    )
    embed.set_footer(text="Brawl Zone • Draft Ranked")
    return embed


@arbre.command(name="draft", description="Entraîne-toi au draft ranked Brawl Stars !")
async def draft_cmd(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if active_draft_games.get(channel_id):
        await interaction.response.send_message(
            "❌ Une partie Draft est déjà en cours dans ce salon !",
            ephemeral=True,
        )
        return

    active_draft_games[channel_id] = True
    await interaction.response.defer()

    gid = interaction.guild_id
    uid = interaction.user.id
    elo_actuel = get_elo(gid, uid)
    scenario = random.choice(SCENARIOS)

    embed = embed_scenario(scenario, interaction.user, elo_actuel)
    embed = embed_scenario(scenario, interaction.user, elo_actuel)
    msg = await interaction.followup.send(embed=embed)

    # Timer 30s avec mise à jour de l'embed toutes les 10s
    deadline = time.monotonic() + 30.0

    async def update_timer():
        for remaining_display in [20, 10]:
            await asyncio.sleep(10)
            if channel_id not in active_draft_games:
                return
            embed_timer = embed_scenario(scenario, interaction.user, elo_actuel)
            embed_timer.description = (
                embed_timer.description.replace(
                    "Tu as **30 secondes** !",
                    f"⏱️ Plus que **{remaining_display} secondes** !"
                )
            )
            try:
                await msg.edit(embed=embed_timer)
            except Exception:
                pass

    timer_task = asyncio.create_task(update_timer())

    def check(m: discord.Message) -> bool:
        return (
            m.channel.id == channel_id
            and m.author.id == uid
            and not m.author.bot
        )

    reponse_finale = None
    position_finale = -2

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            msg_rep = await bot.wait_for("message", timeout=remaining, check=check)
            reponse_finale = msg_rep.content.strip()
            position_finale = trouver_brawler_draft(reponse_finale, scenario)
            break
    except asyncio.TimeoutError:
        pass

    timer_task.cancel()
    active_draft_games.pop(channel_id, None)

    # Calcul delta ELO
    if position_finale == 0:
        delta = 30
    elif position_finale == 1:
        delta = 20
    elif position_finale == 2:
        delta = 15
    elif 3 <= position_finale <= 4:
        delta = 5
    elif position_finale == -2:
        delta = -10
    elif position_finale > 4:
        delta = -15
    else:
        delta = -20

    nouvel_elo = elo_actuel + delta
    set_elo(gid, uid, nouvel_elo)

    embed_res = embed_resultat(
        scenario,
        reponse_finale or "Aucune réponse",
        position_finale,
        delta,
        nouvel_elo,
    )

    try:
        await msg.edit(embed=embed_res)
    except discord.NotFound:
        await interaction.channel.send(embed=embed_res)


@arbre.command(name="draft-elo", description="Affiche ton ELO et ton rang en Draft Ranked")
async def draft_elo_cmd(interaction: discord.Interaction):
    gid = interaction.guild_id
    uid = interaction.user.id
    elo = get_elo(gid, uid)
    rang = get_rang(elo)

    # Classement du serveur
    scores = draft_elo.get(gid, {})
    tries = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rang_serveur = next((i + 1 for i, (u, _) in enumerate(tries) if u == uid), None)

    embed = discord.Embed(
        title="🏆 Draft Ranked — Ton ELO",
        color=0xFFD700,
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="🎖️ Rang", value=rang, inline=True)
    embed.add_field(name="📊 ELO", value=f"`{elo}`", inline=True)
    if rang_serveur:
        embed.add_field(name="🏅 Classement serveur", value=f"`#{rang_serveur}`", inline=True)

    # Barème
    embed.add_field(
        name="📈 Gains/Pertes ELO",
        value=(
            "🎯 Best pick → `+30`\n"
            "✅ Top 2 → `+20`\n"
            "✅ Top 3 → `+15`\n"
            "🟡 Top 5 → `+5`\n"
            "🟠 Top 10 → `-15`\n"
            "❌ Hors top → `-20`\n"
            "⏰ Timeout → `-10`"
        ),
        inline=False,
    )
    embed.set_footer(text="Brawl Zone • Draft Ranked")
    await interaction.response.send_message(embed=embed)


@arbre.command(name="draft-classement", description="Affiche le classement Draft Ranked du serveur")
async def draft_classement_cmd(interaction: discord.Interaction):
    gid = interaction.guild_id
    scores = draft_elo.get(gid, {})

    if not scores:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🏆 Classement Draft Ranked",
                description="Aucune partie jouée ! Lance `/draft` pour commencer.",
                color=0xFFD700,
            )
        )
        return

    tries = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    medailles = ["🥇", "🥈", "🥉"]
    lignes = []
    for i, (uid, elo) in enumerate(tries[:10]):
        membre = interaction.guild.get_member(uid)
        nom = membre.display_name if membre else f"ID {uid}"
        medaille = medailles[i] if i < 3 else f"`#{i + 1}`"
        lignes.append(f"{medaille} **{nom}** — {get_rang(elo)} `{elo} ELO`")

    embed = discord.Embed(
        title="🏆 Classement Draft Ranked",
        description="\n".join(lignes),
        color=0xFFD700,
    )
    embed.set_footer(text="Brawl Zone • Draft Ranked")
    await interaction.response.send_message(embed=embed)


if KEEP_ALIVE_AVAILABLE:
    keep_alive()

bot.run(TOKEN, reconnect=True)

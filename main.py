import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import random
import io
import os
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
            "`/brawler_liste` — Liste des 101 brawlers"
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
#  LANCEMENT
# ═══════════════════════════════════════════════════════════
if KEEP_ALIVE_AVAILABLE:
    keep_alive()

bot.run(TOKEN, reconnect=True)

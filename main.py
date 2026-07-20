import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

try:
    from keep_alive import keep_alive
    KEEP_ALIVE_AVAILABLE = True
except ImportError:
    KEEP_ALIVE_AVAILABLE = False

load_dotenv()
TOKEN = os.getenv("TOKEN_BOT")

LIEN_INVITATION = (
    "https://discord.com/oauth2/authorize?"
    "client_id=1495103873373704472"
    "&permissions=4785076768427024"
    "&integration_type=0"
    "&scope=bot+applications.commands"
)

# ═══════════════════════════════════════════════════════════
#  RÉGLAGES
# ═══════════════════════════════════════════════════════════
DUREE_CHOIX = 60          # secondes laissées au membre pour choisir un type
DELAI_NETTOYAGE = 3       # secondes d'attente avant de vérifier si un vocal temp est vide
DELAI_SUPPRESSION_MSG = 20  # secondes avant de supprimer le message une fois le résultat connu
CONFIG_PATH = "vocaux_config.json"

# ═══════════════════════════════════════════════════════════
#  PERSISTENCE (fichier JSON simple : hubs, types, vocaux temp)
# ═══════════════════════════════════════════════════════════
def charger_configuration():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauvegarder_configuration():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(configuration, f, indent=2, ensure_ascii=False)


configuration = charger_configuration()


def config_serveur(guild_id: int) -> dict:
    """Retourne (et initialise si besoin) la config d'un serveur."""
    gid = str(guild_id)
    if gid not in configuration:
        configuration[gid] = {"hubs": [], "types": {}, "temp_channels": {}}
    configuration[gid].setdefault("hubs", [])
    configuration[gid].setdefault("types", {})
    configuration[gid].setdefault("temp_channels", {})
    return configuration[gid]


# ═══════════════════════════════════════════════════════════
#  BOT — pas besoin d'intents privilégiés (members/presence)
# ═══════════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
arbre = bot.tree


@bot.event
async def on_ready():
    # Nettoyage au démarrage : hubs/vocaux supprimés pendant que le bot était offline
    for gid, gconf in list(configuration.items()):
        guild = bot.get_guild(int(gid))
        if not guild:
            continue
        gconf["hubs"] = [cid for cid in gconf["hubs"] if guild.get_channel(int(cid))]
        for cid in list(gconf["temp_channels"].keys()):
            salon = guild.get_channel(int(cid))
            if not salon or len(salon.members) == 0:
                gconf["temp_channels"].pop(cid, None)
                if salon:
                    try:
                        await salon.delete(reason="Nettoyage au démarrage — vocal vide")
                    except discord.HTTPException:
                        pass
    sauvegarder_configuration()

    await arbre.sync()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="/vocal")
    )
    print(f"[✓] {bot.user} connecté — Slash commands synchronisées.")


# ═══════════════════════════════════════════════════════════
#  MENU DE CHOIX DU TYPE DE VOCAL (affiché dans le chat vocal)
# ═══════════════════════════════════════════════════════════
class ChoixTypeSelect(discord.ui.Select):
    def __init__(self, membre: discord.Member, gconf: dict):
        self.membre = membre
        options = [
            discord.SelectOption(
                label=nom,
                description=f"Limite : {info['limite']} membre(s)" if info["limite"] else "Limite : illimitée",
                emoji="🔊",
            )
            for nom, info in list(gconf["types"].items())[:25]
        ]
        super().__init__(
            placeholder="Choisis le type de vocal à créer...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.membre.id:
            await interaction.response.send_message(
                "❌ Ce choix ne t'est pas destiné.", ephemeral=True
            )
            return
        await creer_vocal_temporaire(interaction, self.membre, self.values[0])
        self.view.stop()


class ChoixTypeView(discord.ui.View):
    def __init__(self, membre: discord.Member, gconf: dict):
        super().__init__(timeout=DUREE_CHOIX)
        self.membre = membre
        self.message: discord.Message | None = None
        self.add_item(ChoixTypeSelect(membre, gconf))

    async def on_timeout(self):
        # Le membre n'a pas répondu à temps → on le déconnecte du vocal
        if self.membre.voice is not None:
            try:
                await self.membre.move_to(None)
            except discord.HTTPException:
                pass
        if self.message:
            embed = discord.Embed(
                title="⏰ Temps écoulé",
                description=f"{self.membre.mention} n'a pas choisi de type de vocal à temps et a été déconnecté.",
                color=0xFF4444,
            )
            try:
                await self.message.edit(content=None, embed=embed, view=None)
                asyncio.create_task(supprimer_message_plus_tard(self.message))
            except discord.HTTPException:
                pass


async def supprimer_message_plus_tard(message: discord.Message, delai: int = DELAI_SUPPRESSION_MSG):
    """Attend `delai` secondes puis supprime le message (silencieux si déjà supprimé)."""
    await asyncio.sleep(delai)
    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def creer_vocal_temporaire(interaction: discord.Interaction, membre: discord.Member, nom_type: str):
    gconf = config_serveur(membre.guild.id)
    type_info = gconf["types"].get(nom_type)
    if not type_info:
        await interaction.response.send_message("❌ Ce type de vocal n'existe plus.", ephemeral=True)
        return

    hub = interaction.channel
    nom_salon = type_info["format_nom"].format(pseudo=membre.display_name, type=nom_type)[:100]

    nouveau_salon = await membre.guild.create_voice_channel(
        name=nom_salon,
        category=hub.category,
        user_limit=type_info["limite"],
    )
    gconf["temp_channels"][str(nouveau_salon.id)] = {"owner_id": membre.id, "type": nom_type}
    sauvegarder_configuration()

    try:
        await membre.move_to(nouveau_salon)
    except discord.HTTPException:
        pass

    embed = discord.Embed(
        title="✅ Vocal créé !",
        description=f"{membre.mention}, ton vocal **{nom_salon}** a été créé et tu y as été déplacé.",
        color=0x00FF88,
    )
    await interaction.response.edit_message(content=None, embed=embed, view=None)
    msg = await interaction.original_response()
    asyncio.create_task(supprimer_message_plus_tard(msg))


# ═══════════════════════════════════════════════════════════
#  ÉVÉNEMENTS VOCAUX : rejoindre un hub / vider un vocal temp
# ═══════════════════════════════════════════════════════════
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return

    gconf = config_serveur(member.guild.id)

    # ── Rejoint un salon hub ────────────────────────────────
    if after.channel and str(after.channel.id) in gconf["hubs"] and before.channel != after.channel:
        if not gconf["types"]:
            return  # aucun type configuré par le staff, on ne fait rien

        embed = discord.Embed(
            title="🎙️ Choisis ton type de vocal",
            description=(
                f"{member.mention}, sélectionne le type de vocal que tu veux créer ci-dessous.\n"
                f"⏱️ Tu as **{DUREE_CHOIX} secondes**, sinon tu seras déconnecté."
            ),
            color=0xFFD700,
        )
        view = ChoixTypeView(member, gconf)
        try:
            msg = await after.channel.send(
                content=member.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
            view.message = msg
        except discord.Forbidden:
            pass

    # ── Quitte un vocal temporaire → suppression si vide ────
    if before.channel and str(before.channel.id) in gconf["temp_channels"]:
        await asyncio.sleep(DELAI_NETTOYAGE)
        salon = member.guild.get_channel(before.channel.id)
        if salon and len(salon.members) == 0:
            gconf["temp_channels"].pop(str(before.channel.id), None)
            sauvegarder_configuration()
            try:
                await salon.delete(reason="Vocal temporaire vide")
            except discord.HTTPException:
                pass


# ═══════════════════════════════════════════════════════════
#  GESTION DES ERREURS DE PERMISSIONS
# ═══════════════════════════════════════════════════════════
@arbre.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ Tu n'as pas la permission d'utiliser cette commande."
    else:
        logging.exception("Erreur commande slash", exc_info=error)
        msg = "❌ Une erreur est survenue en exécutant cette commande."

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


# ═══════════════════════════════════════════════════════════
#  GROUPES DE COMMANDES  /vocal type ...  /vocal hub ...
# ═══════════════════════════════════════════════════════════
groupe_vocal = app_commands.Group(name="vocal", description="Système de vocaux temporaires")
groupe_type = app_commands.Group(name="type", description="Gestion des types de vocaux (staff)", parent=groupe_vocal)
groupe_hub = app_commands.Group(name="hub", description="Gestion des salons hub (staff)", parent=groupe_vocal)


# ── /vocal type creer ────────────────────────────────────────
@groupe_type.command(name="creer", description="Crée un nouveau type de vocal proposé aux membres")
@app_commands.describe(
    nom="Nom du type (ex: Duo, Squad, Chill)",
    limite="Nombre max de membres dans ce type de vocal (0 = illimité)",
    modifiable="Le créateur peut-il renommer/changer la limite de son vocal ensuite ?",
    format_nom="Format du nom du vocal créé. Utilise {pseudo} et {type}.",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def type_creer(
    interaction: discord.Interaction,
    nom: str,
    limite: app_commands.Range[int, 0, 99] = 0,
    modifiable: bool = False,
    format_nom: str = "🔊 {type} de {pseudo}",
):
    gconf = config_serveur(interaction.guild_id)
    if any(t.lower() == nom.lower() for t in gconf["types"]):
        await interaction.response.send_message(f"❌ Le type **{nom}** existe déjà.", ephemeral=True)
        return

    gconf["types"][nom] = {"limite": limite, "modifiable": modifiable, "format_nom": format_nom}
    sauvegarder_configuration()

    embed = discord.Embed(title="✅ Type de vocal créé", color=0x00FF88)
    embed.add_field(name="Nom", value=nom, inline=True)
    embed.add_field(name="Limite", value=str(limite) if limite else "Illimitée", inline=True)
    embed.add_field(name="Modifiable par le créateur", value="Oui" if modifiable else "Non", inline=True)
    embed.add_field(name="Format du nom", value=f"`{format_nom}`", inline=False)
    embed.set_footer(text="Brawl Zone • Vocaux temporaires")
    await interaction.response.send_message(embed=embed)


# ── /vocal type supprimer ───────────────────────────────────
@groupe_type.command(name="supprimer", description="Supprime un type de vocal")
@app_commands.describe(nom="Nom du type à supprimer")
@app_commands.checks.has_permissions(manage_channels=True)
async def type_supprimer(interaction: discord.Interaction, nom: str):
    gconf = config_serveur(interaction.guild_id)
    cle = next((t for t in gconf["types"] if t.lower() == nom.lower()), None)
    if not cle:
        await interaction.response.send_message(f"❌ Le type **{nom}** n'existe pas.", ephemeral=True)
        return
    del gconf["types"][cle]
    sauvegarder_configuration()
    await interaction.response.send_message(f"✅ Type **{cle}** supprimé.")


@type_supprimer.autocomplete("nom")
async def type_supprimer_autocomplete(interaction: discord.Interaction, actuel: str):
    gconf = config_serveur(interaction.guild_id)
    return [
        app_commands.Choice(name=t, value=t)
        for t in gconf["types"] if actuel.lower() in t.lower()
    ][:25]


# ── /vocal type liste ────────────────────────────────────────
@groupe_type.command(name="liste", description="Affiche tous les types de vocaux disponibles")
async def type_liste(interaction: discord.Interaction):
    gconf = config_serveur(interaction.guild_id)
    if not gconf["types"]:
        await interaction.response.send_message("Aucun type de vocal n'a encore été créé.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Types de vocaux disponibles", color=0xFFD700)
    for nom, info in gconf["types"].items():
        embed.add_field(
            name=f"🔊 {nom}",
            value=(
                f"Limite : {info['limite'] if info['limite'] else 'Illimitée'}\n"
                f"Modifiable : {'Oui' if info['modifiable'] else 'Non'}\n"
                f"Format : `{info['format_nom']}`"
            ),
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── /vocal hub creer ─────────────────────────────────────────
@groupe_hub.command(name="creer", description="Crée un salon hub (rejoindre = proposer un choix de vocal)")
@app_commands.describe(
    salon="Salon vocal existant à transformer en hub (sinon un nouveau est créé)",
    nom="Nom du nouveau salon hub (si aucun salon existant n'est donné)",
    categorie="Catégorie où créer le nouveau hub (optionnel)",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def hub_creer(
    interaction: discord.Interaction,
    salon: discord.VoiceChannel = None,
    nom: str = "➕ Créer un vocal",
    categorie: discord.CategoryChannel = None,
):
    gconf = config_serveur(interaction.guild_id)
    if not gconf["types"]:
        await interaction.response.send_message(
            "❌ Crée d'abord au moins un type de vocal avec `/vocal type creer`.", ephemeral=True
        )
        return

    cible = salon or await interaction.guild.create_voice_channel(name=nom, category=categorie)

    if str(cible.id) in gconf["hubs"]:
        await interaction.response.send_message(f"❌ {cible.mention} est déjà un hub.", ephemeral=True)
        return

    gconf["hubs"].append(str(cible.id))
    sauvegarder_configuration()

    embed = discord.Embed(
        title="✅ Hub créé",
        description=f"{cible.mention} est maintenant un salon hub : le rejoindre proposera un choix de vocal.",
        color=0x00FF88,
    )
    await interaction.response.send_message(embed=embed)


# ── /vocal hub supprimer ────────────────────────────────────
@groupe_hub.command(name="supprimer", description="Retire un salon de la liste des hubs")
@app_commands.describe(salon="Salon hub à retirer", supprimer_le_salon="Supprimer aussi le salon Discord ?")
@app_commands.checks.has_permissions(manage_channels=True)
async def hub_supprimer(interaction: discord.Interaction, salon: discord.VoiceChannel, supprimer_le_salon: bool = False):
    gconf = config_serveur(interaction.guild_id)
    if str(salon.id) not in gconf["hubs"]:
        await interaction.response.send_message(f"❌ {salon.mention} n'est pas un hub.", ephemeral=True)
        return

    gconf["hubs"].remove(str(salon.id))
    sauvegarder_configuration()

    if supprimer_le_salon:
        try:
            await salon.delete(reason="Hub retiré")
        except discord.HTTPException:
            pass

    await interaction.response.send_message(f"✅ {salon.mention} n'est plus un hub.")


# ── /vocal hub liste ─────────────────────────────────────────
@groupe_hub.command(name="liste", description="Affiche tous les salons hub du serveur")
async def hub_liste(interaction: discord.Interaction):
    gconf = config_serveur(interaction.guild_id)
    salons = [interaction.guild.get_channel(int(cid)) for cid in gconf["hubs"]]
    salons = [s for s in salons if s]

    if not salons:
        await interaction.response.send_message("Aucun hub n'a encore été créé.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📋 Salons hub",
        description="\n".join(f"🎙️ {s.mention}" for s in salons),
        color=0xFFD700,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════
#  PANNEAU DE CONFIGURATION INTERACTIF  —  /vocal config
# ═══════════════════════════════════════════════════════════
def embed_config(gconf: dict) -> discord.Embed:
    types_txt = "\n".join(
        f"🔊 **{n}** — limite {i['limite'] or '∞'}, {'modifiable' if i['modifiable'] else 'fixe'}"
        for n, i in gconf["types"].items()
    ) or "_Aucun type créé_"
    hubs_txt = "\n".join(f"🎙️ <#{cid}>" for cid in gconf["hubs"]) or "_Aucun hub créé_"

    embed = discord.Embed(
        title="⚙️ Configuration — Vocaux temporaires",
        description="Utilise les boutons ci-dessous pour tout configurer, sans taper d'autre commande.",
        color=0xFFD700,
    )
    embed.add_field(name=f"Types ({len(gconf['types'])})", value=types_txt[:1024], inline=False)
    embed.add_field(name=f"Hubs ({len(gconf['hubs'])})", value=hubs_txt[:1024], inline=False)
    embed.set_footer(text="Panneau valable 5 minutes • Visible uniquement par toi")
    return embed


class VueBase(discord.ui.View):
    """Base commune : restreint le panneau à son auteur et le désactive au timeout."""

    def __init__(self, guild_id: int, auteur_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.auteur_id = auteur_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.auteur_id:
            await interaction.response.send_message("❌ Ce panneau ne t'est pas destiné.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# ── Étape : nouveau type (Modal) ────────────────────────────
class TypeModal(discord.ui.Modal, title="Nouveau type de vocal"):
    nom = discord.ui.TextInput(label="Nom du type", placeholder="Duo", max_length=50)
    limite = discord.ui.TextInput(label="Limite de membres (0 = illimité)", default="0", max_length=2)
    modifiable = discord.ui.TextInput(label="Modifiable par le créateur ? (oui/non)", default="non", max_length=3)
    format_nom = discord.ui.TextInput(
        label="Format du nom ({pseudo} et {type})",
        default="🔊 {type} de {pseudo}",
        max_length=100,
        required=False,
    )

    def __init__(self, guild_id: int, auteur_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.auteur_id = auteur_id

    async def on_submit(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        nom_val = self.nom.value.strip()

        if any(t.lower() == nom_val.lower() for t in gconf["types"]):
            await interaction.response.send_message(f"❌ Le type **{nom_val}** existe déjà.", ephemeral=True)
            return
        try:
            limite_val = max(0, min(99, int(self.limite.value.strip())))
        except ValueError:
            await interaction.response.send_message("❌ La limite doit être un nombre entier.", ephemeral=True)
            return

        modifiable_val = self.modifiable.value.strip().lower() in ("oui", "yes", "true", "1")
        format_val = self.format_nom.value.strip() or "🔊 {type} de {pseudo}"

        gconf["types"][nom_val] = {"limite": limite_val, "modifiable": modifiable_val, "format_nom": format_val}
        sauvegarder_configuration()

        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


# ── Étape : suppression d'un type (Select) ──────────────────
class SelectTypeASupprimer(discord.ui.Select):
    def __init__(self, guild_id: int, gconf: dict):
        self.guild_id = guild_id
        options = [discord.SelectOption(label=n, value=n, emoji="🔊") for n in gconf["types"]][:25]
        super().__init__(placeholder="Choisis le type à supprimer...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        gconf["types"].pop(self.values[0], None)
        sauvegarder_configuration()
        vue = VueConfig(self.guild_id, self.view.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class VueSupprimerType(VueBase):
    def __init__(self, guild_id: int, auteur_id: int, gconf: dict):
        super().__init__(guild_id, auteur_id)
        self.add_item(SelectTypeASupprimer(guild_id, gconf))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def retour(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


# ── Étape : nouveau hub (salon existant OU modal) ───────────
class HubModal(discord.ui.Modal, title="Nouveau salon hub"):
    nom = discord.ui.TextInput(label="Nom du salon", default="➕ Créer un vocal", max_length=100)

    def __init__(self, guild_id: int, auteur_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.auteur_id = auteur_id

    async def on_submit(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        salon = await interaction.guild.create_voice_channel(name=self.nom.value.strip()[:100])
        gconf["hubs"].append(str(salon.id))
        sauvegarder_configuration()

        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class SelectSalonExistant(discord.ui.ChannelSelect):
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        super().__init__(
            placeholder="...ou choisis un salon vocal existant à transformer",
            channel_types=[discord.ChannelType.voice],
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        salon = interaction.guild.get_channel(self.values[0].id)
        if not salon:
            await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
            return
        if str(salon.id) in gconf["hubs"]:
            await interaction.response.send_message(f"❌ {salon.mention} est déjà un hub.", ephemeral=True)
            return

        gconf["hubs"].append(str(salon.id))
        sauvegarder_configuration()

        vue = VueConfig(self.guild_id, self.view.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class VueNouveauHub(VueBase):
    def __init__(self, guild_id: int, auteur_id: int):
        super().__init__(guild_id, auteur_id)
        self.add_item(SelectSalonExistant(guild_id))

    @discord.ui.button(label="Créer un nouveau salon", style=discord.ButtonStyle.success, emoji="➕", row=1)
    async def nouveau_salon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(HubModal(self.guild_id, self.auteur_id))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def retour(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


# ── Étape : suppression d'un hub (Select) ───────────────────
class SelectHubASupprimer(discord.ui.Select):
    def __init__(self, guild_id: int, gconf: dict, guild: discord.Guild):
        self.guild_id = guild_id
        options = []
        for cid in gconf["hubs"]:
            salon = guild.get_channel(int(cid))
            if salon:
                options.append(discord.SelectOption(label=salon.name, value=cid, emoji="🎙️"))
        super().__init__(placeholder="Choisis le hub à supprimer...", options=options[:25], min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        if self.values[0] in gconf["hubs"]:
            gconf["hubs"].remove(self.values[0])
            sauvegarder_configuration()
        vue = VueConfig(self.guild_id, self.view.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class VueSupprimerHub(VueBase):
    def __init__(self, guild_id: int, auteur_id: int, gconf: dict, guild: discord.Guild):
        super().__init__(guild_id, auteur_id)
        self.add_item(SelectHubASupprimer(guild_id, gconf, guild))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def retour(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


# ── Panneau principal ────────────────────────────────────────
class VueConfig(VueBase):
    def __init__(self, guild_id: int, auteur_id: int):
        super().__init__(guild_id, auteur_id)

    @discord.ui.button(label="Nouveau type", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def bouton_nouveau_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TypeModal(self.guild_id, self.auteur_id))

    @discord.ui.button(label="Supprimer un type", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def bouton_supprimer_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        if not gconf["types"]:
            await interaction.response.send_message("❌ Aucun type à supprimer.", ephemeral=True)
            return
        vue = VueSupprimerType(self.guild_id, self.auteur_id, gconf)
        await interaction.response.edit_message(
            embed=discord.Embed(title="🗑️ Supprimer un type", description="Choisis le type à retirer.", color=0xFF4444),
            view=vue,
        )
        vue.message = interaction.message

    @discord.ui.button(label="Nouveau hub", style=discord.ButtonStyle.success, emoji="🎙️", row=1)
    async def bouton_nouveau_hub(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        if not gconf["types"]:
            await interaction.response.send_message(
                "❌ Crée d'abord au moins un type de vocal avant de créer un hub.", ephemeral=True
            )
            return
        vue = VueNouveauHub(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎙️ Nouveau hub",
                description="Choisis un salon vocal existant à transformer, ou crée-en un nouveau.",
                color=0x00FF88,
            ),
            view=vue,
        )
        vue.message = interaction.message

    @discord.ui.button(label="Supprimer un hub", style=discord.ButtonStyle.danger, emoji="🚫", row=1)
    async def bouton_supprimer_hub(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        if not gconf["hubs"]:
            await interaction.response.send_message("❌ Aucun hub à supprimer.", ephemeral=True)
            return
        vue = VueSupprimerHub(self.guild_id, self.auteur_id, gconf, interaction.guild)
        await interaction.response.edit_message(
            embed=discord.Embed(title="🚫 Supprimer un hub", description="Choisis le hub à retirer.", color=0xFF4444),
            view=vue,
        )
        vue.message = interaction.message

    @discord.ui.button(label="Actualiser", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
    async def bouton_actualiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=self)

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.secondary, emoji="✖️", row=2)
    async def bouton_fermer(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(description="Panneau de configuration fermé.", color=0x2B2D31)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


@groupe_vocal.command(name="config", description="Panneau de configuration interactif (types & hubs) en un seul endroit")
@app_commands.checks.has_permissions(manage_channels=True)
async def vocal_config(interaction: discord.Interaction):
    gconf = config_serveur(interaction.guild_id)
    vue = VueConfig(interaction.guild_id, interaction.user.id)
    await interaction.response.send_message(embed=embed_config(gconf), view=vue, ephemeral=True)
    vue.message = await interaction.original_response()


# ── /vocal renommer (membre) ────────────────────────────────
@groupe_vocal.command(name="renommer", description="Renomme ton vocal temporaire (si autorisé)")
@app_commands.describe(nouveau_nom="Nouveau nom du vocal")
async def vocal_renommer(interaction: discord.Interaction, nouveau_nom: str):
    gconf = config_serveur(interaction.guild_id)
    salon = interaction.user.voice.channel if interaction.user.voice else None
    info = gconf["temp_channels"].get(str(salon.id)) if salon else None

    if not info:
        await interaction.response.send_message("❌ Tu dois être dans un vocal temporaire.", ephemeral=True)
        return
    if info["owner_id"] != interaction.user.id:
        await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
        return
    type_info = gconf["types"].get(info["type"])
    if not type_info or not type_info.get("modifiable"):
        await interaction.response.send_message("❌ Ce type de vocal ne peut pas être personnalisé.", ephemeral=True)
        return

    await salon.edit(name=nouveau_nom[:100])
    await interaction.response.send_message(f"✅ Vocal renommé en **{nouveau_nom}**.", ephemeral=True)


# ── /vocal limite (membre) ──────────────────────────────────
@groupe_vocal.command(name="limite", description="Change la limite de membres de ton vocal temporaire (si autorisé)")
@app_commands.describe(nombre="Nouvelle limite (0 = illimité)")
async def vocal_limite(interaction: discord.Interaction, nombre: app_commands.Range[int, 0, 99]):
    gconf = config_serveur(interaction.guild_id)
    salon = interaction.user.voice.channel if interaction.user.voice else None
    info = gconf["temp_channels"].get(str(salon.id)) if salon else None

    if not info:
        await interaction.response.send_message("❌ Tu dois être dans un vocal temporaire.", ephemeral=True)
        return
    if info["owner_id"] != interaction.user.id:
        await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
        return
    type_info = gconf["types"].get(info["type"])
    if not type_info or not type_info.get("modifiable"):
        await interaction.response.send_message("❌ Ce type de vocal ne peut pas être personnalisé.", ephemeral=True)
        return

    await salon.edit(user_limit=nombre)
    await interaction.response.send_message(
        f"✅ Limite mise à jour : **{nombre if nombre else 'illimitée'}**.", ephemeral=True
    )

class InviteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

# ═══════════════════════════════════════════════════════════
#  PANEL D'INVITATION
# ═══════════════════════════════════════════════════════════
    self.add_item(
    discord.ui.Button(
        label="🤖 Inviter Beflow",
        style=discord.ButtonStyle.link,
        url=LIEN_INVITATION,
    )
)

# ═══════════════════════════════════════════════════════════
#  AIDE — /help avec panel interactif
# ═══════════════════════════════════════════════════════════
CMDS = {
    "vocal config": {
        "emoji": "⚙️",
        "titre": "/vocal config",
        "categorie": "Staff",
        "desc": "Panneau de configuration interactif tout-en-un.",
        "details": (
            "Ouvre un panneau avec des boutons pour tout gérer sans taper d'autres commandes : "
            "créer/supprimer un type, créer/supprimer un hub. Un formulaire s'ouvre pour les infos "
            "à saisir (nom, limite...), et un menu déroulant pour choisir un salon existant.\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "vocal type creer": {
        "emoji": "➕",
        "titre": "/vocal type creer",
        "categorie": "Staff",
        "desc": "Crée un nouveau type de vocal proposé aux membres.",
        "details": (
            "Définit un type de vocal que les membres pourront choisir en rejoignant un hub "
            "(ex: Duo, Squad, Chill).\n\n"
            "**Options**\n"
            "`nom` — Nom du type (ex: Duo)\n"
            "`limite` — Nombre max de membres (0 = illimité)\n"
            "`modifiable` — Le créateur peut-il renommer/changer la limite ensuite ?\n"
            "`format_nom` — Modèle du nom du vocal créé, avec `{pseudo}` et `{type}`\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "vocal type supprimer": {
        "emoji": "🗑️",
        "titre": "/vocal type supprimer",
        "categorie": "Staff",
        "desc": "Supprime un type de vocal existant.",
        "details": (
            "Retire un type de la liste proposée aux membres (autocomplétion disponible).\n"
            "Les vocaux déjà créés avec ce type ne sont pas affectés.\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "vocal type liste": {
        "emoji": "📋",
        "titre": "/vocal type liste",
        "categorie": "Info",
        "desc": "Affiche tous les types de vocaux disponibles.",
        "details": "Liste chaque type avec sa limite, s'il est modifiable et son format de nom.",
    },
    "vocal hub creer": {
        "emoji": "🎙️",
        "titre": "/vocal hub creer",
        "categorie": "Staff",
        "desc": "Crée un salon hub (rejoindre = proposer un choix de vocal).",
        "details": (
            "Transforme un salon vocal existant en hub, ou en crée un nouveau si aucun n'est fourni.\n"
            "Autant de hubs que voulu peuvent exister en même temps.\n\n"
            "**Options**\n"
            "`salon` — Salon existant à transformer (optionnel)\n"
            "`nom` — Nom du nouveau salon si aucun n'est fourni\n"
            "`categorie` — Catégorie où créer le hub (optionnel)\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "vocal hub supprimer": {
        "emoji": "🚫",
        "titre": "/vocal hub supprimer",
        "categorie": "Staff",
        "desc": "Retire un salon de la liste des hubs.",
        "details": (
            "Le salon arrête de proposer le choix de vocal en le rejoignant.\n"
            "`supprimer_le_salon` permet aussi de supprimer le salon Discord.\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "vocal hub liste": {
        "emoji": "📋",
        "titre": "/vocal hub liste",
        "categorie": "Info",
        "desc": "Affiche tous les salons hub du serveur.",
        "details": "Liste tous les salons actuellement configurés comme hub.",
    },
    "vocal renommer": {
        "emoji": "✏️",
        "titre": "/vocal renommer",
        "categorie": "Membres",
        "desc": "Renomme ton vocal temporaire.",
        "details": (
            "Utilisable uniquement si tu es dans le vocal temporaire que tu as créé, "
            "et si le type autorise la modification (réglé par le staff).\n\n"
            "**Options**\n"
            "`nouveau_nom` — Nouveau nom du vocal"
        ),
    },
    "vocal limite": {
        "emoji": "👥",
        "titre": "/vocal limite",
        "categorie": "Membres",
        "desc": "Change la limite de membres de ton vocal temporaire.",
        "details": (
            "Utilisable uniquement si tu es dans le vocal temporaire que tu as créé, "
            "et si le type autorise la modification (réglé par le staff).\n\n"
            "**Options**\n"
            "`nombre` — Nouvelle limite (0 = illimité)"
        ),
    },
}


def embed_apercu() -> discord.Embed:
    embed = discord.Embed(
        title="❓ Aide — Vocaux temporaires",
        description="Sélectionne une commande dans le menu ci-dessous pour voir son détail.",
        color=0xFFD700,
    )
    embed.add_field(
        name="🛠️ Staff",
        value=(
            "`/vocal config` — ⭐ Panneau interactif tout-en-un\n"
            "`/vocal type creer` — Crée un type de vocal\n"
            "`/vocal type supprimer` — Supprime un type\n"
            "`/vocal hub creer` — Crée un salon hub\n"
            "`/vocal hub supprimer` — Retire un hub"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Info",
        value=(
            "`/vocal type liste` — Liste des types\n"
            "`/vocal hub liste` — Liste des hubs"
        ),
        inline=False,
    )
    embed.add_field(
        name="👤 Membres",
        value=(
            "`/vocal renommer` — Renomme ton vocal\n"
            "`/vocal limite` — Change la limite de ton vocal"
        ),
        inline=False,
    )
    embed.set_footer(text="Vocaux temporaires • Menu valable 3 minutes")
    return embed


class AideSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Vue d'ensemble", value="apercu",
                description="Retour à la liste des commandes", emoji="📋",
            )
        ]
        for cle, info in CMDS.items():
            options.append(
                discord.SelectOption(
                    label=info["titre"], value=cle,
                    description=info["desc"][:100], emoji=info["emoji"],
                )
            )
        super().__init__(
            placeholder="Sélectionne une commande pour en savoir plus...",
            options=options[:25], min_values=1, max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.auteur_id:
            await interaction.response.send_message("❌ Ce menu ne t'est pas destiné.", ephemeral=True)
            return

        if self.values[0] == "apercu":
            embed = embed_apercu()
        else:
            info = CMDS[self.values[0]]
            embed = discord.Embed(
                title=f"{info['emoji']} {info['titre']}",
                description=info["desc"],
                color=0xFFD700,
            )
            embed.add_field(name="📖 Détails", value=info["details"], inline=False)
            embed.set_footer(text=f"Catégorie : {info['categorie']} • Reviens à la vue d'ensemble dans le menu")

        await interaction.response.edit_message(embed=embed, view=self.view)


class AideView(discord.ui.View):
    def __init__(self, auteur_id: int):
        super().__init__(timeout=180)
        self.auteur_id = auteur_id
        self.message: discord.Message | None = None
        self.add_item(AideSelect())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@arbre.command(name="help", description="Affiche l'aide du bot vocaux temporaires")
async def help_cmd(interaction: discord.Interaction):
    view = AideView(interaction.user.id)
    await interaction.response.send_message(embed=embed_apercu(), view=view, ephemeral=True)
    view.message = await interaction.original_response()


arbre.add_command(groupe_vocal)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        embed = discord.Embed(
            title="🌊 Beflow",
            description=(
                "Salut ! Je suis **Beflow**.\n\n"
                "Je crée automatiquement des **vocaux temporaires** entièrement configurables.\n\n"
                "Clique sur le bouton ci-dessous pour m'ajouter à ton serveur."
            ),
            color=0x5865F2,
        )

        embed.add_field(
            name="✨ Fonctionnalités",
            value=(
                "🎙️ Vocaux temporaires\n"
                "🎛️ Types de salons\n"
                "📂 Hubs\n"
                "⚙️ Configuration interactive\n"
                "👤 Renommage & limite des vocaux"
            ),
            inline=False,
        )

        embed.set_footer(text="Développé par Bebefirm1")

        await message.reply(
            embed=embed,
            view=InviteView(),
            mention_author=False,
        )

    await bot.process_commands(message)
    
if KEEP_ALIVE_AVAILABLE:
    keep_alive()

bot.run(TOKEN, reconnect=True)

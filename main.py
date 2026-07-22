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
    "&permissions=8"
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
#
#  Structure d'un serveur :
#  {
#    "hubs": {"<channel_id>": {"types": ["Duo", "Trio"]}, ...},
#    "types": {"<nom>": {"limite":..., "modifiable_nom":..., "modifiable_limite":..., "format_nom":...}, ...},
#    "temp_channels": {"<channel_id>": {"owner_id":..., "type":..., "masque":..., "verrou":...}, ...},
#  }
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


def migrer_configuration():
    """Convertit l'ancien format (hubs = liste de salons, types partagés par tout
    le serveur) vers le nouveau format (hubs = dict avec la liste des types
    autorisés dans chaque hub). Les hubs existants récupèrent tous les types déjà
    définis, pour ne rien casser au premier démarrage après mise à jour."""
    modifie = False
    for gconf in configuration.values():
        if isinstance(gconf.get("hubs"), list):
            types_existants = list(gconf.get("types", {}).keys())
            gconf["hubs"] = {cid: {"types": list(types_existants)} for cid in gconf["hubs"]}
            modifie = True
    if modifie:
        sauvegarder_configuration()


migrer_configuration()


def config_serveur(guild_id: int) -> dict:
    """Retourne (et initialise si besoin) la config d'un serveur."""
    gid = str(guild_id)
    if gid not in configuration:
        configuration[gid] = {"hubs": {}, "types": {}, "temp_channels": {}}
    gconf = configuration[gid]
    gconf.setdefault("hubs", {})
    gconf.setdefault("types", {})
    gconf.setdefault("temp_channels", {})
    if isinstance(gconf["hubs"], list):
        gconf["hubs"] = {cid: {"types": list(gconf["types"].keys())} for cid in gconf["hubs"]}
    return gconf


# ═══════════════════════════════════════════════════════════
#  BOT — pas besoin d'intents privilégiés (members/presence)
# ═══════════════════════════════════════════════════════════
intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
arbre = bot.tree


@bot.event
async def on_ready():
    # Vue persistante : nécessaire pour que les boutons du panneau vocal
    # continuent de fonctionner après un redémarrage du bot
    bot.add_view(PanelVocalView())

    # Nettoyage au démarrage : hubs/vocaux supprimés pendant que le bot était offline
    for gid, gconf in list(configuration.items()):
        guild = bot.get_guild(int(gid))
        if not guild:
            continue
        gconf["hubs"] = {
            cid: info for cid, info in gconf.get("hubs", {}).items() if guild.get_channel(int(cid))
        }
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
        activity=discord.Activity(type=discord.ActivityType.watching, name="Not Feller & Mitteg & Nadouja")
    )
    print(f"[✓] {bot.user} connecté — Slash commands synchronisées.")


# ═══════════════════════════════════════════════════════════
#  MENU DE CHOIX DU TYPE DE VOCAL (affiché dans le chat vocal)
# ═══════════════════════════════════════════════════════════
class ChoixTypeSelect(discord.ui.Select):
    def __init__(self, membre: discord.Member, types_disponibles: dict):
        self.membre = membre
        options = [
            discord.SelectOption(
                label=nom,
                description=f"Limite : {info['limite']} membre(s)" if info["limite"] else "Limite : illimitée",
                emoji="🔊",
            )
            for nom, info in list(types_disponibles.items())[:25]
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
    def __init__(self, membre: discord.Member, types_disponibles: dict):
        super().__init__(timeout=DUREE_CHOIX)
        self.membre = membre
        self.message: discord.Message | None = None
        self.add_item(ChoixTypeSelect(membre, types_disponibles))

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


# ═══════════════════════════════════════════════════════════
#  PANNEAU DE GESTION DU VOCAL (affiché dans le chat du vocal créé)
#  Vue persistante : les boutons fonctionnent même après un redémarrage
#  du bot, et la permission (nom/limite) est vérifiée à chaque clic.
# ═══════════════════════════════════════════════════════════
class RenommerVocalModal(discord.ui.Modal, title="Renommer le vocal"):
    nouveau_nom = discord.ui.TextInput(label="Nouveau nom", max_length=100)

    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        salon = interaction.guild.get_channel(self.channel_id)
        if not salon:
            await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
            return
        await salon.edit(name=self.nouveau_nom.value[:100])
        await interaction.response.send_message(f"✅ Vocal renommé en **{self.nouveau_nom.value}**.", ephemeral=True)


class LimiteVocalModal(discord.ui.Modal, title="Changer la limite"):
    nombre = discord.ui.TextInput(label="Nouvelle limite (0 = illimité)", default="0", max_length=2)

    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valeur = max(0, min(99, int(self.nombre.value.strip())))
        except ValueError:
            await interaction.response.send_message("❌ La limite doit être un nombre entier.", ephemeral=True)
            return
        salon = interaction.guild.get_channel(self.channel_id)
        if not salon:
            await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
            return
        await salon.edit(user_limit=valeur)
        await interaction.response.send_message(
            f"✅ Limite mise à jour : **{valeur if valeur else 'illimitée'}**.", ephemeral=True
        )


def embed_panel_vocal(type_nom: str, masque: bool, verrou: bool) -> discord.Embed:
    embed = discord.Embed(
        title="🎛️ Gestion de ton vocal",
        description=(
            "Utilise les boutons ci-dessous pour personnaliser ton vocal "
            "(disponible seulement si le type le permet)."
        ),
        color=0xFFD700,
    )
    embed.add_field(name="Type", value=type_nom, inline=True)
    embed.add_field(name="Visibilité", value="🙈 Masqué" if masque else "👁️ Visible", inline=True)
    embed.add_field(name="Accès", value="🔒 Verrouillé" if verrou else "🔓 Ouvert", inline=True)
    return embed


class PanelVocalView(discord.ui.View):
    """Vue du panneau affiché dans chaque vocal temporaire.

    Les custom_id sont fixes pour rester utilisables après un redémarrage du bot
    (une instance par défaut est enregistrée comme vue persistante dans on_ready).
    À chaque envoi ou édition réelle, on reconstruit une instance avec l'état
    courant (masque/verrou) pour que les libellés des boutons restent corrects.
    """

    def __init__(self, masque: bool = False, verrou: bool = False):
        super().__init__(timeout=None)

        bouton_renommer = discord.ui.Button(
            label="Renommer", style=discord.ButtonStyle.primary, emoji="✏️",
            custom_id="panel_vocal_renommer",
        )
        bouton_renommer.callback = self.bouton_renommer
        self.add_item(bouton_renommer)

        bouton_limite = discord.ui.Button(
            label="Limite", style=discord.ButtonStyle.primary, emoji="👥",
            custom_id="panel_vocal_limite",
        )
        bouton_limite.callback = self.bouton_limite
        self.add_item(bouton_limite)

        bouton_masquer = discord.ui.Button(
            label="Afficher" if masque else "Masquer",
            style=discord.ButtonStyle.secondary,
            emoji="👁️" if masque else "🙈",
            custom_id="panel_vocal_masquer",
        )
        bouton_masquer.callback = self.bouton_masquer
        self.add_item(bouton_masquer)

        bouton_verrou = discord.ui.Button(
            label="Déverrouiller" if verrou else "Verrouiller",
            style=discord.ButtonStyle.danger if verrou else discord.ButtonStyle.secondary,
            emoji="🔓" if verrou else "🔒",
            custom_id="panel_vocal_verrou",
        )
        bouton_verrou.callback = self.bouton_verrou
        self.add_item(bouton_verrou)

    @staticmethod
    def _info(interaction: discord.Interaction):
        gconf = config_serveur(interaction.guild_id)
        return gconf, gconf["temp_channels"].get(str(interaction.channel_id))

    async def bouton_renommer(self, interaction: discord.Interaction):
        gconf, info = self._info(interaction)
        if not info:
            await interaction.response.send_message("❌ Ce salon n'est plus un vocal temporaire.", ephemeral=True)
            return
        if info["owner_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
            return
        type_info = gconf["types"].get(info["type"])
        if not type_info or not type_info.get("modifiable_nom"):
            await interaction.response.send_message("❌ Le nom de ce vocal ne peut pas être modifié.", ephemeral=True)
            return
        await interaction.response.send_modal(RenommerVocalModal(interaction.channel_id))

    async def bouton_limite(self, interaction: discord.Interaction):
        gconf, info = self._info(interaction)
        if not info:
            await interaction.response.send_message("❌ Ce salon n'est plus un vocal temporaire.", ephemeral=True)
            return
        if info["owner_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
            return
        type_info = gconf["types"].get(info["type"])
        if not type_info or not type_info.get("modifiable_limite"):
            await interaction.response.send_message("❌ La limite de ce vocal ne peut pas être modifiée.", ephemeral=True)
            return
        await interaction.response.send_modal(LimiteVocalModal(interaction.channel_id))

    async def bouton_masquer(self, interaction: discord.Interaction):
        gconf, info = self._info(interaction)
        if not info:
            await interaction.response.send_message("❌ Ce salon n'est plus un vocal temporaire.", ephemeral=True)
            return
        if info["owner_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
            return

        salon = interaction.channel
        nouvel_etat = not info.get("masque", False)
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.view_channel = False if nouvel_etat else None
        try:
            await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        except discord.HTTPException:
            await interaction.response.send_message("❌ Impossible de modifier les permissions du salon.", ephemeral=True)
            return

        info["masque"] = nouvel_etat
        sauvegarder_configuration()

        nouvelle_vue = PanelVocalView(masque=nouvel_etat, verrou=info.get("verrou", False))
        await interaction.response.edit_message(
            embed=embed_panel_vocal(info["type"], nouvel_etat, info.get("verrou", False)),
            view=nouvelle_vue,
        )

    async def bouton_verrou(self, interaction: discord.Interaction):
        gconf, info = self._info(interaction)
        if not info:
            await interaction.response.send_message("❌ Ce salon n'est plus un vocal temporaire.", ephemeral=True)
            return
        if info["owner_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Seul le créateur du vocal peut le modifier.", ephemeral=True)
            return

        salon = interaction.channel
        nouvel_etat = not info.get("verrou", False)
        overwrite = salon.overwrites_for(interaction.guild.default_role)
        overwrite.connect = False if nouvel_etat else None
        try:
            await salon.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        except discord.HTTPException:
            await interaction.response.send_message("❌ Impossible de modifier les permissions du salon.", ephemeral=True)
            return

        info["verrou"] = nouvel_etat
        sauvegarder_configuration()

        nouvelle_vue = PanelVocalView(masque=info.get("masque", False), verrou=nouvel_etat)
        await interaction.response.edit_message(
            embed=embed_panel_vocal(info["type"], info.get("masque", False), nouvel_etat),
            view=nouvelle_vue,
        )


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

    masque_initial = type_info.get("masque_defaut", False)

    # Le créateur garde toujours accès à son vocal, même s'il le masque ou le verrouille ensuite
    try:
        await nouveau_salon.set_permissions(membre, view_channel=True, connect=True)
    except discord.HTTPException:
        pass

    if masque_initial:
        try:
            await nouveau_salon.set_permissions(interaction.guild.default_role, view_channel=False)
        except discord.HTTPException:
            pass

    gconf["temp_channels"][str(nouveau_salon.id)] = {
        "owner_id": membre.id,
        "type": nom_type,
        "masque": masque_initial,
        "verrou": False,
    }
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

    try:
        await nouveau_salon.send(
            embed=embed_panel_vocal(nom_type, masque_initial, False),
            view=PanelVocalView(masque=masque_initial, verrou=False),
        )
    except discord.HTTPException:
        pass


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
        types_du_hub = gconf["hubs"][str(after.channel.id)].get("types", [])
        types_disponibles = {n: gconf["types"][n] for n in types_du_hub if n in gconf["types"]}

        if not types_disponibles:
            logging.warning(
                f"Hub {after.channel.id} rejoint par {member.id} mais aucun type de vocal "
                f"n'est disponible dans ce hub sur le serveur {member.guild.id} (utilise /vocal config)."
            )
            return  # aucun type disponible dans ce hub, on ne fait rien

        embed = discord.Embed(
            title="🎙️ Choisis ton type de vocal",
            description=(
                f"{member.mention}, sélectionne le type de vocal que tu veux créer ci-dessous.\n"
                f"⏱️ Tu as **{DUREE_CHOIX} secondes**, sinon tu seras déconnecté."
            ),
            color=0xFFD700,
        )
        view = ChoixTypeView(member, types_disponibles)
        try:
            msg = await after.channel.send(
                content=member.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )
            view.message = msg
        except discord.Forbidden:
            logging.warning(
                f"Permission refusée pour envoyer un message dans le hub {after.channel.id} "
                f"(serveur {member.guild.id}) — vérifie que le bot peut écrire dans ce salon vocal."
            )

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
#  GROUPE DE COMMANDES  /vocal ...
#  (toute la gestion des types/hubs passe désormais par /vocal config)
# ═══════════════════════════════════════════════════════════
groupe_vocal = app_commands.Group(name="vocal", description="Système de vocaux temporaires")


# ═══════════════════════════════════════════════════════════
#  PANNEAU DE CONFIGURATION INTERACTIF  —  /vocal config
# ═══════════════════════════════════════════════════════════
def embed_config(gconf: dict) -> discord.Embed:
    types_txt = "\n".join(
        f"🔊 **{n}** — limite {i['limite'] or '∞'} · nom {'✅' if i.get('modifiable_nom') else '❌'} · "
        f"limite {'✅' if i.get('modifiable_limite') else '❌'} · masqué par défaut {'✅' if i.get('masque_defaut') else '❌'}"
        for n, i in gconf["types"].items()
    ) or "_Aucun type créé_"
    hubs_txt = "\n".join(
        f"🎙️ <#{cid}> — {len(info.get('types', []))} type(s) disponible(s)"
        for cid, info in gconf["hubs"].items()
    ) or "_Aucun hub créé_"

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


# ── Étape : options du type (boutons oui/non), puis modal pour le texte ─
class TypeModal(discord.ui.Modal, title="Nouveau type de vocal"):
    nom = discord.ui.TextInput(label="Nom du type", placeholder="Duo", max_length=50)
    limite = discord.ui.TextInput(label="Limite de membres (0 = illimité)", default="0", max_length=2)
    format_nom = discord.ui.TextInput(
        label="Format du nom ({pseudo} et {type})",
        default="🔊 {type} de {pseudo}",
        max_length=100,
        required=False,
    )

    def __init__(
        self,
        guild_id: int,
        auteur_id: int,
        modifiable_nom: bool,
        modifiable_limite: bool,
        masque_defaut: bool,
    ):
        super().__init__()
        self.guild_id = guild_id
        self.auteur_id = auteur_id
        self.modifiable_nom = modifiable_nom
        self.modifiable_limite = modifiable_limite
        self.masque_defaut = masque_defaut

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

        format_val = self.format_nom.value.strip() or "🔊 {type} de {pseudo}"

        gconf["types"][nom_val] = {
            "limite": limite_val,
            "modifiable_nom": self.modifiable_nom,
            "modifiable_limite": self.modifiable_limite,
            "masque_defaut": self.masque_defaut,
            "format_nom": format_val,
        }
        sauvegarder_configuration()

        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class OptionsTypeView(VueBase):
    """Première étape de création d'un type : options oui/non par boutons.
    On ne peut pas tout mettre dans le modal (limite de 5 champs texte), donc
    les bascules oui/non sont réglées ici avant d'ouvrir le formulaire de texte."""

    def __init__(self, guild_id: int, auteur_id: int):
        super().__init__(guild_id, auteur_id, timeout=180)
        self.modifiable_nom = False
        self.modifiable_limite = False
        self.masque_defaut = False
        self._construire_boutons()

    def _construire_boutons(self):
        self.clear_items()

        bouton_nom = discord.ui.Button(
            label=f"Nom modifiable : {'Oui' if self.modifiable_nom else 'Non'}",
            style=discord.ButtonStyle.success if self.modifiable_nom else discord.ButtonStyle.secondary,
            emoji="✏️", row=0,
        )
        bouton_nom.callback = self._toggle_nom
        self.add_item(bouton_nom)

        bouton_limite = discord.ui.Button(
            label=f"Limite modifiable : {'Oui' if self.modifiable_limite else 'Non'}",
            style=discord.ButtonStyle.success if self.modifiable_limite else discord.ButtonStyle.secondary,
            emoji="👥", row=0,
        )
        bouton_limite.callback = self._toggle_limite
        self.add_item(bouton_limite)

        bouton_masque = discord.ui.Button(
            label=f"Masqué par défaut : {'Oui' if self.masque_defaut else 'Non'}",
            style=discord.ButtonStyle.success if self.masque_defaut else discord.ButtonStyle.secondary,
            emoji="🙈", row=1,
        )
        bouton_masque.callback = self._toggle_masque
        self.add_item(bouton_masque)

        bouton_continuer = discord.ui.Button(label="Continuer", style=discord.ButtonStyle.primary, emoji="➡️", row=2)
        bouton_continuer.callback = self._continuer
        self.add_item(bouton_continuer)

        bouton_annuler = discord.ui.Button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="✖️", row=2)
        bouton_annuler.callback = self._annuler
        self.add_item(bouton_annuler)

    async def _toggle_nom(self, interaction: discord.Interaction):
        self.modifiable_nom = not self.modifiable_nom
        self._construire_boutons()
        await interaction.response.edit_message(view=self)

    async def _toggle_limite(self, interaction: discord.Interaction):
        self.modifiable_limite = not self.modifiable_limite
        self._construire_boutons()
        await interaction.response.edit_message(view=self)

    async def _toggle_masque(self, interaction: discord.Interaction):
        self.masque_defaut = not self.masque_defaut
        self._construire_boutons()
        await interaction.response.edit_message(view=self)

    async def _continuer(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TypeModal(
                self.guild_id,
                self.auteur_id,
                self.modifiable_nom,
                self.modifiable_limite,
                self.masque_defaut,
            )
        )

    async def _annuler(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
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
        for hub_info in gconf["hubs"].values():
            if self.values[0] in hub_info.get("types", []):
                hub_info["types"].remove(self.values[0])
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

    def __init__(self, guild_id: int, auteur_id: int, categorie_id: int | None = None):
        super().__init__()
        self.guild_id = guild_id
        self.auteur_id = auteur_id
        self.categorie_id = categorie_id

    async def on_submit(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        categorie = interaction.guild.get_channel(self.categorie_id) if self.categorie_id else None
        salon = await interaction.guild.create_voice_channel(name=self.nom.value.strip()[:100], category=categorie)
        gconf["hubs"][str(salon.id)] = {"types": list(gconf["types"].keys())}
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

        gconf["hubs"][str(salon.id)] = {"types": list(gconf["types"].keys())}
        sauvegarder_configuration()

        vue = VueConfig(self.guild_id, self.view.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class SelectCategorieHub(discord.ui.ChannelSelect):
    """Choix de la catégorie du salon qui sera créé via le bouton 'Créer un nouveau salon'."""

    def __init__(self):
        super().__init__(
            placeholder="Catégorie du nouveau salon (optionnel)...",
            channel_types=[discord.ChannelType.category],
            min_values=1,
            max_values=1,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.categorie_id = self.values[0].id
        await interaction.response.send_message(
            f"📁 Catégorie sélectionnée : **{self.values[0].name}** (pour le prochain salon créé).",
            ephemeral=True,
        )


class VueNouveauHub(VueBase):
    def __init__(self, guild_id: int, auteur_id: int, guild: discord.Guild):
        super().__init__(guild_id, auteur_id)
        self.categorie_id: int | None = None
        self.add_item(SelectSalonExistant(guild_id))
        if guild.categories:
            self.add_item(SelectCategorieHub())

    @discord.ui.button(label="Créer un nouveau salon", style=discord.ButtonStyle.success, emoji="➕", row=2)
    async def nouveau_salon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(HubModal(self.guild_id, self.auteur_id, self.categorie_id))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, emoji="⬅️", row=2)
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
        gconf["hubs"].pop(self.values[0], None)
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


# ── Étape : types disponibles par hub (Select multi-valeurs) ───
class SelectTypesHub(discord.ui.Select):
    def __init__(self, guild_id: int, hub_id: str, gconf: dict):
        self.guild_id = guild_id
        self.hub_id = hub_id
        actuels = set(gconf["hubs"].get(hub_id, {}).get("types", []))
        options = [
            discord.SelectOption(label=n, value=n, emoji="🔊", default=(n in actuels))
            for n in gconf["types"]
        ][:25]
        super().__init__(
            placeholder="Choisis les types disponibles pour ce hub...",
            options=options,
            min_values=0,
            max_values=len(options) if options else 1,
        )

    async def callback(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        gconf["hubs"].setdefault(self.hub_id, {})["types"] = list(self.values)
        sauvegarder_configuration()
        vue = VueConfig(self.guild_id, self.view.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class VueTypesHub(VueBase):
    def __init__(self, guild_id: int, auteur_id: int, hub_id: str, gconf: dict):
        super().__init__(guild_id, auteur_id)
        self.hub_id = hub_id
        if gconf["types"]:
            self.add_item(SelectTypesHub(guild_id, hub_id, gconf))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def retour(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        vue = VueConfig(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(embed=embed_config(gconf), view=vue)
        vue.message = interaction.message


class SelectHubPourTypes(discord.ui.Select):
    def __init__(self, guild_id: int, gconf: dict, guild: discord.Guild):
        self.guild_id = guild_id
        options = []
        for cid in gconf["hubs"]:
            salon = guild.get_channel(int(cid))
            if salon:
                options.append(discord.SelectOption(label=salon.name, value=cid, emoji="🎙️"))
        super().__init__(placeholder="Choisis le hub à configurer...", options=options[:25], min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        gconf = config_serveur(self.guild_id)
        salon = interaction.guild.get_channel(int(self.values[0]))
        vue = VueTypesHub(self.guild_id, self.view.auteur_id, self.values[0], gconf)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"🔀 Types disponibles — {salon.name if salon else '#' + self.values[0]}",
                description=(
                    "Sélectionne les types de vocaux disponibles dans ce hub. "
                    "Les types non cochés n'apparaîtront pas dans le menu de ce hub."
                ),
                color=0xFFD700,
            ),
            view=vue,
        )
        vue.message = interaction.message


class VueChoixHubTypes(VueBase):
    def __init__(self, guild_id: int, auteur_id: int, gconf: dict, guild: discord.Guild):
        super().__init__(guild_id, auteur_id)
        self.add_item(SelectHubPourTypes(guild_id, gconf, guild))

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
        vue = OptionsTypeView(self.guild_id, self.auteur_id)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="➕ Nouveau type — options",
                description=(
                    "Règle les options ci-dessous, puis clique sur **Continuer** pour saisir "
                    "le nom, la limite et le format de nom du type."
                ),
                color=0xFFD700,
            ),
            view=vue,
        )
        vue.message = interaction.message

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
        vue = VueNouveauHub(self.guild_id, self.auteur_id, interaction.guild)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎙️ Nouveau hub",
                description=(
                    "Choisis un salon vocal existant à transformer, une catégorie pour le nouveau "
                    "salon (optionnel), ou crée-en un nouveau directement. Le nouveau hub reçoit "
                    "automatiquement tous les types existants — modifiable ensuite via **Types par hub**."
                ),
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

    @discord.ui.button(label="Types par hub", style=discord.ButtonStyle.primary, emoji="🔀", row=1)
    async def bouton_types_hub(self, interaction: discord.Interaction, button: discord.ui.Button):
        gconf = config_serveur(self.guild_id)
        if not gconf["hubs"]:
            await interaction.response.send_message("❌ Crée d'abord au moins un hub.", ephemeral=True)
            return
        if not gconf["types"]:
            await interaction.response.send_message("❌ Crée d'abord au moins un type de vocal.", ephemeral=True)
            return
        vue = VueChoixHubTypes(self.guild_id, self.auteur_id, gconf, interaction.guild)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🔀 Types par hub",
                description="Choisis le hub dont tu veux configurer les types disponibles.",
                color=0xFFD700,
            ),
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


# ── /vocal renommer et /vocal limite ────────────────────────
# Retirés : ces actions se font désormais via le panneau de boutons
# envoyé automatiquement dans chaque vocal temporaire créé.

# ═══════════════════════════════════════════════════════════
#  PANEL D'INVITATION
# ═══════════════════════════════════════════════════════════

class InviteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Inviter Beflow",
                emoji="<:love:1486416128254152826>",
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
            "créer/supprimer un type, créer/supprimer un hub, et choisir quels types sont "
            "disponibles dans chaque hub (**Types par hub**). Un formulaire s'ouvre pour les infos "
            "à saisir (nom, limite, si le nom et/ou la limite du vocal seront modifiables...), et un "
            "menu déroulant pour choisir un salon existant.\n\n"
            "**Permission requise :** Gérer les salons"
        ),
    },
    "types par hub": {
        "emoji": "🔀",
        "titre": "Types par hub",
        "categorie": "Staff",
        "desc": "Choisis quels types de vocaux sont proposés dans chaque hub.",
        "details": (
            "Un hub ne propose que les types qui lui sont explicitement assignés. Un nouveau hub "
            "reçoit tous les types existants au moment de sa création ; tu peux ensuite en retirer "
            "certains (par exemple pour garder un type de test uniquement disponible dans un hub "
            "privé, sans qu'il apparaisse dans les autres hubs)."
        ),
    },
    "panneau vocal": {
        "emoji": "🎛️",
        "titre": "Panneau dans ton vocal",
        "categorie": "Membres",
        "desc": "Gère ton vocal temporaire directement depuis ses boutons.",
        "details": (
            "Dès qu'un vocal temporaire est créé, un message avec des boutons apparaît dans son "
            "chat :\n"
            "**✏️ Renommer** et **👥 Limite** — utilisables seulement si le staff a autorisé cette "
            "modification pour ce type de vocal (réglable indépendamment via `/vocal config`).\n"
            "**🙈 Masquer / 👁️ Afficher** — cache le vocal pour tout le monde sauf toi.\n"
            "**🔒 Verrouiller / 🔓 Déverrouiller** — empêche quiconque de te rejoindre (sans "
            "déconnecter les membres déjà présents).\n\n"
            "Ces deux derniers boutons sont utilisables uniquement par le créateur du vocal."
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
            "`/vocal config` — ⭐ Panneau interactif tout-en-un (types & hubs)\n"
            "🔀 Types par hub — choisir quels types apparaissent dans chaque hub"
        ),
        inline=False,
    )
    embed.add_field(
        name="👤 Membres",
        value="🎛️ Un panneau de boutons (renommer / limite / masquer / verrouiller) apparaît directement dans chaque vocal créé.",
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
            title="<a:r2:1485268957664383038> Beflow",
            description=(
                "Salut ! Je suis **Beflow**.\n\n"
                "Je crée automatiquement des **vocaux temporaires** entièrement configurables.\n\n"
                "Clique sur le bouton ci-dessous pour m'ajouter à ton serveur."
            ),
            color=0x5865F2,
        )

        embed.add_field(
            name="<a:mangerr:1485359165516939356> Fonctionnalités",
            value=(
                "<a:ar:1485250353854288035> Vocaux temporaires\n"
                "<a:ar:1485250353854288035> Types de salons\n"
                "<a:ar:1485250353854288035> Hubs\n"
                "<a:ar:1485250353854288035> Configuration interactive\n"
                "<a:ar:1485250353854288035> Gestion des vocs"
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

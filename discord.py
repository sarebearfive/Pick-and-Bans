pip install -U discord.py
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = "MTM5OTU1Njg2NDI2OTg3NzM0MA.G-NCs8.wX3RNsLT4cMNOfyQYHiT6p3ftMTY40MKrLQtMg"

MAP_POOL = [
    "Abyss", "Ascent", "Bind", "Corrode", "Fracture",
    "Haven", "Icebox", "Lotus", "Pearl", "Split", "Sunset"
]

TURN_ORDER = [
    ("Ban", 0), ("Ban", 1), 
    ("Pick", 0), ("Pick", 1), 
    ("Ban", 0), ("Ban", 1), 
    ("Ban", 0), ("Ban", 1), 
    ("Ban", 0)
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

sessions = {}

class PickBanSession:
    def __init__(self, player1, player2):
        self.players = [player1, player2]
        self.maps = MAP_POOL.copy()
        self.picks = []
        self.bans = []
        self.turn = 0

    def is_map_available(self, map_name):
        return map_name in self.maps and map_name not in self.picks and map_name not in self.bans

    def current_turn(self):
        return TURN_ORDER[self.turn] if self.turn < len(TURN_ORDER) else None

    def make_choice(self, action, player, map_name):
        expected_action, player_index = self.current_turn()
        if player != self.players[player_index] or action != expected_action:
            return False, f"It is {expected_action} turn for {self.players[player_index].mention}."
        if not self.is_map_available(map_name):
            return False, f"{map_name} is not a valid choice."

        if action == "Pick":
            self.picks.append(map_name)
        else:
            self.bans.append(map_name)

        self.turn += 1
        return True, None

    def remaining_map(self):
        return list(set(self.maps) - set(self.picks) - set(self.bans))[0]

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot is online as {bot.user}")

@tree.command(name="start_pickban", description="Start a map pick/ban session between two players")
@app_commands.describe(player1="First player", player2="Second player")
async def start_pickban(interaction: discord.Interaction, player1: discord.Member, player2: discord.Member):
    channel_id = interaction.channel.id
    if channel_id in sessions:
        await interaction.response.send_message("A session is already running in this channel.", ephemeral=True)
        return

    sessions[channel_id] = PickBanSession(player1, player2)
    await interaction.response.send_message(f"🎮 Pick/Ban started between {player1.mention} and {player2.mention}.")
    await prompt_next_turn(interaction)

async def prompt_next_turn(interaction):
    session = sessions[interaction.channel.id]
    if session.turn >= len(TURN_ORDER):
        decider = session.remaining_map()
        await interaction.followup.send(
            f"✅ **Pick/Ban Complete!**\n"
            f"**Picks:** {', '.join(session.picks)}\n"
            f"**Bans:** {', '.join(session.bans)}\n"
            f"**Decider Map:** {decider}"
        )
        del sessions[interaction.channel.id]
        return

    action, player_index = TURN_ORDER[session.turn]
    player = session.players[player_index]
    available = [m for m in session.maps if m not in session.picks and m not in session.bans]
    await interaction.followup.send(f"**Turn {session.turn + 1}: {action}** - {player.mention}, choose one of: {', '.join(available)}")

@tree.command(name="pick", description="Pick a map")
@app_commands.describe(map_name="Name of the map to pick")
async def pick(interaction: discord.Interaction, map_name: str):
    await handle_choice(interaction, "Pick", map_name.title())

@tree.command(name="ban", description="Ban a map")
@app_commands.describe(map_name="Name of the map to ban")
async def ban(interaction: discord.Interaction, map_name: str):
    await handle_choice(interaction, "Ban", map_name.title())

async def handle_choice(interaction: discord.Interaction, action, map_name):
    channel_id = interaction.channel.id
    if channel_id not in sessions:
        await interaction.response.send_message("No active session. Use /start_pickban to begin.", ephemeral=True)
        return

    session = sessions[channel_id]
    success, error = session.make_choice(action, interaction.user, map_name)
    if not success:
        await interaction.response.send_message(error, ephemeral=True)
        return

    await interaction.response.send_message(f"✅ {action} confirmed: **{map_name}** by {interaction.user.mention}")
    await prompt_next_turn(interaction)

@tree.command(name="cancel_pickban", description="Cancel the current pick/ban session")
async def cancel_pickban(interaction: discord.Interaction):
    if interaction.channel.id in sessions:
        del sessions[interaction.channel.id]
        await interaction.response.send_message("Pick/ban session canceled.")
    else:
        await interaction.response.send_message("No session to cancel.")

bot.run(TOKEN)
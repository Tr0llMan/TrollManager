import discord
from discord.ext import tasks, commands
from discord import app_commands
from googleapiclient.discovery import build
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Twitch API Configuration
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_NOTIFICATION_CHANNEL_ID = int(os.getenv("DISCORD_NOTIFICATION_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
DYNAMIC_CATEGORY_ID = int(os.getenv("DYNAMIC_CATEGORY_ID"))

# Parameterized Configurations
YOUTUBE_CONFIG = {
    "channel_id": os.getenv("YOUTUBE_CHANNEL_ID"),
    "roles": {
        "Overwatch 2": "<@&1293619010897969184>",  # Overwatch Role
        "Minecraft": "<@&1311374496405393439>",  # Minecraft Role
        "Roblox": "<@&1293619104627953704>",  # Roblox Role
        "Dev Log": "<@&1311378340564959354>",  # Dev Log Role
        "Warzone": "<@&1293619059568541747>",  # Warzone Role
        "default": "<@&1311377083313950730>",  # Default YouTube Role
    },
}

TWITCH_CONFIG = {
    "streamers": {
        "Tr0lIMan": "<@&1311374441649012847>",  # Twitch Role for Tr0lIMan
    }
}

DYNAMIC_VC_CONFIG = {
    "triggers": {
        1206542741778210896: 1098638128643846144,  # General Trigger
        1206543008263045150: 1293619059568541747,  # Warzone Trigger
        1206543033823400007: 1293619010897969184,  # Overwatch Trigger
        1293626844360474664: 1293619104627953704,  # Roblox Trigger
        1311375381369978992: 1311374496405393439,  # Minecraft Trigger
    },
    "max_inactive_time": 300,  # Default: 5 minutes
}

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global State
dynamic_vcs = {}
vc_counters = {}
last_video_id = None
is_twitch_live = False


# Helper Functions
async def get_twitch_access_token():
    """Authenticate with Twitch API and get an access token."""
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as response:
            data = await response.json()
            return data.get("access_token")


async def check_twitch_streams():
    """Check if Twitch users are live."""
    global is_twitch_live
    access_token = await get_twitch_access_token()
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }
    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            streams = data.get("data", [])
            if streams:
                if not is_twitch_live:
                    is_twitch_live = True
                    stream_title = streams[0]["title"]
                    stream_url = f"https://www.twitch.tv/{TWITCH_USERNAME}"
                    role = TWITCH_CONFIG["streamers"].get(TWITCH_USERNAME, "")
                    message = f"🔴 **{TWITCH_USERNAME} is now live on Twitch! {role}**\n**Title:** {stream_title}\nWatch here: {stream_url}"
                    channel = bot.get_channel(DISCORD_NOTIFICATION_CHANNEL_ID)
                    if channel:
                        await channel.send(message)
            else:
                is_twitch_live = False


async def get_latest_video(channel_id):
    """Fetch the latest video or stream from a YouTube channel."""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"part=snippet&channelId={channel_id}&maxResults=1&order=date&type=video&key={YOUTUBE_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if "items" in data and len(data["items"]) > 0:
                video = data["items"][0]
                video_title = video["snippet"]["title"]
                video_id = video["id"]["videoId"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                live_broadcast_content = video["snippet"].get("liveBroadcastContent", "none")
                return video_id, video_title, video_url, live_broadcast_content
            else:
                return None, None, None, None


def generate_custom_message(video_title, video_url):
    """Generate a custom message based on the video title."""
    for keyword, role in YOUTUBE_CONFIG["roles"].items():
        if keyword in video_title:
            return f"🎮 **New {keyword} video is out {role}!**\nCheck it out: {video_url}"
    return f"🎥 **New video uploaded:** **{video_title}** {YOUTUBE_CONFIG['roles']['default']}\nWatch here: {video_url}"


# Scheduled Tasks
@tasks.loop(minutes=5)
async def check_new_video_and_streams():
    global last_video_id
    # Check YouTube
    video_id, video_title, video_url, live_broadcast_content = await get_latest_video(YOUTUBE_CONFIG["channel_id"])
    if video_id and video_id != last_video_id:
        last_video_id = video_id
        if live_broadcast_content == "live":
            message = f"🔴 **Live Stream Alert!** {video_title}\nWatch here: {video_url}"
        else:
            message = generate_custom_message(video_title, video_url)
        channel = bot.get_channel(DISCORD_NOTIFICATION_CHANNEL_ID)
        if channel:
            await channel.send(message)
    # Check Twitch
    await check_twitch_streams()


@tree.command(name="set_dynamicvc", description="Configure dynamic voice channels.")
@app_commands.describe(
    host_category="The host category for trigger channels.",
    dynamic_category="The dynamic category where new VCs will be created.",
    vc_ids="Comma-separated list of trigger VC IDs.",
    roles="Comma-separated list of associated roles (must match VC IDs).",
)
async def set_dynamicvc(
    interaction: discord.Interaction,
    host_category: discord.CategoryChannel,
    dynamic_category: discord.CategoryChannel,
    vc_ids: str,
    roles: str,
):
    """Configure dynamic voice channels."""
    global DYNAMIC_CATEGORY_ID
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    # Parse VC IDs and Roles
    vc_id_list = [int(vc_id.strip()) for vc_id in vc_ids.split(",")]
    role_id_list = [int(role_id.strip()) for role_id in roles.split(",")]

    if len(vc_id_list) != len(role_id_list):
        await interaction.response.send_message(
            "The number of VC IDs and Roles must match.", ephemeral=True
        )
        return

    # Update Dynamic VC Config
    for vc_id, role_id in zip(vc_id_list, role_id_list):
        DYNAMIC_VC_CONFIG["triggers"][vc_id] = role_id

    # Update global dynamic category ID
    DYNAMIC_CATEGORY_ID = dynamic_category.id

    # Confirm the configuration
    response = (
        f"Dynamic VC configuration updated!\n\n"
        f"**Host Category:** {host_category.name}\n"
        f"**Dynamic Category:** {dynamic_category.name}\n"
        f"**Trigger VC IDs and Roles:**\n" +
        "\n".join([f"VC ID: {vc_id}, Role ID: {role_id}" for vc_id, role_id in zip(vc_id_list, role_id_list)])
    )
    await interaction.response.send_message(response, ephemeral=True)


@tree.command(name="read_config", description="Read the current bot configuration.")
async def read_config(interaction: discord.Interaction):
    """Display the current configurations."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    dynamic_vcs_config = "\n".join(
        [f"VC ID: {trigger}, Role ID: {role}" for trigger, role in DYNAMIC_VC_CONFIG["triggers"].items()]
    )
    twitch_config = "\n".join([f"{streamer}: {role}" for streamer, role in TWITCH_CONFIG["streamers"].items()])
    youtube_config = f"Channel ID: {YOUTUBE_CONFIG['channel_id']}\nRoles:\n" + \
                     "\n".join([f"{keyword}: {role}" for keyword, role in YOUTUBE_CONFIG["roles"].items()])

    response = (
        f"**Current Bot Configuration:**\n\n"
        f"**Dynamic VCs:**\n{dynamic_vcs_config}\n\n"
        f"**Twitch Streamers:**\n{twitch_config}\n\n"
        f"**YouTube Notifications:**\n{youtube_config}"
    )
    await interaction.response.send_message(f"```{response}```", ephemeral=True)


@tree.command(name="set_inactivity_time", description="Set the maximum inactivity time for dynamic VCs.")
@app_commands.describe(time="Maximum inactivity time in seconds.")
async def set_inactivity_time(interaction: discord.Interaction, time: int):
    """Set the inactivity timeout for dynamic VCs."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    DYNAMIC_VC_CONFIG["max_inactive_time"] = time
    await interaction.response.send_message(
        f"Inactivity timeout for dynamic VCs has been updated to {time} seconds.", ephemeral=True
    )


@tree.command(name="add_streamer", description="Add a Twitch streamer for notifications.")
@app_commands.describe(username="Twitch username.", role="Role ID for notifications.")
async def add_streamer(interaction: discord.Interaction, username: str, role: str):
    """Add a Twitch streamer."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    TWITCH_CONFIG["streamers"][username] = role
    await interaction.response.send_message(
        f"Twitch streamer '{username}' added with notifications for role {role}.", ephemeral=True
    )


@tree.command(name="add_youtube", description="Add a YouTube keyword and associated role.")
@app_commands.describe(keyword="Keyword to look for in video titles.", role="Role ID for notifications.")
async def add_youtube(interaction: discord.Interaction, keyword: str, role: str):
    """Add a YouTube keyword for notifications."""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return

    YOUTUBE_CONFIG["roles"][keyword] = role
    await interaction.response.send_message(
        f"Keyword '{keyword}' added for YouTube notifications with role {role}.", ephemeral=True
    )


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name}")
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    check_new_video_and_streams.start()


@bot.event
async def on_voice_state_update(member, before, after):
    """Handle dynamic VC creation."""
    if after.channel and after.channel.id in DYNAMIC_VC_CONFIG["triggers"]:
        dynamic_category_id = DYNAMIC_VC_CONFIG["triggers"][after.channel.id]
        guild = bot.get_guild(GUILD_ID)
        dynamic_category = discord.utils.get(guild.categories, id=dynamic_category_id)

        # Different VC naming for General Trigger
        if after.channel.id == 1206542741778210896:  # General Trigger ID
            vc_name = f"{member.display_name}-VC"
        else:
            role_id = DYNAMIC_VC_CONFIG["triggers"][after.channel.id]
            role = discord.utils.get(guild.roles, id=role_id)
            vc_name = f"{role.name}-{vc_counters.get(after.channel.id, 1)}"
            vc_counters[after.channel.id] = vc_counters.get(after.channel.id, 1) + 1

        # Create and move member to the new VC
        new_vc = await guild.create_voice_channel(name=vc_name, category=dynamic_category)
        await member.move_to(new_vc)
        dynamic_vcs[new_vc.id] = new_vc.id
        await asyncio.create_task(delete_empty_vc(new_vc.id))


async def delete_empty_vc(vc_id):
    """Delete a VC if it is empty after checking every minute for up to 5 minutes."""
    for _ in range(DYNAMIC_VC_CONFIG["max_inactive_time"] // 60):
        await asyncio.sleep(60)
        guild = bot.get_guild(GUILD_ID)
        vc = guild.get_channel(vc_id)
        if vc and len(vc.members) == 0:
            await vc.delete()
            dynamic_vcs.pop(vc_id, None)
            return


bot.run(DISCORD_BOT_TOKEN)

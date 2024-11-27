import discord
from discord.ext import tasks
from googleapiclient.discovery import build
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve variables with corrected names
YOUTUBE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
DISCORD_NOTIFICATION_CHANNEL_ID = int(os.getenv("DISCORD_NOTIFICATION_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
DYNAMIC_CATEGORY_ID = int(os.getenv("DYNAMIC_CATEGORY_ID"))

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)

# Mapping of trigger channels to roles and categories
TRIGGER_CHANNELS = {
    # Normal VC
    "<#1206542741778210896>": "@everyone",
    "<#1206543008263045150>": "<@&1293619059568541747>",
    # Overwatch VC
    "<#1206543033823400007>": "<@&1293619010897969184>",
    # Roblox VC
    "<#1293626844360474664>": "<@&1293619104627953704>",
    # Minecraft VC
    "<#1311375381369978992>": "<@&1311374496405393439>",
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ]
)

# Create the bot
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True  # Needed for voice channel and role management
bot = discord.Client(intents=intents)

# Track dynamically created VCs and their expiration timers
dynamic_vcs = {}
vc_counters = {key: 1 for key in TRIGGER_CHANNELS.keys()}  # Counter for VC numbering
last_video_id = None  # Track the last posted YouTube video ID


async def get_latest_video(channel_id):
    """Fetch the latest video or stream from a YouTube channel."""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"part=snippet&channelId={channel_id}&maxResults=1&order=date&type=video&key={YOUTUBE_API_KEY}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                if response.status != 200:
                    logging.error(f"Error fetching video: {data}")
                    return None, None, None, None

                if "items" in data and len(data["items"]) > 0:
                    video = data["items"][0]
                    video_title = video["snippet"]["title"]
                    video_id = video["id"]["videoId"]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    # Extract the liveBroadcastContent field
                    live_broadcast_content = video["snippet"].get("liveBroadcastContent", "none")
                    return video_id, video_title, video_url, live_broadcast_content
                else:
                    logging.warning("No videos found for the channel.")
                    return None, None, None, None
    except Exception as e:
        logging.error(f"Error fetching video: {e}")
        return None, None, None, None


def generate_custom_message(video_title, video_url):
    """Generate a custom message based on the video title."""
    if "Overwatch 2" in video_title:
        return f"🎮 A new Overwatch 2 video is out <@&1293619010897969184>! Check it out: {video_url}"
    elif "Minecraft" in video_title:
        return f"🌍 A new Minecraft adventure awaits <@&1311374496405393439>! Watch here: {video_url}"
    elif "Roblox" in video_title:
        return f"🤖 A new Roblox video is out <@&1293619104627953704>! Check it out: {video_url}"
    elif "Dev Log" in video_title:
        return f"📓 A new Dev Log has been released <@&1311378340564959354>! Check it out: {video_url}"
    elif "Warzone" in video_title:
        return f"🔫 A new Warzone video got posted <@&1293619059568541747>! Show us some love: {video_url}"
    else:
        return f"New video uploaded <@&1311377083313950730>!: **{video_title}**\nWatch here: {video_url}"


async def delete_empty_vc(vc_id):
    """Checks every minute if a VC is empty, then deletes it if so."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        guild = bot.get_guild(GUILD_ID)
        vc = guild.get_channel(vc_id)
        if vc and len(vc.members) == 0:
            logging.info(f"Deleting empty VC: {vc.name}")
            await vc.delete()
            dynamic_vcs.pop(vc_id, None)
            break



# Bot Events
@bot.event
async def on_ready():
    """Triggered when the bot connects to Discord."""
    logging.info(f"Logged in as {bot.user.name}")
    check_new_video.start()  # Start the YouTube monitoring task


@bot.event
async def on_voice_state_update(member, before, after):
    """
    Triggered when a user's voice state changes (e.g., joining/leaving a VC).
    Handles dynamic VC creation and monitoring.
    """
    guild = bot.get_guild(GUILD_ID)

    # Check if the user joined one of the trigger channels
    if after.channel and after.channel.name in TRIGGER_CHANNELS:
        role_name = TRIGGER_CHANNELS[after.channel.name]  # Get the role name
        role = discord.utils.get(guild.roles, name=role_name)  # Find the corresponding role

        if not role:
            logging.warning(f"Role '{role_name}' not found in guild.")
            return

        # Generate a unique VC name
        category_name = after.channel.name.split("-")[1]
        vc_name = f"{category_name}-VC-{vc_counters[after.channel.name]}"
        vc_counters[after.channel.name] += 1

        # Create a new VC under the specified category
        category = discord.utils.get(guild.categories, id=DYNAMIC_CATEGORY_ID)
        if not category:
            logging.warning(f"Category with ID {DYNAMIC_CATEGORY_ID} not found.")
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),  # Default: no access
            role: discord.PermissionOverwrite(connect=True),  # Role: access
        }

        new_vc = await guild.create_voice_channel(name=vc_name, category=category, overwrites=overwrites)
        dynamic_vcs[new_vc.id] = new_vc  # Track the VC
        logging.info(f"Created new VC: {vc_name}")

        # Move the user to the newly created VC
        await member.move_to(new_vc)
        logging.info(f"Moved {member.display_name} to {vc_name}")

        # Schedule VC deletion after 5 minutes of inactivity
        await asyncio.create_task(delete_empty_vc(new_vc.id))

    # Check if the user left a dynamic VC
    if before.channel and before.channel.id in dynamic_vcs:
        vc_id = before.channel.id
        vc = dynamic_vcs[vc_id]
        if len(vc.members) == 0:  # If the VC is empty
            logging.info(f"VC {vc.name} is empty. Scheduling deletion.")
            await asyncio.create_task(delete_empty_vc(vc_id))


@bot.event
async def on_guild_channel_delete(channel):
    """
    Triggered when a channel is deleted.
    Cleans up the `dynamic_vcs` dictionary.
    """
    if channel.id in dynamic_vcs:
        logging.info(f"VC {channel.name} was manually deleted.")
        dynamic_vcs.pop(channel.id, None)


# Background Tasks
@tasks.loop(minutes=5)
async def check_new_video():
    """Periodically checks for new videos or live streams and posts updates."""
    global last_video_id

    video_id, video_title, video_url, live_broadcast_content = await get_latest_video(YOUTUBE_CHANNEL_ID)

    if video_id and video_id != last_video_id:
        last_video_id = video_id  # Update the last video ID
        logging.info(f"New content detected: {video_title} ({live_broadcast_content})")

        # Determine the type of message based on content type
        if live_broadcast_content == "live":
            message = f"🔴 **Live Stream Alert <@&1311374441649012847>!** {video_title}\nWatch here: {video_url}"
        elif live_broadcast_content == "upcoming":
            message = f"📅 **Upcoming Live Stream <@&1311374441649012847>!** {video_title}\nWatch here: {video_url}"
        else:
            message = generate_custom_message(video_title, video_url)  # Use the existing video message logic

        # Post the message in the notification channel
        channel = bot.get_channel(DISCORD_NOTIFICATION_CHANNEL_ID)
        if channel:
            await channel.send(message)
            logging.info(f"Posted update in channel {DISCORD_NOTIFICATION_CHANNEL_ID}: {message}")
        else:
            logging.error(f"Failed to fetch Discord channel with ID {DISCORD_NOTIFICATION_CHANNEL_ID}")


@check_new_video.before_loop
async def before_check_new_video():
    """Wait until the bot is ready before starting the task."""
    await bot.wait_until_ready()

# Run the bot
bot.run(DISCORD_BOT_TOKEN)

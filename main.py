import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import asyncio
import logging
import os
from typing import Optional
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask setup for UptimeRobot
FLASK_AVAILABLE = False
try:
    from flask import Flask
    FLASK_AVAILABLE = True
    logger.info("Flask available - web server enabled")
except ImportError:
    logger.info("Flask not installed. Web server disabled. Install with: pip install flask")

# Bot token from environment variables
BOT_TOKEN = None
for token_var in ['DISCORD_TOKEN', 'BOT_TOKEN', 'TOKEN']:
    token = os.getenv(token_var)
    if token and token != "YOUR_BOT_TOKEN_HERE":
        BOT_TOKEN = token
        logger.info(f"Bot token found from {token_var}")
        break

if not BOT_TOKEN:
    logger.error("No valid bot token found in environment variables!")
    logger.error("Please set one of: DISCORD_TOKEN, BOT_TOKEN, or TOKEN")

# Configuration
ADMIN_ROLE_ID = 1410911675351306250
LOG_CHANNEL_ID = 1411664747958501429
PORT = int(os.getenv("PORT", 3000))

# Bot setup with timeout configurations
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix='!', 
    intents=intents,
    heartbeat_timeout=60.0,
    chunk_guilds_at_startup=False
)

# Data storage
user_data = {}

# Flask app for UptimeRobot
if FLASK_AVAILABLE:
    app = Flask(__name__)
    flask_started = False
    
    @app.route('/')
    def home():
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Discord Bot Status</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status-online {{ color: #28a745; }}
                .status-offline {{ color: #dc3545; }}
                h1 {{ color: #343a40; }}
                p {{ margin: 10px 0; font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Discord Bot Status</h1>
                <p><strong>Bot Status:</strong> <span class="{'status-online' if bot.is_ready() else 'status-offline'}">{['Online', 'Offline'][not bot.is_ready()]}</span></p>
                <p><strong>Bot User:</strong> {bot.user if bot.user else 'Not connected'}</p>
                <p><strong>Guilds:</strong> {len(bot.guilds) if bot.is_ready() else 'N/A'}</p>
                <p><strong>Users in Database:</strong> {len(user_data)}</p>
                <p><strong>Uptime:</strong> Bot is running</p>
                <p><strong>Server Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Platform:</strong> Railway</p>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/health')
    def health():
        return {
            'status': 'healthy', 
            'bot_ready': bot.is_ready(), 
            'timestamp': datetime.now().isoformat(),
            'guilds': len(bot.guilds) if bot.is_ready() else 0,
            'users_in_db': len(user_data)
        }, 200
    
    @app.route('/ping')
    def ping():
        return 'pong'
    
    @app.route('/status')
    def status():
        return {
            'online': bot.is_ready(),
            'user': str(bot.user) if bot.user else None,
            'guilds': len(bot.guilds) if bot.is_ready() else 0
        }
    
    def start_flask_server():
        global flask_started
        if flask_started:
            return
        flask_started = True
        try:
            logger.info(f"Starting Flask server on 0.0.0.0:{PORT}")
            app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logger.error(f"Flask server error: {e}")
            import traceback
            traceback.print_exc()

def save_data():
    try:
        with open('roblox_data.json', 'w') as f:
            json.dump(user_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def load_data():
    global user_data
    try:
        with open('roblox_data.json', 'r') as f:
            user_data = json.load(f)
        logger.info(f"Loaded data for {len(user_data)} users")
    except FileNotFoundError:
        logger.info("No existing data file found, starting fresh")
        user_data = {}
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        user_data = {}

@bot.event
async def on_ready():
    logger.info(f'Bot online: {bot.user} (ID: {bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    logger.info(f'Bot is ready and operational!')
    load_data()
    
    # Add retry logic for command sync
    max_retries = 3
    for attempt in range(max_retries):
        try:
            synced = await bot.tree.sync()
            logger.info(f'Synced {len(synced)} slash commands')
            break
        except Exception as e:
            logger.error(f'Sync attempt {attempt + 1} failed: {e}')
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                logger.error("Failed to sync commands after all retries")

@bot.event
async def on_disconnect():
    logger.warning("Bot disconnected from Discord")

@bot.event
async def on_resumed():
    logger.info("Bot reconnected to Discord")

def is_admin(interaction):
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)

async def update_or_create_log_message(user_id, username, timestamp, set_by_admin=False, admin_user=None):
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.warning(f"Could not find log channel with ID {LOG_CHANNEL_ID}")
            return

        # Look for existing message for this user
        existing_message = None
        async for message in channel.history(limit=100):
            if (message.author == bot.user and 
                message.embeds and 
                len(message.embeds) > 0 and
                message.embeds[0].title == "🎮 Roblox Username Set" and
                message.embeds[0].description and
                f"<@{user_id}>" in message.embeds[0].description):
                
                existing_message = message
                break

        # Create the embed
        embed = discord.Embed(
            title="🎮 Roblox Username Set",
            description=f"<@{user_id}>",
            color=0x00b2ff
        )
        embed.add_field(name="🔗 Roblox Username:", value=f"**{username}**", inline=False)
        embed.add_field(name="⏰ Set At:", value=f"<t:{timestamp}:R>", inline=False)
        
        if set_by_admin and admin_user:
            embed.set_footer(text=f"Set by {admin_user.display_name} (Admin)")

        # Update existing message or create new one
        if existing_message:
            await asyncio.wait_for(existing_message.edit(embed=embed), timeout=15.0)
            logger.info(f"Updated existing log message for user {user_id}")
        else:
            await asyncio.wait_for(channel.send(embed=embed), timeout=15.0)
            logger.info(f"Created new log message for user {user_id}")
                
    except asyncio.TimeoutError:
        logger.error("Timeout while updating log message")
    except Exception as e:
        logger.error(f"Error updating log message: {e}")

@bot.tree.command(name="roblox", description="Set your Roblox username (3 hour cooldown)")
async def roblox_command(interaction: discord.Interaction, username: str):
    user_id = str(interaction.user.id)
    now = datetime.now()

    logger.info(f"Command called by {interaction.user} ({user_id}) at {now}")

    # Validate username (basic validation)
    if len(username) > 20 or len(username) < 3:
        embed = discord.Embed(
            title="Invalid Username",
            description="❌ Roblox usernames must be between 3-20 characters",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check cooldown
    if user_id in user_data:
        last_used_str = user_data[user_id].get('last_used')
        if last_used_str:
            try:
                last_used = datetime.fromisoformat(last_used_str)
                time_diff = now - last_used

                logger.info(f"Last used: {last_used}, Time difference: {time_diff}")

                if time_diff < timedelta(hours=3):
                    # Calculate when they can use it again
                    next_available_time = last_used + timedelta(hours=3)
                    next_available_timestamp = int(next_available_time.timestamp())

                    embed = discord.Embed(
                        title="Cooldown Active",
                        description=f"⏰ You can change your username again <t:{next_available_timestamp}:R>",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logger.info(f"User blocked - cooldown until {next_available_time}")
                    return
            except Exception as e:
                logger.error(f"Error parsing timestamp: {e}")

    logger.info("User allowed to proceed")

    # Send initial response first
    next_available = int((now + timedelta(hours=3)).timestamp())
    embed = discord.Embed(
        description=f"✅ Roblox username set to **{username}**\n\n⏰ Next change available <t:{next_available}:R>",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Update data
    user_data[user_id] = {
        'username': username,
        'last_used': now.isoformat(),
        'set_by': 'self'
    }

    if save_data():
        logger.info(f"Data saved for user {user_id}")
    else:
        logger.error(f"Failed to save data for user {user_id}")

    # Update or create log message
    timestamp = int(now.timestamp())
    await update_or_create_log_message(interaction.user.id, username, timestamp)

    logger.info("Command completed successfully")

@bot.tree.command(name="manroblox", description="Admin: Set user's Roblox username (No cooldown)")
async def manroblox_command(interaction: discord.Interaction, user: discord.Member, robloxusername: str):
    if not is_admin(interaction):
        embed = discord.Embed(
            description="❌ Admin only command",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    logger.info(f"Admin command by {interaction.user} ({interaction.user.id}) for user {user} ({user.id})")

    # Validate username (basic validation)
    if len(robloxusername) > 20 or len(robloxusername) < 3:
        embed = discord.Embed(
            title="Invalid Username",
            description="❌ Roblox usernames must be between 3-20 characters",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Send initial response first
    embed = discord.Embed(
        description=f"✅ Set {user.mention}'s username to **{robloxusername}**",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Update data
    user_data[str(user.id)] = {
        'username': robloxusername,
        'last_used': datetime.now().isoformat(),
        'set_by': str(interaction.user.id)
    }

    if save_data():
        logger.info(f"Data saved for user {user.id}")
    else:
        logger.error(f"Failed to save data for user {user.id}")

    # Update or create log message
    admin_timestamp = int(datetime.now().timestamp())
    await update_or_create_log_message(user.id, robloxusername, admin_timestamp, set_by_admin=True, admin_user=interaction.user)

    logger.info("Admin command completed successfully")

@bot.tree.command(name="getroblox", description="Get a user's Roblox username")
async def getroblox_command(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    target_user = user or interaction.user
    user_id = str(target_user.id)
    
    if user_id not in user_data:
        embed = discord.Embed(
            description=f"❌ No Roblox username found for {target_user.mention}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    username = user_data[user_id]['username']
    set_time = user_data[user_id].get('last_used', 'Unknown')
    
    try:
        if set_time != 'Unknown':
            set_datetime = datetime.fromisoformat(set_time)
            timestamp = int(set_datetime.timestamp())
            time_display = f"<t:{timestamp}:R>"
        else:
            time_display = "Unknown"
    except ValueError:
        time_display = "Unknown"
    
    embed = discord.Embed(
        title="🎮 Roblox Username",
        description=f"**User:** {target_user.mention}\n**Username:** {username}\n**Set:** {time_display}",
        color=0x00b2ff
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Enhanced error handling
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    logger.error(f"Slash command error: {error}")
    if not interaction.response.is_done():
        embed = discord.Embed(
            description="❌ An error occurred while processing this command",
            color=0xff0000
        )
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Bot error in {event}: {args}")

# Add reconnect logic
async def run_bot_with_reconnect():
    """Run bot with automatic reconnection logic"""
    max_retries = 5
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting bot (attempt {attempt + 1}/{max_retries})...")
            await bot.start(BOT_TOKEN)
        except (discord.ConnectionClosed, discord.HTTPException, asyncio.TimeoutError) as e:
            logger.error(f"Connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Max retries reached. Bot shutting down.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

def main():
    if not BOT_TOKEN:
        logger.error("ERROR: No bot token found!")
        logger.error("Please set DISCORD_TOKEN environment variable in Railway")
        return

    logger.info("Starting Discord Roblox Bot...")
    logger.info(f"Port: {PORT}")
    
    if not FLASK_AVAILABLE:
        logger.warning("Flask not available. Web server disabled.")
        logger.warning("Install Flask with: pip install flask")
    else:
        # Start Flask server in a separate thread
        logger.info("Starting Flask web server...")
        flask_thread = threading.Thread(target=start_flask_server, daemon=False)
        flask_thread.start()
        
        # Give the server a moment to start
        time.sleep(3)
        logger.info(f"Web server should be available at http://localhost:{PORT}")
    
    try:
        # Start the bot
        asyncio.run(run_bot_with_reconnect())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Bot startup error: {e}")

if __name__ == "__main__":
    main()

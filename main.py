
import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import time
import sys
import aiofiles

# Railway logging setup
import logging
logging.basicConfig(level=logging.INFO)

print("🚀 Starting Discord Bot...")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
ADMIN_ROLE_ID = 1405525451807522847
LOG_CHANNEL_ID = 1405523454924685353
PURCHASE_LOG_CHANNEL_ID = 1405523454924685353

# Coinflip configuration
coinflip_config = {
    "win_chance": 45,  # 45% chance to win
    "max_bet": 1000    # Maximum bet of 1000 tokens
}

# Mines multipliers (based on number of safe spots clicked)
MINES_MULTIPLIERS = {
    1: 1.00, 2: 1.10, 3: 1.21, 4: 1.33, 5: 1.46,
    6: 1.61, 7: 1.77, 8: 1.95, 9: 2.14, 10: 2.36,
    11: 2.59, 12: 2.85, 13: 3.14, 14: 3.45, 15: 3.80,
    16: 4.18, 17: 4.60, 18: 5.06, 19: 5.57, 20: 6.12,
    21: 6.74, 22: 7.41, 23: 8.15, 24: 8.97, 25: 9.87
}

# Roles that get extra entries in giveaways (customize these IDs for your server)
# Format: {role_id: extra_entries}
PRIORITY_ROLES = {
    1410917252190179369: 7,  # Highest priority role - 7 extra entries
    1410917163933503521: 5,  # Medium priority role - 5 extra entries  
    1410917146459897928: 3,  # Low priority role - 3 extra entries
}

# Data storage
user_data = {}
shop_data = []
cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}, "mines": {}}
pending_duels = {}
active_giveaways = {}
giveaway_daily_totals = {}  # Track daily giveaway amounts
active_mines_games = {}  # Track active mines games
invite_data = {}  # Track invites: {inviter_id: {invited_users: [], total_invites: 0, tokens_earned: 0}}
user_message_times = {}  # Anti-spam tracking: {user_id: [timestamp1, timestamp2, ...]}

# Data file paths
USER_DATA_FILE = 'user_data.json'
SHOP_DATA_FILE = 'shop_data.json'
COOLDOWNS_FILE = 'cooldowns.json'
GIVEAWAYS_FILE = 'giveaways.json'
DAILY_GIVEAWAYS_FILE = 'daily_giveaways.json'
COINFLIP_CONFIG_FILE = 'coinflip_config.json'
INVITE_DATA_FILE = 'invite_data.json'
ANTISPAM_DATA_FILE = 'antispam_data.json'

WORK_JOBS = [
    "worked as a cashier at the supermarket", "stocked shelves at the grocery store", 
    "bagged groceries for customers", "worked the deli counter", "organized the produce section",
    "cleaned shopping carts", "collected carts from the parking lot", "worked customer service desk",
    "restocked the dairy section", "faced products on shelves", "worked the bakery counter",
    "unloaded delivery trucks", "worked overnight stocking shift", "operated the floor buffer",
    "cleaned the break room", "worked at Target", "worked at Walmart", "worked at Best Buy",
    "worked at Home Depot", "worked at CVS pharmacy", "worked the drive-thru window",
    "flipped burgers at McDonald's", "worked the fryer at KFC", "prepped vegetables at Subway",
    "worked as a server at Applebee's", "bussed tables at Olive Garden", "worked as a host at Chili's",
    "cleaned the kitchen at Taco Bell", "worked the pizza oven", "delivered pizzas",
    "worked at Starbucks", "worked at Dunkin Donuts", "made sandwiches at Subway",
    "filed paperwork at an office", "answered phones at a call center", "did data entry",
    "made copies and scanned documents", "worked reception desk", "sorted mail at post office",
    "updated customer databases", "scheduled appointments", "worked at bank teller window",
    "helped customers at DMV", "worked at phone store", "worked at gas station",
    "loaded boxes at Amazon warehouse", "worked construction cleanup", "painted houses",
    "helped people move", "worked landscaping", "cleaned office buildings", "worked at car wash",
    "did home repairs", "worked at recycling center", "unloaded freight trucks",
    "worked factory assembly line", "cleaned windows", "delivered for DoorDash",
    "drove for Uber", "worked at movie theater", "worked at gym front desk",
    "worked at library", "tutored kids", "walked dogs", "pet-sat", "house-sat", "baby-sat"
]

CRIME_ACTIVITIES = [
    "took extra napkins from fast food", "used work wifi for personal stuff", 
    "took longer breaks than allowed", "used company printer for personal use",
    "took pens from work", "ate someone's lunch from office fridge",
    "used sick day when not really sick", "browsed social media during work",
    "took extra coffee from break room", "left work 5 minutes early",
    "used work bathroom excessively", "took free mints from restaurant",
    "opened bag of chips before paying", "ate grapes while shopping",
    "used express lane with too many items", "didn't return shopping cart",
    "cut in line at checkout", "price-checked everything twice",
    "used student discount without being student", "tried on clothes with no intention to buy",
    "squeezed all the bread loaves", "spoiled movie endings", "left someone on read",
    "didn't hold elevator door", "took the good parking spot", "walked slowly in front of people",
    "chewed loudly in quiet places", "talked during movies", "didn't say thanks when door was held",
    "cut in line at coffee shop", "took up two seats on bus", "used someone's Netflix password",
    "didn't skip YouTube ads for creator", "used free trial with fake email",
    "downloaded music illegally", "used fake birthday for discounts",
    "made multiple email accounts for free trials", "used VPN to get cheaper prices",
    "shared streaming passwords", "used incognito mode to avoid cookies",
    "jaywalked across street", "littered a gum wrapper", "parked slightly over the line",
    "used bathroom without buying anything", "took extra sauce packets",
    "mixed different sodas at fountain", "didn't tip delivery driver enough",
    "returned item after using it once", "claimed package was lost when it wasn't",
    "used expired coupon"
]

async def load_data():
    """Load all data from files"""
    global user_data, shop_data, cooldowns, active_giveaways, giveaway_daily_totals, coinflip_config, invite_data, user_message_times
    
    try:
        # Load user data
        if os.path.exists(USER_DATA_FILE):
            async with aiofiles.open(USER_DATA_FILE, 'r') as f:
                contents = await f.read()
                user_data = json.loads(contents)
                print(f"✅ Loaded user data for {len(user_data)} users")
        else:
            print("ℹ️ No user data file found, starting fresh")
            user_data = {}
            
        # Load shop data
        if os.path.exists(SHOP_DATA_FILE):
            async with aiofiles.open(SHOP_DATA_FILE, 'r') as f:
                contents = await f.read()
                shop_data = json.loads(contents)
                print(f"✅ Loaded {len(shop_data)} shop items")
        else:
            print("ℹ️ No shop data file found, starting fresh")
            shop_data = []
            
        # Load cooldowns
        if os.path.exists(COOLDOWNS_FILE):
            async with aiofiles.open(COOLDOWNS_FILE, 'r') as f:
                contents = await f.read()
                cooldowns = json.loads(contents)
                print("✅ Loaded cooldown data")
        else:
            print("ℹ️ No cooldowns file found, starting fresh")
            cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}, "mines": {}}
        
        # Load active giveaways
        if os.path.exists(GIVEAWAYS_FILE):
            async with aiofiles.open(GIVEAWAYS_FILE, 'r') as f:
                contents = await f.read()
                active_giveaways = json.loads(contents)
                print(f"✅ Loaded {len(active_giveaways)} active giveaways")
        else:
            print("ℹ️ No giveaways file found, starting fresh")
            active_giveaways = {}
            
        # Load daily giveaway totals
        if os.path.exists(DAILY_GIVEAWAYS_FILE):
            async with aiofiles.open(DAILY_GIVEAWAYS_FILE, 'r') as f:
                contents = await f.read()
                giveaway_daily_totals = json.loads(contents)
                print("✅ Loaded daily giveaway totals")
        else:
            print("ℹ️ No daily giveaways file found, starting fresh")
            giveaway_daily_totals = {}
            
        # Load coinflip configuration
        if os.path.exists(COINFLIP_CONFIG_FILE):
            async with aiofiles.open(COINFLIP_CONFIG_FILE, 'r') as f:
                contents = await f.read()
                coinflip_config = json.loads(contents)
                print("✅ Loaded coinflip configuration")
        else:
            print("ℹ️ No coinflip config file found, using defaults")
            coinflip_config = {"win_chance": 45, "max_bet": 1000}
            
        # Load invite data
        if os.path.exists(INVITE_DATA_FILE):
            async with aiofiles.open(INVITE_DATA_FILE, 'r') as f:
                contents = await f.read()
                invite_data = json.loads(contents)
                print(f"✅ Loaded invite data for {len(invite_data)} inviters")
        else:
            print("ℹ️ No invite data file found, starting fresh")
            invite_data = {}
            
        # Load anti-spam data
        if os.path.exists(ANTISPAM_DATA_FILE):
            async with aiofiles.open(ANTISPAM_DATA_FILE, 'r') as f:
                contents = await f.read()
                user_message_times = json.loads(contents)
                print("✅ Loaded anti-spam data")
        else:
            print("ℹ️ No anti-spam data file found, starting fresh")
            user_message_times = {}
            
    except Exception as e:
        print(f"⚠️ Error loading data: {e}")
        # Initialize empty data structures if loading fails
        user_data = {}
        shop_data = []
        cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}, "mines": {}}
        active_giveaways = {}
        giveaway_daily_totals = {}
        coinflip_config = {"win_chance": 45, "max_bet": 1000}
        invite_data = {}
        user_message_times = {}

def parse_amount(amount_str):
    """Parse amount strings with k, m, b suffixes"""
    if isinstance(amount_str, int):
        return amount_str
    
    amount_str = str(amount_str).strip().lower()
    
    if amount_str.endswith('k'):
        try:
            return int(float(amount_str[:-1]) * 1000)
        except ValueError:
            return None
    elif amount_str.endswith('m'):
        try:
            return int(float(amount_str[:-1]) * 1000000)
        except ValueError:
            return None
    elif amount_str.endswith('b'):
        try:
            return int(float(amount_str[:-1]) * 1000000000)
        except ValueError:
            return None
    else:
        try:
            return int(amount_str)
        except ValueError:
            return None

async def save_data():
    """Save all data to files"""
    try:
        # Save user data
        async with aiofiles.open(USER_DATA_FILE, 'w') as f:
            await f.write(json.dumps(user_data, indent=2))
        
        # Save shop data
        async with aiofiles.open(SHOP_DATA_FILE, 'w') as f:
            await f.write(json.dumps(shop_data, indent=2))
        
        # Save cooldowns
        async with aiofiles.open(COOLDOWNS_FILE, 'w') as f:
            await f.write(json.dumps(cooldowns, indent=2))
            
        # Save active giveaways
        async with aiofiles.open(GIVEAWAYS_FILE, 'w') as f:
            await f.write(json.dumps(active_giveaways, indent=2))
            
        # Save daily giveaway totals
        async with aiofiles.open(DAILY_GIVEAWAYS_FILE, 'w') as f:
            await f.write(json.dumps(giveaway_daily_totals, indent=2))
            
        # Save coinflip configuration
        async with aiofiles.open(COINFLIP_CONFIG_FILE, 'w') as f:
            await f.write(json.dumps(coinflip_config, indent=2))
            
        # Save invite data
        async with aiofiles.open(INVITE_DATA_FILE, 'w') as f:
            await f.write(json.dumps(invite_data, indent=2))
            
        # Save anti-spam data
        async with aiofiles.open(ANTISPAM_DATA_FILE, 'w') as f:
            await f.write(json.dumps(user_message_times, indent=2))
            
        print("💾 Data saved successfully")
        return True
    except Exception as e:
        print(f"⚠️ Error saving data: {e}")
        return False

async def force_save_on_exit():
    """Force save data when bot shuts down"""
    print("🔄 Bot shutting down, saving data...")
    try:
        if await save_data():
            print("💾 Data saved on exit")
        else:
            print("❌ Failed to save data on exit")
    except Exception as e:
        print(f"⚠️ Error saving on exit: {e}")

async def log_action(action_type, title, description, color=0x0099ff, user=None, fields=None):
    """Send log message to the log channel"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f"⚠️ Log channel {LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", "Field"),
                    value=field.get("value", "No value"),
                    inline=field.get("inline", True)
                )
        
        embed.set_footer(text=f"Action: {action_type}")
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"⚠️ Error sending log: {e}")

async def log_purchase(user, item_name, price, quantity=1):
    """Log purchase to purchase log channel"""
    try:
        purchase_channel = bot.get_channel(PURCHASE_LOG_CHANNEL_ID)
        if not purchase_channel:
            print(f"⚠️ Purchase log channel {PURCHASE_LOG_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title="🛒 Purchase Made",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Item", value=item_name, inline=True)
        embed.add_field(name="Quantity", value=str(quantity), inline=True)
        embed.add_field(name="Total Cost", value=f"{price * quantity:,} 🪙", inline=True)
        embed.add_field(name="Unit Price", value=f"{price:,} 🪙", inline=True)
        
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        await purchase_channel.send(embed=embed)
        
    except Exception as e:
        print(f"⚠️ Error sending purchase log: {e}")

def get_user_balance(user_id):
    """Get user balance"""
    return user_data.get(str(user_id), {}).get('balance', 0)

def update_balance(user_id, amount):
    """Update user balance"""
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'total_earned': 0, 'total_spent': 0}
    
    user_data[user_id]['balance'] += amount
    if amount > 0:
        user_data[user_id]['total_earned'] = user_data[user_id].get('total_earned', 0) + amount
    else:
        user_data[user_id]['total_spent'] = user_data[user_id].get('total_spent', 0) + abs(amount)
    
    return user_data[user_id]['balance']

def get_rank(balance):
    """Get user rank"""
    if balance >= 100000: return "🏆 Legendary"
    elif balance >= 50000: return "💎 Elite"
    elif balance >= 20000: return "🥇 VIP"
    elif balance >= 10000: return "🥈 Premium"
    elif balance >= 5000: return "🥉 Gold"
    elif balance >= 1000: return "🟢 Silver"
    else: return "🔵 Starter"

def can_use_command(user_id, command_type, hours):
    """Check if user can use command with persistent cooldowns"""
    user_id = str(user_id)
    if user_id not in cooldowns[command_type]:
        return True, None
    
    try:
        last_used = datetime.fromisoformat(cooldowns[command_type][user_id])
        next_use = last_used + timedelta(hours=hours)
        if datetime.now() >= next_use:
            return True, None
        return False, next_use
    except:
        return True, None

def can_use_short_cooldown(user_id, command_type, seconds):
    """Check short cooldowns"""
    user_id = str(user_id)
    if user_id not in cooldowns[command_type]:
        return True
    
    try:
        last_used = float(cooldowns[command_type][user_id])
        if time.time() - last_used >= seconds:
            return True
        return False
    except:
        return True

def set_short_cooldown(user_id, command_type):
    """Set short cooldown using timestamp"""
    cooldowns[command_type][str(user_id)] = str(time.time())

def format_time(next_use):
    """Format time remaining"""
    try:
        remaining = next_use - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return "soon"

def is_admin(user):
    """Check if user is admin"""
    return any(role.id == ADMIN_ROLE_ID for role in user.roles)

def check_spam(user_id):
    """Check if user is spamming and deduct tokens if they are"""
    current_time = time.time()
    user_id_str = str(user_id)
    
    if user_id_str not in user_message_times:
        user_message_times[user_id_str] = []
    
    # Remove timestamps older than 10 seconds
    user_message_times[user_id_str] = [t for t in user_message_times[user_id_str] if current_time - t < 10]
    
    # Add current timestamp
    user_message_times[user_id_str].append(current_time)
    
    # Check if user has sent more than 5 messages in 10 seconds
    if len(user_message_times[user_id_str]) > 5:
        # Deduct 50 tokens for spamming
        balance_before = get_user_balance(user_id)
        if balance_before >= 50:
            new_balance = update_balance(user_id, -50)
            asyncio.create_task(save_data())
            
            # Clear the message times to prevent multiple deductions
            user_message_times[user_id_str] = []
            
            return True, balance_before, new_balance
    
    return False, 0, 0

# Auto-save task
async def auto_save():
    """Auto save every 30 seconds"""
    while True:
        await asyncio.sleep(30)
        await save_data()

# Clean up expired duels
async def cleanup_expired_duels():
    """Clean up expired duel challenges"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        current_time = datetime.now()
        expired_duels = []
        
        for duel_key, duel_data in pending_duels.items():
            try:
                created_at = duel_data['created_at']
                if (current_time - created_at).total_seconds() > 300:
                    expired_duels.append(duel_key)
            except:
                expired_duels.append(duel_key)
        
        for expired_key in expired_duels:
            del pending_duels[expired_key]

# Clean up expired giveaways
async def cleanup_expired_giveaways():
    """Clean up expired giveaways"""
    while True:
        await asyncio.sleep(60)  # 1 minute
        current_time = datetime.now()
        expired_giveaways = []
        
        for giveaway_id, giveaway_data in active_giveaways.items():
            try:
                end_time = datetime.fromisoformat(giveaway_data['end_time'])
                if current_time >= end_time:
                    expired_giveaways.append(giveaway_id)
            except:
                expired_giveaways.append(giveaway_id)
        
        for expired_id in expired_giveaways:
            del active_giveaways[expired_id]
            await save_data()

# Clean up expired mines games
async def cleanup_expired_mines():
    """Clean up expired mines games"""
    while True:
        await asyncio.sleep(60)  # 1 minute
        current_time = datetime.now()
        expired_mines = []
        
        for game_id, game_data in active_mines_games.items():
            try:
                created_at = datetime.fromisoformat(game_data['created_at'])
                if (current_time - created_at).total_seconds() > 300:  # 5 minutes
                    expired_mines.append(game_id)
            except:
                expired_mines.append(game_id)
        
        for expired_id in expired_mines:
            del active_mines_games[expired_id]

# Reset daily giveaway totals at midnight
async def reset_daily_giveaway_totals():
    """Reset daily giveaway totals at midnight"""
    while True:
        now = datetime.now()
        # Calculate time until next midnight
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_midnight - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        
        # Reset daily totals
        giveaway_daily_totals.clear()
        await save_data()
        print("🔄 Reset daily giveaway totals")

# Clean up old anti-spam data
async def cleanup_antispam_data():
    """Clean up old anti-spam data"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        current_time = time.time()
        
        for user_id in list(user_message_times.keys()):
            # Remove all timestamps older than 1 hour
            user_message_times[user_id] = [t for t in user_message_times[user_id] if current_time - t < 3600]
            
            # Remove user entry if no recent messages
            if not user_message_times[user_id]:
                del user_message_times[user_id]
        
        await save_data()

@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is online!')
    await load_data()
    
    # Start background tasks
    bot.auto_save_task = asyncio.create_task(auto_save())
    bot.cleanup_task = asyncio.create_task(cleanup_expired_duels())
    bot.giveaway_cleanup_task = asyncio.create_task(cleanup_expired_giveaways())
    bot.mines_cleanup_task = asyncio.create_task(cleanup_expired_mines())
    bot.daily_reset_task = asyncio.create_task(reset_daily_giveaway_totals())
    bot.antispam_cleanup_task = asyncio.create_task(cleanup_antispam_data())
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")

@bot.event
async def on_message(message):
    if not message.author.bot and message.guild:
        # Check for spam
        is_spam, old_balance, new_balance = check_spam(message.author.id)
        if is_spam:
            try:
                embed = discord.Embed(
                    title="⚠️ Anti-Spam System",
                    description="You have been detected sending messages too quickly!",
                    color=0xff4444,
                    timestamp=datetime.now()
                )
                embed.add_field(name="Penalty", value="-50 🪙", inline=True)
                embed.add_field(name="Old Balance", value=f"{old_balance:,} 🪙", inline=True)
                embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
                embed.set_footer(text="Please wait between messages to avoid penalties")
                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass
        
        # Award tokens for normal messages (if not spamming)
        tokens = random.randint(1, 5)
        update_balance(message.author.id, tokens)
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    """Check if member was invited by someone and reward the inviter"""
    try:
        # Check if the member's account is 30 days or older
        account_age = datetime.now().astimezone() - member.created_at
        if account_age.days < 30:
            print(f"❌ {member} joined but account is too new ({account_age.days} days)")
            return
        
        # Get all invites for the guild
        try:
            invites = await member.guild.invites()
        except:
            print(f"⚠️ Could not get invites for guild {member.guild.name}")
            return
        
        # Find the invite with the highest uses (most likely the one used)
        used_invite = None
        max_uses = 0
        
        for invite in invites:
            if invite.inviter and not invite.inviter.bot and invite.uses > max_uses:
                used_invite = invite
                max_uses = invite.uses
        
        if not used_invite or used_invite.inviter.id == member.id:
            return
        
        inviter_id = str(used_invite.inviter.id)
        invited_id = str(member.id)
        
        # Initialize inviter data if not exists
        if inviter_id not in invite_data:
            invite_data[inviter_id] = {
                'invited_users': [],
                'total_invites': 0,
                'tokens_earned': 0
            }
        
        # Check if this user was already tracked
        if invited_id in invite_data[inviter_id]['invited_users']:
            return
        
        # Reward inviter with 300 tokens
        update_balance(int(inviter_id), 300)
        invite_data[inviter_id]['invited_users'].append(invited_id)
        invite_data[inviter_id]['total_invites'] += 1
        invite_data[inviter_id]['tokens_earned'] += 300
        
        await save_data()
        
        # Send DM to inviter
        try:
            embed = discord.Embed(
                title="🎉 Invite Reward!",
                description=f"You invited {member.mention} and got 300 tokens!",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="Invited User", value=member.display_name, inline=True)
            embed.add_field(name="Reward", value="300 🪙", inline=True)
            embed.add_field(name="Total Invites", value=invite_data[inviter_id]['total_invites'], inline=True)
            embed.set_footer(text="IM's Universe")
            
            await used_invite.inviter.send(embed=embed)
        except:
            print(f"⚠️ Could not DM {used_invite.inviter} about invite reward")
        
        print(f"✅ {used_invite.inviter} rewarded 300 tokens for inviting {member}")
        
    except Exception as e:
        print(f"⚠️ Error processing member join: {e}")


# Invite Panel View
class InvitePanelView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    @discord.ui.button(label="🔗 Generate Invite Link", style=discord.ButtonStyle.green, emoji="🔗")
    async def generate_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return
        
        try:
            # Create an invite for the server with longer duration
            guild = interaction.guild
            invite_channel = guild.text_channels[0]  # Use first text channel
            
            # Create invite with reasonable settings
            invite = await invite_channel.create_invite(
                max_uses=10, 
                unique=True, 
                max_age=604800,  # 7 days
                reason=f"Invite generated by {interaction.user} for token rewards"
            )
            
            embed = discord.Embed(
                title="🔗 Your Personal Invite Link",
                description=f"Share this link to invite friends to the server!",
                color=0x0099ff
            )
            embed.add_field(name="Invite Link", value=invite.url, inline=False)
            embed.add_field(name="Reward", value="300 🪙 per valid invite", inline=True)
            embed.add_field(name="Requirements", value="Account must be 30+ days old", inline=True)
            embed.add_field(name="Expires", value="7 days", inline=True)
            embed.add_field(name="Max Uses", value="10 uses", inline=True)
            embed.set_footer(text="You'll receive a DM when someone joins using your link")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"⚠️ Error generating invite: {e}")
            await interaction.response.send_message("❌ Could not generate invite link. Please try again or ask an admin.", ephemeral=True)

    
    @discord.ui.button(label="📊 View My Invites", style=discord.ButtonStyle.blurple, emoji="📊")
    async def view_invites(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your panel!", ephemeral=True)
            return
        
        user_id_str = str(interaction.user.id)
        user_invites = invite_data.get(user_id_str, {
            'invited_users': [],
            'total_invites': 0,
            'tokens_earned': 0
        })
        
        embed = discord.Embed(
            title="📊 Your Invite Statistics",
            description="Track your invites and rewards",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Total Invites", value=user_invites['total_invites'], inline=True)
        embed.add_field(name="Tokens Earned", value=f"{user_invites['tokens_earned']:,} 🪙", inline=True)
        embed.add_field(name="Reward per Invite", value="300 🪙", inline=True)
        
        if user_invites['invited_users']:
            # Show recent invites (last 5)
            recent_invites = user_invites['invited_users'][-5:]
            invite_text = ""
            for invited_id in recent_invites:
                try:
                    user = await bot.fetch_user(int(invited_id))
                    invite_text += f"• {user.mention}\n"
                except:
                    invite_text += f"• Unknown User (ID: {invited_id})\n"
            
            if len(user_invites['invited_users']) > 5:
                invite_text += f"\n... and {len(user_invites['invited_users']) - 5} more"
            
            embed.add_field(name="Recent Invites", value=invite_text, inline=False)
        else:
            embed.add_field(name="Recent Invites", value="No invites yet", inline=False)
        
        embed.set_footer(text="Keep inviting to earn more tokens!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="invitespanel", description="View invite rewards information and manage your invites")
async def invitespanel(interaction: discord.Interaction):
    """Display the invite rewards panel"""
    embed = discord.Embed(
        title="🎉 Invite Rewards System",
        description="Earn tokens by inviting friends to the server!",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="💰 Reward System",
        value="• **300 🪙** per valid invite\n• Account must be **30+ days old**\n• You'll receive a DM when rewarded\n• No limit on invites!",
        inline=False
    )
    
    embed.add_field(
        name="📋 How It Works",
        value="1. Generate your personal invite link\n2. Share it with friends\n3. When they join, you get 300 tokens\n4. Track your invites and earnings",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Requirements",
        value="• Invited accounts must be 30+ days old\n• Must use your personal invite link\n• Bot must have permissions to track invites",
        inline=False
    )
    
    user_id_str = str(interaction.user.id)
    user_invites = invite_data.get(user_id_str, {
        'invited_users': [],
        'total_invites': 0,
        'tokens_earned': 0
    })
    
    embed.add_field(
        name="📊 Your Stats",
        value=f"**Total Invites:** {user_invites['total_invites']}\n**Tokens Earned:** {user_invites['tokens_earned']:,} 🪙",
        inline=False
    )
    
    embed.set_footer(text="Use the buttons below to manage your invites")
    
    view = InvitePanelView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="balance", description="Check your token balance")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = get_user_balance(interaction.user.id)
    data = user_data.get(user_id, {})
    earned = data.get('total_earned', 0)
    spent = data.get('total_spent', 0)
    rank = get_rank(balance)
    
    embed = discord.Embed(
        title="💰 Token Wallet",
        color=0x7B68EE,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Current Balance", value=f"**{balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Total Spent", value=f"{spent:,} 🪙", inline=True)
    embed.add_field(name="Total Earned", value=f"{earned:,} 🪙", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.set_footer(text="💬 Chat to earn 1-5 tokens per message")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Claim daily tokens (24h cooldown)")
async def daily(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "daily", 24)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"⏰ Daily already claimed! Come back in **{time_left}**", ephemeral=True)
        return
    
    tokens = random.randint(1, 50)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["daily"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    embed = discord.Embed(title="🎁 Daily Reward!", color=0x00ff00)
    embed.add_field(name="Earned", value=f"{tokens:,} 🪙", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="work", description="Work for tokens (3h cooldown)")
async def work(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "work", 3)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"💼 Still tired! Rest for **{time_left}** more", ephemeral=True)
        return
    
    tokens = random.randint(1, 100)
    job = random.choice(WORK_JOBS)
    new_balance = update_balance(interaction.user.id, tokens)
    cooldowns["work"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    embed = discord.Embed(title="💼 Work Complete!", color=0x4CAF50)
    embed.add_field(name="Job", value=f"You {job}", inline=False)
    embed.add_field(name="Earned", value=f"{tokens:,} 🪙", inline=True)
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="crime", description="Commit crime for tokens (1h cooldown, risky!)")
async def crime(interaction: discord.Interaction):
    can_use, next_use = can_use_command(interaction.user.id, "crime", 1)
    
    if not can_use:
        time_left = format_time(next_use)
        await interaction.response.send_message(f"🚔 Lay low for **{time_left}** more!", ephemeral=True)
        return
    
    success = random.choice([True, False])
    activity = random.choice(CRIME_ACTIVITIES)
    
    if success:
        tokens = random.randint(1, 100)
        new_balance = update_balance(interaction.user.id, tokens)
        embed = discord.Embed(title="🎭 Crime Success!", color=0x00ff00)
        embed.add_field(name="Crime", value=f"You {activity}", inline=False)
        embed.add_field(name="Gained", value=f"+{tokens:,} 🪙", inline=True)
    else:
        tokens = random.randint(1, 200)
        current = get_user_balance(interaction.user.id)
        tokens = min(tokens, current)
        new_balance = update_balance(interaction.user.id, -tokens)
        embed = discord.Embed(title="🚔 Crime Failed!", color=0xff4444)
        embed.add_field(name="Crime", value=f"Tried to {activity}", inline=False)
        embed.add_field(name="Lost", value=f"-{tokens:,} 🪙", inline=True)
    
    embed.add_field(name="Balance", value=f"{new_balance:,} 🪙", inline=True)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    cooldowns["crime"][str(interaction.user.id)] = datetime.now().isoformat()
    await save_data()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="coinflip", description="Bet tokens on a coinflip")
async def coinflip(interaction: discord.Interaction, amount: str, choice: str):  # Changed to string for amount
    if not can_use_short_cooldown(interaction.user.id, "coinflip", 5):
        await interaction.response.send_message("⏰ Please wait 5 seconds between coinflips!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    # Check max bet
    if parsed_amount > coinflip_config["max_bet"]:
        await interaction.response.send_message(f"❌ Maximum bet is {coinflip_config['max_bet']:,} tokens!", ephemeral=True)
        return
    
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await interaction.response.send_message("❌ Choose 'heads' or 'tails' (or 'h'/'t')!", ephemeral=True)
        return
    
    if choice in ['h', 'heads']:
        choice = 'heads'
    else:
        choice = 'tails'
    
    balance = get_user_balance(interaction.user.id)
    if balance < parsed_amount:
        await interaction.response.send_message(f"❌ Insufficient funds! You need **{parsed_amount - balance:,}** more tokens.", ephemeral=True)
        return

    # More natural coinflip with configurable odds
    # Generate a random number between 1-100
    roll = random.randint(1, 100)
    
    # Use configurable win chance
    win_chance = coinflip_config["win_chance"]
    won = roll <= win_chance  # If roll is within win chance percentage, player wins
    
    # Make it feel more natural by using actual coin flip logic
    # but with weighted outcomes
    actual_flip = random.choice(['heads', 'tails'])
    result = actual_flip
    
    # If the player should lose based on house edge, override the result
    # but make it feel natural by only doing this sometimes
    if not won and random.random() < 0.7:  # 70% of losses feel natural
        result = 'tails' if choice == 'heads' else 'heads'
    
    if won:
        # Player wins their bet
        winnings = parsed_amount
        new_balance = update_balance(interaction.user.id, winnings)
        embed = discord.Embed(title="🪙 Coinflip - YOU WON!", color=0x00ff00)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=f"🪙 {result.title()}", inline=True)
        embed.add_field(name="Winnings", value=f"+{winnings:,} 🪙", inline=True)
    else:
        # Player loses their bet
        new_balance = update_balance(interaction.user.id, -parsed_amount)
        embed = discord.Embed(title="🪙 Coinflip - YOU LOST!", color=0xff4444)
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=f"🪙 {result.title()}", inline=True)
        embed.add_field(name="Lost", value=f"-{parsed_amount:,} 🪙", inline=True)
    
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    set_short_cooldown(interaction.user.id, "coinflip")
    await save_data()
    
    await log_action(
        "COINFLIP",
        f"🪙 Coinflip {'Win' if won else 'Loss'}",
        f"{interaction.user.mention} {'won' if won else 'lost'} **{parsed_amount:,} tokens** on coinflip",
        color=0x00ff00 if won else 0xff4444,
        user=interaction.user,
        fields=[
            {"name": "Bet Amount", "value": f"{parsed_amount:,} 🪙", "inline": True},
            {"name": "Choice", "value": choice.title(), "inline": True},
            {"name": "Result", "value": result.title(), "inline": True},
            {"name": "Outcome", "value": "Won" if won else "Lost", "inline": True}
        ]
    )
    
    await interaction.response.send_message(embed=embed)

# Mines game button class
# Mines game button class
class MinesButton(discord.ui.Button):
    def __init__(self, position, revealed=False, is_mine=False):
        self.position = position
        self.revealed = revealed
        self.is_mine = is_mine
        
        if revealed:
            if is_mine:
                super().__init__(style=discord.ButtonStyle.danger, label="💣", disabled=True, row=position // 5)
            else:
                super().__init__(style=discord.ButtonStyle.success, label="💎", disabled=True, row=position // 5)
        else:
             super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=min(position // 5, 4))
    
    async def callback(self, interaction: discord.Interaction):
        # Get the game data
        game_id = f"{interaction.user.id}_mines"
        if game_id not in active_mines_games:
            await interaction.response.send_message("❌ This game has expired!", ephemeral=True)
            return
        
        game = active_mines_games[game_id]
        
        # Check if game is over or position already revealed
        if game.get('game_over') or self.position in game['revealed']:
            await interaction.response.defer()
            return
        
        # Check if it's a mine
        if self.position in game['mines']:
            # Game over - player hit a mine
            game['revealed'].append(self.position)
            game['game_over'] = True
            
            # Update all buttons
            for child in self.view.children:
                if isinstance(child, MinesButton):
                    if child.position in game['mines']:
                        child.revealed = True
                        child.is_mine = True
                        child.style = discord.ButtonStyle.danger
                        child.label = "💣"
                        child.disabled = True
                    elif child.position in game['revealed']:
                        child.revealed = True
                        child.style = discord.ButtonStyle.success
                        child.label = "💎"
                        child.disabled = True
            
            # Update message with loss
            embed = discord.Embed(
                title="💣 Mines Game - YOU LOST!",
                description=f"You hit a mine and lost your bet of **{game['bet']:,}** 🪙",
                color=0xff4444
            )
            embed.add_field(name="Bet Amount", value=f"{game['bet']:,} 🪙", inline=True)
            embed.add_field(name="Safe Spots Found", value=f"{len(game['revealed']) - 1}", inline=True)  # -1 because last one was a mine
            embed.add_field(name="Multiplier", value=f"{MINES_MULTIPLIERS.get(len(game['revealed']) - 1, 1.0):.2f}x", inline=True)
            embed.set_footer(text="Better luck next time!")
            
            await interaction.response.edit_message(embed=embed, view=self.view)
            
            # Remove game from active games
            del active_mines_games[game_id]
            return
        
        # Safe spot - add to revealed and update multiplier
        game['revealed'].append(self.position)
        self.revealed = True
        self.style = discord.ButtonStyle.success
        self.label = "💎"
        self.disabled = True
        
        # Calculate current multiplier
        current_multiplier = MINES_MULTIPLIERS.get(len(game['revealed']), 1.0)
        potential_win = int(game['bet'] * current_multiplier)
        
        # Update the embed
        embed = discord.Embed(
            title="💎 Mines Game",
            description=f"Click on squares to reveal gems. Avoid the mines!",
            color=0x00ff00
        )
        embed.add_field(name="Bet Amount", value=f"{game['bet']:,} 🪙", inline=True)
        embed.add_field(name="Safe Spots Found", value=f"{len(game['revealed'])}", inline=True)
        embed.add_field(name="Current Multiplier", value=f"{current_multiplier:.2f}x", inline=True)
        embed.add_field(name="Potential Win", value=f"{potential_win:,} 🪙", inline=True)
        embed.add_field(name="Mines Remaining", value=f"{game['mines_count']} / 25", inline=True)
        embed.add_field(name="‎", value="‎", inline=True)
        embed.set_footer(text="Click 'Cash Out' to collect your winnings!")
        
        await interaction.response.edit_message(embed=embed, view=self.view)

# Mines game view with cash out button
class MinesView(discord.ui.View):
    def __init__(self, game_id):
        super().__init__(timeout=300)
        self.game_id = game_id
        
        # Create the initial board
        for i in range(25):
            self.add_item(MinesButton(i))
    
        @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.green, row=5)
        async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
           # Get the game data
           if self.game_id not in active_mines_games:
             await interaction.response.send_message("❌ This game has expired!", ephemeral=True)
             return

        game = active_mines_games[self.game_id]


        # Calculate winnings
        multiplier = MINES_MULTIPLIERS.get(len(game['revealed']), 1.0)
        winnings = int(game['bet'] * multiplier)
        
    async def handle_cash_out(interaction, winnings):
        # Update user balance
        update_balance(interaction.user.id, winnings)

        # Save data asynchronously
        await save_data()
        
        await interaction.response.send_message("✅ You cashed out!", ephemeral=True)
        
        # Reveal all mines and disable all buttons
        for child in self.view.children:
            if isinstance(child, MinesButton):
                if child.position in game['mines'] and not child.revealed:
                    child.revealed = True
                    child.is_mine = True
                    child.style = discord.ButtonStyle.danger
                    child.label = "💣"
                    child.disabled = True
                elif not child.revealed:
                    child.disabled = True
        
        # Update message with win
        embed = discord.Embed(
            title="💰 Mines Game - CASH OUT!",
            description=f"You cashed out and won **{winnings:,}** 🪙!",
            color=0x00ff00
        )
        embed.add_field(name="Bet Amount", value=f"{game['bet']:,} 🪙", inline=True)
        embed.add_field(name="Safe Spots Found", value=f"{len(game['revealed'])}", inline=True)
        embed.add_field(name="Multiplier", value=f"{multiplier:.2f}x", inline=True)
        embed.add_field(name="Winnings", value=f"{winnings:,} 🪙", inline=True)
        embed.add_field(name="Mines", value=f"{game['mines_count']} / 25", inline=True)
        embed.add_field(name="‎", value="‎", inline=True)
        embed.set_footer(text="Congratulations!")
        
        await interaction.response.edit_message(embed=embed, view=self.view)
        
        # Remove game from active games
        del active_mines_games[self.game_id]
        
        # Log the mines game
        await log_action(
            "MINES",
            "💰 Mines Game Won",
            f"**{interaction.user.mention}** won **{winnings:,} tokens** in mines game",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Bet Amount", "value": f"{game['bet']:,} 🪙", "inline": True},
                {"name": "Safe Spots", "value": len(game['revealed']), "inline": True},
                {"name": "Multiplier", "value": f"{multiplier:.2f}x", "inline": True},
                {"name": "Winnings", "value": f"{winnings:,} 🪙", "inline": True}
            ]
        )

@bot.tree.command(name="mines", description="Play mines game - find gems to multiply your bet!")
async def mines(interaction: discord.Interaction, amount: str, mines_count: int):  # Changed to string for amount
    # Check cooldown
    if not can_use_short_cooldown(interaction.user.id, "mines", 10):
        await interaction.response.send_message("⏰ Please wait 10 seconds between mines games!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    # Validate parameters
    if parsed_amount < 100:
        await interaction.response.send_message("❌ Minimum bet is 100 tokens!", ephemeral=True)
        return
    
    if parsed_amount > 1000:
        await interaction.response.send_message("❌ Maximum bet is 1,000 tokens!", ephemeral=True)
        return
    
    if mines_count < 1 or mines_count > 24:
        await interaction.response.send_message("❌ Number of mines must be between 1 and 24!", ephemeral=True)
        return
    
    # Check balance
    balance = get_user_balance(interaction.user.id)
    if balance < parsed_amount:
        await interaction.response.send_message(f"❌ You need **{parsed_amount - balance:,}** more tokens to play!", ephemeral=True)
        return
    
    # Deduct bet amount
    update_balance(interaction.user.id, -parsed_amount)
    set_short_cooldown(interaction.user.id, "mines")
    await save_data()
    
    # Create game
    game_id = f"{interaction.user.id}_mines"
    
    # Generate mines
    all_positions = list(range(25))
    mines_positions = random.sample(all_positions, mines_count)
    
    active_mines_games[game_id] = {
        'bet': parsed_amount,
        'mines': mines_positions,
        'mines_count': mines_count,
        'revealed': [],
        'created_at': datetime.now().isoformat(),
        'game_over': False
    }
    
    # Create embed
    embed = discord.Embed(
        title="💎 Mines Game",
        description=f"Click on squares to reveal gems. Avoid the mines!",
        color=0x00ff00
    )
    embed.add_field(name="Bet Amount", value=f"{parsed_amount:,} 🪙", inline=True)
    embed.add_field(name="Safe Spots Found", value="0", inline=True)
    embed.add_field(name="Current Multiplier", value="1.00x", inline=True)
    embed.add_field(name="Potential Win", value=f"{parsed_amount:,} 🪙", inline=True)
    embed.add_field(name="Mines", value=f"{mines_count} / 25", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    embed.set_footer(text="Click 'Cash Out' to collect your winnings!")
    
    # Create view with buttons
    view = MinesView(game_id)
    await interaction.response.send_message(embed=embed, view=view)

# Coinflip configuration modal
class CoinflipConfigModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Coinflip Configuration")
    
    win_chance = discord.ui.TextInput(
        label="Win Chance (%)",
        placeholder="Enter a number between 1-100",
        default=str(coinflip_config["win_chance"]),
        min_length=1,
        max_length=3
    )
    
    max_bet = discord.ui.TextInput(
        label="Max Bet (supports k, m, b suffixes)",
        placeholder="Enter maximum bet amount",
        default=str(coinflip_config["max_bet"]),
        min_length=1,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        try:
            win_chance = int(self.win_chance.value)
            if win_chance < 1 or win_chance > 100:
                await interaction.response.send_message("❌ Win chance must be between 1-100%!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Win chance must be a valid number!", ephemeral=True)
            return
        
        try:
            max_bet = parse_amount(self.max_bet.value)
            if max_bet is None or max_bet <= 0:
                await interaction.response.send_message("❌ Max bet must be a valid number! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Max bet must be a valid number! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
            return
        
        # Update configuration
        coinflip_config["win_chance"] = win_chance
        coinflip_config["max_bet"] = max_bet
        await save_data()
        
        embed = discord.Embed(title="✅ Coinflip Configuration Updated", color=0x00ff00)
        embed.add_field(name="Win Chance", value=f"{win_chance}%", inline=True)
        embed.add_field(name="Max Bet", value=f"{max_bet:,} 🪙", inline=True)
        embed.set_footer(text="Changes applied to all coinflip games")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the configuration change
        await log_action(
            "COINFLIP_CONFIG",
            "⚙️ Coinflip Configuration Updated",
            f"**{interaction.user.mention}** updated coinflip configuration",
            color=0x0099ff,
            user=interaction.user,
            fields=[
                {"name": "Win Chance", "value": f"{win_chance}%", "inline": True},
                {"name": "Max Bet", "value": f"{max_bet:,} 🪙", "inline": True}
            ]
        )

@bot.tree.command(name="config_cf", description="Configure coinflip settings (Admin only)")
async def config_cf(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    await interaction.response.send_modal(CoinflipConfigModal())

# Hide admin commands from regular users
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
    else:
        raise error

class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger_id, challenged_id, amount):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.challenged_id = challenged_id
        self.amount = amount
    
    @discord.ui.button(label="✅ Accept Duel", style=discord.ButtonStyle.green)
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("❌ This duel is not for you!", ephemeral=True)
            return
        
        challenger_balance = get_user_balance(self.challenger_id)
        challenged_balance = get_user_balance(self.challenged_id)
        
        if challenger_balance < self.amount:
            await interaction.response.send_message("❌ The challenger no longer has enough tokens!", ephemeral=True)
            return
        
        if challenged_balance < self.amount:
            await interaction.response.send_message(f"❌ You don't have enough tokens! Need {self.amount - challenged_balance:,} more.", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        winner_id = random.choice([self.challenger_id, self.challenged_id])
        loser_id = self.challenged_id if winner_id == self.challenger_id else self.challenger_id
        
        update_balance(winner_id, self.amount)
        update_balance(loser_id, -self.amount)
        await save_data()
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        challenger = bot.get_user(self.challenger_id)
        challenged = bot.get_user(self.challenged_id)
        
        embed = discord.Embed(title="⚔️ Duel Complete!", color=0xFFD700)
        embed.add_field(name="Winner", value=f"🏆 {winner.mention}", inline=True)
        embed.add_field(name="Loser", value=f"💀 {loser.mention}", inline=True)
        embed.add_field(name="Amount", value=f"{self.amount:,} 🪙", inline=True)
        embed.add_field(name="Winner's Balance", value=f"{get_user_balance(winner_id):,} 🪙", inline=True)
        embed.add_field(name="Loser's Balance", value=f"{get_user_balance(loser_id):,} 🪙", inline=True)
        embed.add_field(name="‎", value="‎", inline=True)
        
        embed.set_footer(text="The coin has decided!")
        
        await log_action(
            "DUEL",
            "⚔️ Duel Completed",
            f"Duel between {challenger.mention} and {challenged.mention}",
            color=0xFFD700,
            user=winner,
            fields=[
                {"name": "Challenger", "value": challenger.mention, "inline": True},
                {"name": "Challenged", "value": challenged.mention, "inline": True},
                {"name": "Amount", "value": f"{self.amount:,} 🪙", "inline": True},
                {"name": "Winner", "value": winner.mention, "inline": True}
            ]
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Decline Duel", style=discord.ButtonStyle.red)
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged_id:
            await interaction.response.send_message("❌ This duel is not for you!", ephemeral=True)
            return
        
        duel_key = f"{self.challenger_id}_{self.challenged_id}"
        if duel_key in pending_duels:
            del pending_duels[duel_key]
        
        challenger = bot.get_user(self.challenger_id)
        embed = discord.Embed(
            title="❌ Duel Declined", 
            description=f"{interaction.user.mention} declined the duel challenge from {challenger.mention}.",
            color=0xff4444
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

@bot.tree.command(name="duel", description="Challenge another user to a coinflip duel")
async def duel(interaction: discord.Interaction, user: discord.Member, amount: str):  # Changed to string for amount
    if not can_use_short_cooldown(interaction.user.id, "duel", 10):
        await interaction.response.send_message("⏰ Please wait 10 seconds between duel challenges!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't duel yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ You can't duel bots!", ephemeral=True)
        return
    
    challenger_balance = get_user_balance(interaction.user.id)
    if challenger_balance < parsed_amount:
        await interaction.response.send_message(f"❌ You need **{parsed_amount - challenger_balance:,}** more tokens to make this challenge!", ephemeral=True)
        return
    
    challenged_balance = get_user_balance(user.id)
    if challenged_balance < parsed_amount:
        await interaction.response.send_message(f"❌ {user.mention} doesn't have enough tokens for this duel! They need {parsed_amount - challenged_balance:,} more.", ephemeral=True)
        return
    
    duel_key = f"{interaction.user.id}_{user.id}"
    reverse_duel_key = f"{user.id}_{interaction.user.id}"
    
    if duel_key in pending_duels or reverse_duel_key in pending_duels:
        await interaction.response.send_message("❌ There's already a pending duel between you two!", ephemeral=True)
        return
    
    pending_duels[duel_key] = {
        'challenger': interaction.user.id,
        'challenged': user.id,
        'amount': parsed_amount,
        'created_at': datetime.now()
    }
    
    set_short_cooldown(interaction.user.id, "duel")
    
    embed = discord.Embed(
        title="⚔️ Duel Challenge!",
        description=f"{interaction.user.mention} challenges {user.mention} to a duel!",
        color=0xFFD700
    )
    
    embed.add_field(name="💰 Stakes", value=f"{parsed_amount:,} 🪙", inline=True)
    embed.add_field(name="🎯 Rules", value="Winner takes all!\nCoinflip decides the victor", inline=True)
    embed.add_field(name="⏰ Expires", value="60 seconds", inline=True)
    
    embed.add_field(name="💪 Challenger Balance", value=f"{challenger_balance:,} 🪙", inline=True)
    embed.add_field(name="🎲 Challenged Balance", value=f"{challenged_balance:,} 🪙", inline=True)
    embed.add_field(name="‎", value="‎", inline=True)
    
    embed.set_footer(text=f"{user.display_name}, will you accept this challenge?")
    
    view = DuelAcceptView(interaction.user.id, user.id, parsed_amount)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="gift", description="Gift tokens to another user (max 3k per day)")
async def gift(interaction: discord.Interaction, user: discord.Member, amount: str):  # Changed to string for amount
    if not can_use_short_cooldown(interaction.user.id, "gift", 3):
        await interaction.response.send_message("⏰ Please wait 3 seconds between gifts!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    if parsed_amount > 3000:
        await interaction.response.send_message("❌ You can only gift up to 3,000 tokens per day!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ Can't gift to yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ Can't gift to bots!", ephemeral=True)
        return
    
    # Check daily gift limit
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    if user_id not in giveaway_daily_totals:
        giveaway_daily_totals[user_id] = {}
    
    if today not in giveaway_daily_totals[user_id]:
        giveaway_daily_totals[user_id][today] = 0
    
    if giveaway_daily_totals[user_id][today] + parsed_amount > 3000:
        remaining = 3000 - giveaway_daily_totals[user_id][today]
        await interaction.response.send_message(f"❌ You can only gift {remaining:,} more tokens today!", ephemeral=True)
        return
    
    giver_balance = get_user_balance(interaction.user.id)
    if giver_balance < parsed_amount:
        await interaction.response.send_message(f"❌ Need **{parsed_amount - giver_balance:,}** more tokens!", ephemeral=True)
        return
    
    update_balance(interaction.user.id, -parsed_amount)
    update_balance(user.id, parsed_amount)
    giveaway_daily_totals[user_id][today] += parsed_amount
    set_short_cooldown(interaction.user.id, "gift")
    await save_data()
    
    await log_action(
        "GIFT",
        "🎁 Token Gift",
        f"{interaction.user.mention} gifted **{parsed_amount:,} tokens** to {user.mention}",
        color=0xffb347,
        user=interaction.user,
        fields=[
            {"name": "Giver", "value": interaction.user.mention, "inline": True},
            {"name": "Receiver", "value": user.mention, "inline": True},
            {"name": "Amount", "value": f"{parsed_amount:,} 🪙", "inline": True},
            {"name": "Daily Total", "value": f"{giveaway_daily_totals[user_id][today]:,}/3,000 🪙", "inline": True}
        ]
    )
    
    message = f"🎁 {interaction.user.mention} gifted **{parsed_amount:,} tokens** 🪙 to {user.mention}! 🎉"
    await interaction.response.send_message(message)

# Purchase confirmation view
class PurchaseConfirmView(discord.ui.View):
    def __init__(self, item, user_id):
        super().__init__(timeout=60)
        self.item = item
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Confirm Purchase", style=discord.ButtonStyle.green)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        balance = get_user_balance(interaction.user.id)
        if balance < self.item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{self.item['price'] - balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        new_balance = update_balance(interaction.user.id, -self.item['price'])
        await save_data()
        
        # Log the purchase
        await log_purchase(interaction.user, self.item['name'], self.item['price'])
        
        embed = discord.Embed(title="✅ Purchase Successful!", color=0x00ff00)
        embed.add_field(name="Item", value=self.item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{self.item['price']:,} 🪙", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
        
        if self.item.get('description'):
            embed.add_field(name="Description", value=self.item['description'], inline=False)
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            return
        
        embed = discord.Embed(title="❌ Purchase Cancelled", description="Your purchase has been cancelled.", color=0xff4444)
        await interaction.response.edit_message(embed=embed, view=None)

# Shop view with buttons
class ShopView(discord.ui.View):
    def __init__(self, user_balance):
        super().__init__(timeout=300)
        self.user_balance = user_balance
        
        for i, item in enumerate(shop_data[:25]):
            affordable = user_balance >= item['price']
            button = discord.ui.Button(
                label=f"{item['name']} - {item['price']:,}🪙",
                style=discord.ButtonStyle.green if affordable else discord.ButtonStyle.grey,
                disabled=not affordable,
                custom_id=f"buy_{i}"
            )
            button.callback = self.create_buy_callback(i)
            self.add_item(button)
    
    def create_buy_callback(self, item_index):
        async def buy_callback(interaction):
            await self.show_purchase_confirmation(interaction, item_index)
        return buy_callback
    
    async def show_purchase_confirmation(self, interaction, item_index):
        if item_index >= len(shop_data):
            await interaction.response.send_message("❌ Invalid item!", ephemeral=True)
            return
        
        item = shop_data[item_index]
        balance = get_user_balance(interaction.user.id)
        
        if balance < item['price']:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You need **{item['price'] - balance:,}** more tokens.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(title="🛒 Purchase Confirmation", color=0xFFD700)
        embed.add_field(name="Item", value=item['name'], inline=True)
        embed.add_field(name="Cost", value=f"{item['price']:,} 🪙", inline=True)
        embed.add_field(name="Your Balance", value=f"{balance:,} 🪙", inline=True)
        embed.add_field(name="Balance After", value=f"{balance - item['price']:,} 🪙", inline=True)
        
        if item.get('description'):
            embed.add_field(name="Description", value=item['description'], inline=False)
        
        embed.set_footer(text="Are you sure you want to buy this item?")
        
        view = PurchaseConfirmView(item, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="shop", description="Browse the token shop")
async def shop(interaction: discord.Interaction):
    balance = get_user_balance(interaction.user.id)
    
    embed = discord.Embed(title="🛒 Token Shop", color=0x0099ff)
    embed.add_field(name="Your Balance", value=f"**{balance:,}** 🪙", inline=False)
    
    if not shop_data:
        embed.description = "🚫 No items available!"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    items_text = ""
    for item in shop_data[:10]:
        affordable = "✅" if balance >= item['price'] else "❌"
        items_text += f"{affordable} **{item['name']}** - {item['price']:,} 🪙\n"
        if item.get('description'):
            items_text += f"    *{item['description'][:50]}{'...' if len(item['description']) > 50 else ''}*\n"
        items_text += "\n"
    
    embed.add_field(name="Available Items", value=items_text, inline=False)
    embed.set_footer(text="Click the buttons below to purchase items!")
    
    view = ShopView(balance)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item from the shop")
async def buy(interaction: discord.Interaction, item_name: str, quantity: int = 1):
    # Check 3 second cooldown
    if not can_use_short_cooldown(interaction.user.id, "buy", 3):
        await interaction.response.send_message("⏰ Please wait 3 seconds between purchases!", ephemeral=True)
        return
    
    if quantity <= 0:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return
    
    # Find the item
    item = None
    for shop_item in shop_data:
        if shop_item['name'].lower() == item_name.lower():
            item = shop_item
            break
    
    if not item:
        similar = [i['name'] for i in shop_data if item_name.lower() in i['name'].lower()]
        error_msg = f"❌ Item **{item_name}** not found!"
        if similar:
            error_msg += f"\n\nDid you mean: {', '.join(similar[:3])}"
        await interaction.response.send_message(error_msg, ephemeral=True)
        return
    
    balance = get_user_balance(interaction.user.id)
    total_cost = item['price'] * quantity
    
    if balance < total_cost:
        await interaction.response.send_message(
            f"❌ Insufficient funds!\n"
            f"**Cost:** {total_cost:,} 🪙 ({item['price']:,} × {quantity})\n"
            f"**Your Balance:** {balance:,} 🪙\n"
            f"**Need:** {total_cost - balance:,} more tokens",
            ephemeral=True
        )
        return
    
    # Purchase successful
    new_balance = update_balance(interaction.user.id, -total_cost)
    set_short_cooldown(interaction.user.id, "buy")
    await save_data()
    
    # Log the purchase
    await log_purchase(interaction.user, item['name'], item['price'], quantity)
    
    embed = discord.Embed(title="✅ Purchase Successful!", color=0x00ff00)
    embed.add_field(name="Item", value=item['name'], inline=True)
    embed.add_field(name="Quantity", value=str(quantity), inline=True)
    embed.add_field(name="Total Cost", value=f"{total_cost:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=False)
    
    if item.get('description'):
        embed.add_field(name="Description", value=item['description'], inline=False)
    
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Shop management modals and views
class AddItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add Shop Item")
    
    name = discord.ui.TextInput(label="Item Name")
    price = discord.ui.TextInput(label="Price (supports k, m, b suffixes)")
    description = discord.ui.TextInput(label="Description", required=False, style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        # Parse price with suffixes
        price_val = parse_amount(self.price.value)
        if price_val is None or price_val <= 0:
            await interaction.response.send_message("❌ Invalid price! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
            return
        
        # Check for duplicate items
        for item in shop_data:
            if item['name'].lower() == self.name.value.lower():
                await interaction.response.send_message("❌ Item with this name already exists!", ephemeral=True)
                return
        
        new_item = {
            'name': self.name.value,
            'price': price_val,
            'description': self.description.value or ""
        }
        
        shop_data.append(new_item)
        await save_data()
        
        # Log shop item addition
        await log_action(
            "SHOP_ADD",
            "🛒 Shop Item Added",
            f"**{interaction.user.mention}** added new item to shop",
            color=0x00ff00,
            user=interaction.user,
            fields=[
                {"name": "Item Name", "value": new_item['name'], "inline": True},
                {"name": "Price", "value": f"{new_item['price']:,} 🪙", "inline": True},
                {"name": "Description", "value": new_item['description'] or "No description", "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Added!", color=0x00ff00)
        embed.add_field(name="Name", value=new_item['name'], inline=False)
        embed.add_field(name="Price", value=f"{new_item['price']:,} 🪙", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class UpdateItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Update Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number", placeholder="Enter number (1, 2, 3...)")
    name = discord.ui.TextInput(label="New Name (optional)", required=False)
    price = discord.ui.TextInput(label="New Price (optional, supports k, m, b)", required=False)
    description = discord.ui.TextInput(label="New Description (optional)", required=False, style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        try:
            item_idx = int(self.item_number.value) - 1
            if item_idx < 0 or item_idx >= len(shop_data):
                await interaction.response.send_message(f"❌ Invalid item number! Must be 1-{len(shop_data)}", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Item number must be a valid number!", ephemeral=True)
            return
        
        if self.name.value.strip():
            # Check for duplicate names (excluding current item)
            for i, item in enumerate(shop_data):
                if i != item_idx and item['name'].lower() == self.name.value.lower():
                    await interaction.response.send_message("❌ Item with this name already exists!", ephemeral=True)
                    return
            shop_data[item_idx]['name'] = self.name.value.strip()
        
        if self.price.value.strip():
            # Parse price with suffixes
            new_price = parse_amount(self.price.value)
            if new_price is None or new_price <= 0:
                await interaction.response.send_message("❌ Price must be a valid number! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
                return
            shop_data[item_idx]['price'] = new_price
        
        if self.description.value.strip():
            shop_data[item_idx]['description'] = self.description.value.strip()
        
        await save_data()
        
        # Log shop item update
        await log_action(
            "SHOP_UPDATE",
            "✏️ Shop Item Updated",
            f"**{interaction.user.mention}** updated shop item",
            color=0x0099ff,
            user=interaction.user,
            fields=[
                {"name": "Item", "value": shop_data[item_idx]['name'], "inline": True},
                {"name": "Price", "value": f"{shop_data[item_idx]['price']:,} 🪙", "inline": True},
                {"name": "Changes Made", "value": "Updated item properties", "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Updated!", color=0x0099ff)
        embed.add_field(name="Item", value=shop_data[item_idx]['name'], inline=True)
        embed.add_field(name="Price", value=f"{shop_data[item_idx]['price']:,} 🪙", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteItemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Delete Shop Item")
    
    item_number = discord.ui.TextInput(label="Item Number", placeholder="Enter number (1, 2, 3...)")
    confirmation = discord.ui.TextInput(label="Type 'DELETE' to confirm", placeholder="This cannot be undone!")
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
            
        if self.confirmation.value.upper() != "DELETE":
            await interaction.response.send_message("❌ You must type 'DELETE' to confirm!", ephemeral=True)
            return
        
        try:
            item_idx = int(self.item_number.value) - 1
            if item_idx < 0 or item_idx >= len(shop_data):
                await interaction.response.send_message(f"❌ Invalid item number! Must be 1-{len(shop_data)}", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Item number must be a valid number!", ephemeral=True)
            return
        
        deleted_item = shop_data.pop(item_idx)
        await save_data()
        
        # Log shop item deletion
        await log_action(
            "SHOP_DELETE",
            "🗑️ Shop Item Deleted",
            f"**{interaction.user.mention}** deleted shop item",
            color=0xff4444,
            user=interaction.user,
            fields=[
                {"name": "Deleted Item", "value": deleted_item['name'], "inline": True},
                {"name": "Price", "value": f"{deleted_item['price']:,} 🪙", "inline": True},
                {"name": "Description", "value": deleted_item.get('description', 'No description'), "inline": False}
            ]
        )
        
        embed = discord.Embed(title="✅ Item Deleted!", color=0xff4444)
        embed.add_field(name="Deleted Item", value=deleted_item['name'], inline=True)
        embed.add_field(name="Price", value=f"{deleted_item['price']:,} 🪙", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.send_modal(AddItemModal())
    
    @discord.ui.button(label="✏️ Update Item", style=discord.ButtonStyle.blurple)
    async def update_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not shop_data:
            await interaction.response.send_message("❌ No items in shop to update!", ephemeral=True)
            return
        
        await interaction.response.send_modal(UpdateItemModal())
    
    @discord.ui.button(label="🗑️ Delete Item", style=discord.ButtonStyle.red)
    async def delete_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not shop_data:
            await interaction.response.send_message("❌ No items in shop to delete!", ephemeral=True)
            return
        
        await interaction.response.send_modal(DeleteItemModal())

@bot.tree.command(name="addshop", description="Manage shop (Admin only)")
async def addshop(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    embed = discord.Embed(title="🛍️ Shop Management", color=0xff9900)
    embed.add_field(name="📊 Stats", value=f"**Items:** {len(shop_data)}\n**Status:** {'Active' if shop_data else 'Empty'}", inline=True)
    
    if shop_data:
        total_value = sum(item['price'] for item in shop_data)
        cheapest = min(shop_data, key=lambda x: x['price'])
        most_expensive = max(shop_data, key=lambda x: x['price'])
        
        embed.add_field(
            name="💰 Price Range", 
            value=f"**Cheapest:** {cheapest['price']:,} 🪙\n**Most Expensive:** {most_expensive['price']:,} 🪙\n**Total Value:** {total_value:,} 🪙", 
            inline=True
        )
        
        items_list = "\n".join([f"{i+1}. **{item['name']}** - {item['price']:,} 🪙" for i, item in enumerate(shop_data[:10])])
        if len(shop_data) > 10:
            items_list += f"\n... and {len(shop_data) - 10} more items"
        embed.add_field(name="🛒 Current Items", value=items_list, inline=False)
    else:
        embed.add_field(name="🛒 Current Items", value="*No items in shop*", inline=False)
    
    embed.add_field(
        name="🔧 Available Actions",
        value="• **Add Item** - Create new shop items\n• **Update Item** - Modify existing items\n• **Delete Item** - Remove items from shop",
        inline=False
    )
    
    embed.set_footer(text="Use the buttons below to manage the shop")
    
    view = ShopManageView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ResetConfirmView(discord.ui.View):
    def __init__(self, original_user_id):
        super().__init__(timeout=30)
        self.original_user_id = original_user_id
    
    @discord.ui.button(label="🗑️ YES, RESET ALL DATA", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("❌ Only the command user can confirm!", ephemeral=True)
            return
        
        # Reset all data
        global user_data, cooldowns, invite_data, user_message_times
        user_data.clear()
        cooldowns = {"daily": {}, "work": {}, "crime": {}, "gift": {}, "buy": {}, "coinflip": {}, "duel": {}, "giveaway": {}, "mines": {}}
        invite_data.clear()
        user_message_times.clear()
        await save_data()
        
        success_embed = discord.Embed(
            title="✅ Data Reset Complete",
            description="All user data has been permanently deleted.\nUsers will start fresh with 0 tokens.",
            color=0x00ff00
        )
        success_embed.set_footer(text=f"Reset by {interaction.user.display_name}")
        
        await interaction.response.edit_message(embed=success_embed, view=None)
        
        # Log data reset action
        await log_action(
            "DATA_RESET",
            "🗑️ All Data Reset",
            f"**{interaction.user.mention}** performed a complete data reset",
            color=0xff0000,
            user=interaction.user,
            fields=[
                {"name": "Action", "value": "All user data deleted", "inline": True},
                {"name": "Users Affected", "value": "All server members", "inline": True},
                {"name": "Reset Time", "value": f"<t:{int(datetime.now().timestamp())}:F>", "inline": False}
            ]
        )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("❌ Only the command user can cancel!", ephemeral=True)
            return
        
        cancel_embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="Data reset has been cancelled. All user data remains intact.",
            color=0x808080
        )
        
        await interaction.response.edit_message(embed=cancel_embed, view=None)

@bot.tree.command(name="resetdata", description="Reset all user data (Admin only)")
async def resetdata(interaction: discord.Interaction, confirmation_code: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if confirmation_code != "BgH7459njrYEy7":
        await interaction.response.send_message("❌ Invalid confirmation code!", ephemeral=True)
        return
    
    # Ask for final confirmation
    embed = discord.Embed(
        title="⚠️ DATA RESET CONFIRMATION",
        description="**Are you absolutely sure you want to reset ALL user data?**\n\n"
                   "This will permanently delete:\n"
                   "• All user balances\n"
                   "• All earning/spending history\n"
                   "• All cooldown timers\n"
                   "• Purchase records\n"
                   "• Invite data\n"
                   "• Anti-spam data\n\n"
                   "**THIS CANNOT BE UNDONE!**",
        color=0xff0000
    )
    
    view = ResetConfirmView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="leaderboard", description="View the top token holders")
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    if not user_data:
        embed = discord.Embed(
            title="📊 Token Leaderboard",
            description="No users have earned tokens yet!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    sorted_users = []
    for user_id, data in user_data.items():
        balance = data.get('balance', 0)
        if balance > 0:
            try:
                user = bot.get_user(int(user_id))
                if user:
                    sorted_users.append({
                        'user': user,
                        'balance': balance,
                        'rank': get_rank(balance)
                    })
            except:
                continue
    
    sorted_users.sort(key=lambda x: x['balance'], reverse=True)
    
    if not sorted_users:
        embed = discord.Embed(
            title="📊 Token Leaderboard",
            description="No users with tokens found!",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    per_page = 10
    max_pages = (len(sorted_users) + per_page - 1) // per_page
    page = max(1, min(page, max_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_users = sorted_users[start_idx:end_idx]
    
    embed = discord.Embed(
        title="📊 Token Leaderboard",
        color=0xFFD700,
        timestamp=datetime.now()
    )
    
    leaderboard_text = ""
    for i, user_data_item in enumerate(page_users, start=start_idx + 1):
        user = user_data_item['user']
        balance = user_data_item['balance']
        rank = user_data_item['rank']
        
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"**{i}.**"
        
        leaderboard_text += f"{medal} **{user.display_name}** - {balance:,} 🪙 {rank}\n"
    
    embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
    
    user_position = None
    for i, user_data_item in enumerate(sorted_users, 1):
        if user_data_item['user'].id == interaction.user.id:
            user_position = i
            break
    
    if user_position and (user_position < start_idx + 1 or user_position > end_idx):
        user_balance = get_user_balance(interaction.user.id)
        user_rank = get_rank(user_balance)
        embed.add_field(
            name="Your Position",
            value=f"**#{user_position}** - {user_balance:,} 🪙 {user_rank}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{max_pages} • {len(sorted_users)} total users")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="adminbalance", description="Check user balance (Admin only)")
async def adminbalance(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    user_id = str(user.id)
    balance = get_user_balance(user.id)
    data = user_data.get(user_id, {})
    earned = data.get('total_earned', 0)
    spent = data.get('total_spent', 0)
    rank = get_rank(balance)
    
    embed = discord.Embed(title=f"💰 {user.display_name}'s Wallet", color=0xFF6B6B)
    embed.add_field(name="Balance", value=f"**{balance:,}** 🪙", inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Spent", value=f"{spent:,} 🪙", inline=True)
    embed.add_field(name="Earned", value=f"{earned:,} 🪙", inline=True)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addtoken", description="Add tokens (Admin only)")
async def addtoken(interaction: discord.Interaction, user: discord.Member, amount: str):  # Changed to string
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    new_balance = update_balance(user.id, parsed_amount)
    await save_data()
    
    await log_action(
        "ADD_TOKENS",
        "💰 Tokens Added",
        f"**{interaction.user.mention}** added **{parsed_amount:,} tokens** to {user.mention}",
        color=0x00ff00,
        user=interaction.user,
        fields=[
            {"name": "Target User", "value": user.mention, "inline": True},
            {"name": "Amount Added", "value": f"{parsed_amount:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )
    
    embed = discord.Embed(title="✅ Tokens Added", color=0x00ff00)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Added", value=f"{parsed_amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removetoken", description="Remove tokens from a user (Admin only)")
async def removetoken(interaction: discord.Interaction, user: discord.Member, amount: str):  # Changed to string
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    current_balance = get_user_balance(user.id)
    if current_balance < parsed_amount:
        await interaction.response.send_message(
            f"❌ User only has {current_balance:,} tokens! Cannot remove {parsed_amount:,} tokens.",
            ephemeral=True
        )
        return
    
    new_balance = update_balance(user.id, -parsed_amount)
    await save_data()
    
    await log_action(
        "REMOVE_TOKENS",
        "💰 Tokens Removed",
        f"**{interaction.user.mention}** removed **{parsed_amount:,} tokens** from {user.mention}",
        color=0xff4444,
        user=interaction.user,
        fields=[
            {"name": "Target User", "value": user.mention, "inline": True},
            {"name": "Amount Removed", "value": f"{parsed_amount:,} 🪙", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:,} 🪙", "inline": True}
        ]
    )
    
    embed = discord.Embed(title="✅ Tokens Removed", color=0xff4444)
    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="Removed", value=f"{parsed_amount:,} 🪙", inline=True)
    embed.add_field(name="New Balance", value=f"{new_balance:,} 🪙", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Giveaway entry button
class GiveawayEnterView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=25)  # 25 second timeout
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.green, emoji="🎉")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.giveaway_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.giveaway_id]
        
        # Check if user already entered
        if str(interaction.user.id) in giveaway['entries']:
            await interaction.response.send_message("❌ You've already entered this giveaway!", ephemeral=True)
            return
        
        # Calculate entries based on roles
        entries = 1  # Base entry
        
        # Add bonus entries for special roles
        for role_id, bonus_entries in PRIORITY_ROLES.items():
            if any(role.id == role_id for role in interaction.user.roles):
                entries += bonus_entries
        
        # Add user to entries
        giveaway['entries'][str(interaction.user.id)] = entries
        giveaway['total_entries'] += entries
        
        await save_data()
        
        role_bonus_text = ""
        for role_id, bonus_entries in PRIORITY_ROLES.items():
            if any(role.id == role_id for role in interaction.user.roles):
                role_bonus_text += f"• <@&{role_id}>: +{bonus_entries} entries\n"
        
        if role_bonus_text:
            bonus_message = f"\n**Role Bonuses:**\n{role_bonus_text}"
        else:
            bonus_message = ""
        
        await interaction.response.send_message(
            f"✅ You've entered the giveaway with **{entries}** entries! Good luck!{bonus_message}",
            ephemeral=True
        )

@bot.tree.command(name="giveaway", description="Start a token giveaway (25 seconds)")
async def giveaway(interaction: discord.Interaction, amount: str, winners: int):  # Changed to string for amount
    # Check cooldown - 30 seconds for giveaways
    if not can_use_short_cooldown(interaction.user.id, "giveaway", 30):
        await interaction.response.send_message("⏰ Please wait 30 seconds before starting another giveaway!", ephemeral=True)
        return
    
    # Parse amount with suffixes
    parsed_amount = parse_amount(amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message("❌ Invalid amount! Use numbers or suffixes like 10k, 1m, 1b", ephemeral=True)
        return
    
    # Validate parameters - Minimum 50 tokens, maximum 5k for giveaway
    if parsed_amount < 50:
        await interaction.response.send_message("❌ Minimum giveaway amount is 50 tokens!", ephemeral=True)
        return
    
    if parsed_amount > 5000:
        await interaction.response.send_message("❌ Maximum giveaway amount is 5,000 tokens!", ephemeral=True)
        return
    
    if winners < 1 or winners > 12:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 12!", ephemeral=True)
        return
    
    # Check daily giveaway limit - Changed from 50000 to 5000
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    if user_id not in giveaway_daily_totals:
        giveaway_daily_totals[user_id] = {}
    
    if today not in giveaway_daily_totals[user_id]:
        giveaway_daily_totals[user_id][today] = 0
    
    # Changed from 50000 to 5000
    if giveaway_daily_totals[user_id][today] + parsed_amount > 5000:
        remaining = 5000 - giveaway_daily_totals[user_id][today]
        await interaction.response.send_message(
            f"❌ You can only giveaway {remaining:,} more tokens today! (5k daily limit)",  # Updated message
            ephemeral=True
        )
        return
    
    # Check if user has enough tokens
    balance = get_user_balance(interaction.user.id)
    if balance < parsed_amount:
        await interaction.response.send_message(f"❌ You need **{parsed_amount - balance:,}** more tokens to start this giveaway!", ephemeral=True)
        return
    
    # Deduct tokens from user
    new_balance = update_balance(interaction.user.id, -parsed_amount)
    giveaway_daily_totals[user_id][today] += parsed_amount
    set_short_cooldown(interaction.user.id, "giveaway")  # Set 3 minute cooldown
    
    # Create giveaway
    giveaway_id = f"{interaction.user.id}_{int(time.time())}"
    prize_per_winner = parsed_amount // winners
    
    active_giveaways[giveaway_id] = {
        'creator': interaction.user.id,
        'amount': parsed_amount,
        'winners': winners,
        'prize_per_winner': prize_per_winner,
        'entries': {},
        'total_entries': 0,
        'created_at': datetime.now().isoformat(),
        'end_time': (datetime.now() + timedelta(seconds=25)).isoformat()  # 25 seconds
    }
    
    await save_data()
    
    # Create embed with improved UI
    embed = discord.Embed(
        title="🎉 TOKEN GIVEAWAY 🎉",
        description=f"Hosted by {interaction.user.mention}",
        color=0xFFD700,
        timestamp=datetime.now()
    )
    
    # Add thumbnail
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1125274830004781156.webp?size=96&quality=lossless")
    
    # Main prize info
    embed.add_field(
        name="🏆 TOTAL PRIZE", 
        value=f"**{parsed_amount:,}** 🪙", 
        inline=True
    )
    embed.add_field(
        name="👑 WINNERS", 
        value=f"**{winners}** lucky winners", 
        inline=True
    )
    embed.add_field(
        name="💰 PRIZE PER WINNER", 
        value=f"**{prize_per_winner:,}** 🪙", 
        inline=True
    )
    
    # Time and entries
    embed.add_field(
        name="⏰ TIME REMAINING", 
        value="**25 seconds**", 
        inline=True
    )
    embed.add_field(
        name="🎫 ENTRIES", 
        value="**0** entries", 
        inline=True
    )

    # Role bonus section
    role_bonus_text = "\n".join([f"<@&{role_id}>: **+{bonus} entries**" for role_id, bonus in PRIORITY_ROLES.items()])
    if role_bonus_text:
        embed.add_field(
            name="🌟 ROLE BONUSES", 
            value=role_bonus_text, 
            inline=False
        )
    
    # Footer with instructions
    embed.set_footer(
        text="Click the button below to enter! • Ends in 25 seconds",
        icon_url="https://cdn.discordapp.com/emojis/1125272129399365632.webp?size=96&quality=lossless"
    )
    
    view = GiveawayEnterView(giveaway_id)
    await interaction.response.send_message(embed=embed, view=view)
    
    # Update the giveaway message every 5 seconds with progress
    async def update_giveaway_message():
        for i in range(5):  # 5 updates (25 seconds total)
            await asyncio.sleep(5)
            
            if giveaway_id not in active_giveaways:
                break
                
            giveaway = active_giveaways[giveaway_id]
            time_left = 20 - (i * 5)
            
            # Update embed
            updated_embed = discord.Embed(
                title="🎉 TOKEN GIVEAWAY 🎉",
                description=f"Hosted by {interaction.user.mention}",
                color=0xFFD700,
                timestamp=datetime.now()
            )
            
            updated_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1125274830004781156.webp?size=96&quality=lossless")
            updated_embed.add_field(name="🏆 TOTAL PRIZE", value=f"**{parsed_amount:,}** 🪙", inline=True)
            updated_embed.add_field(name="👑 WINNERS", value=f"**{winners}** lucky winners", inline=True)
            updated_embed.add_field(name="💰 PRIZE PER WINNER", value=f"**{prize_per_winner:,}** 🪙", inline=True)
            updated_embed.add_field(name="⏰ TIME REMAINING", value=f"**{time_left} seconds**", inline=True)
            updated_embed.add_field(name="🎫 ENTRIES", value=f"**{giveaway['total_entries']:,}** entries", inline=True)
            
            # Calculate approximate chances
            if giveaway['total_entries'] > 0:
                approx_chance = min(100, round((winners / giveaway['total_entries']) * 100, 1))
                updated_embed.add_field(name="🎲 YOUR CHANCES", value=f"**~{approx_chance}%** chance to win", inline=True)
            else:
                updated_embed.add_field(name="🎲 YOUR CHANCES", value="Be the first to enter!", inline=True)
            
            if role_bonus_text:
                updated_embed.add_field(name="🌟 ROLE BONUSES", value=role_bonus_text, inline=False)
            
            updated_embed.set_footer(
                text=f"Click the button below to enter! • Ends in {time_left} seconds",
                icon_url="https://cdn.discordapp.com/emojis/1125272129399365632.webp?size=96&quality=lossless"
            )
            
            try:
                await interaction.edit_original_response(embed=updated_embed, view=view)
            except:
                break
    
    # Start the update task
    asyncio.create_task(update_giveaway_message())
    
    # Wait for giveaway to end
    await asyncio.sleep(25)
    
    # End the giveaway
    if giveaway_id in active_giveaways:
        giveaway = active_giveaways[giveaway_id]
        
        if giveaway['total_entries'] > 0:
            # Select winners
            all_entries = []
            for user_id, entries in giveaway['entries'].items():
                all_entries.extend([user_id] * entries)
            
            # Ensure we don't try to select more winners than entries
            winner_count = min(giveaway['winners'], len(set(all_entries)))
            if winner_count > 0:
                selected_winners = random.sample(all_entries, winner_count)
                unique_winners = list(set(selected_winners))
                
                # Distribute prizes
                winner_mentions = []
                for winner_id in unique_winners:
                    try:
                        winner = await bot.fetch_user(int(winner_id))
                        update_balance(winner.id, giveaway['prize_per_winner'])
                        winner_mentions.append(winner.mention)
                    except:
                        continue
                
                # Create clean results embed
                result_embed = discord.Embed(
                    title="🎊 GIVEAWAY ENDED 🎊",
                    description=f"**Hosted by:** {interaction.user.mention}",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                # Results summary
                result_embed.add_field(name="🏆 Total Prize", value=f"**{giveaway['amount']:,}** 🪙", inline=True)
                result_embed.add_field(name="👑 Winners", value=f"**{len(unique_winners)}**", inline=True)
                result_embed.add_field(name="💰 Prize Each", value=f"**{giveaway['prize_per_winner']:,}** 🪙", inline=True)
                
                # Winners list
                if winner_mentions:
                    winners_text = "\n".join(winner_mentions)
                    result_embed.add_field(
                        name="🎉 Congratulations to the winners!", 
                        value=winners_text, 
                        inline=False
                    )
                
                result_embed.set_footer(text="Tokens have been distributed to winners!")
                
                # Log the giveaway
                await log_action(
                    "GIVEAWAY",
                    "🎉 Giveaway Completed",
                    f"**{interaction.user.mention}** hosted a giveaway of **{giveaway['amount']:,} tokens**",
                    color=0xFFD700,
                    user=interaction.user,
                    fields=[
                        {"name": "Total Prize", "value": f"{giveaway['amount']:,} 🪙", "inline": True},
                        {"name": "Winners", "value": f"{len(unique_winners)}", "inline": True},
                        {"name": "Prize per Winner", "value": f"{giveaway['prize_per_winner']:,} 🪙", "inline": True},
                        {"name": "Winners", "value": "\n".join(winner_mentions) if winner_mentions else "No winners", "inline": False}
                    ]
                )
                
                # Update the message
                try:
                    await interaction.edit_original_response(embed=result_embed, view=None)
                except Exception as e:
                    print(f"⚠️ Error updating giveaway message: {e}")
                    
            else:
                # No valid winners found
                refund_embed = discord.Embed(
                    title="🎉 GIVEAWAY ENDED",
                    description="No valid winners could be selected. Tokens have been refunded.",
                    color=0xff4444
                )
                
                # Refund the creator
                update_balance(interaction.user.id, giveaway['amount'])
                giveaway_daily_totals[user_id][today] -= giveaway['amount']
                
                try:
                    await interaction.edit_original_response(embed=refund_embed, view=None)
                except:
                    pass
                
        else:
            # No entries, refund the creator
            update_balance(interaction.user.id, giveaway['amount'])
            giveaway_daily_totals[user_id][today] -= giveaway['amount']
            
            refund_embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED",
                description="No one entered the giveaway. Tokens have been refunded.",
                color=0xff4444
            )
            
            try:
                await interaction.edit_original_response(embed=refund_embed, view=None)
            except:
                pass
        
        # Remove giveaway from active list
        del active_giveaways[giveaway_id]
        await save_data()

@bot.tree.command(name="giveawayinfo", description="Check your daily giveaway limits")
async def giveawayinfo(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    today = datetime.now().date().isoformat()
    
    daily_gifted = giveaway_daily_totals.get(user_id, {}).get(today, 0)
    daily_giveaway = giveaway_daily_totals.get(user_id, {}).get(today, 0)
    
    embed = discord.Embed(
        title="📊 Giveaway Information",
        description="Your daily limits and usage",
        color=0x0099ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🎁 Daily Gift Limit", 
        value=f"**{daily_gifted:,}/3,000** 🪙 used today\n*Resets at midnight*", 
        inline=True
    )
    
    # Changed from 50,000 to 5,000
    embed.add_field(
        name="🎉 Daily Giveaway Limit", 
        value=f"**{daily_giveaway:,}/5,000** 🪙 used today\n*Resets at midnight*", 
        inline=True
    )
    
    # Calculate time until reset
    now = datetime.now()
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_until_reset = next_midnight - now
    hours, remainder = divmod(time_until_reset.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed.add_field(
        name="⏰ Time Until Reset", 
        value=f"**{hours}h {minutes}m {seconds}s**", 
        inline=False
    )
    
    # Role bonus info
    role_bonus_text = "\n".join([f"<@&{role_id}>: +{bonus} entries" for role_id, bonus in PRIORITY_ROLES.items()])
    if role_bonus_text:
        embed.add_field(
            name="🌟 Role Bonuses", 
            value=role_bonus_text, 
            inline=False
        )
    
    embed.set_footer(text="Host giveaways to share your wealth!")
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="about")
async def about(ctx):
    """Traditional text command for bot info"""
    embed = discord.Embed(
        title="🤖 Bot Commands Guide",
        description="Here are all the commands you can use to earn and spend tokens!",
        timestamp=datetime.now()
    )
    
    # Economy Commands
    embed.add_field(
        name="💰 Economy Commands",
        value=(
            "`/balance` - Check your token balance and stats\n"
            "`/daily` - Claim daily tokens (24h cooldown)\n"
            "`/work` - Work for tokens (3h cooldown)\n"
            "`/crime` - Risky crime for tokens (1h cooldown)\n"
            "`/coinflip <amount> <heads/tails>` - Bet tokens on coinflip\n"
            "`/duel <user> <amount>` - Challenge someone to coinflip\n"
            "`/gift <user> <amount>` - Gift tokens to another user\n"
            "`/giveaway <amount> <winners>` - Start a token giveaway\n"
            "`/giveawayinfo` - Check your daily limits\n"
            "`/mines <amount> <mines>` - Play mines game (find gems to multiply your bet!)\n"
            "`/invitespanel` - View invite rewards and manage invites"
        ),
        inline=False
    )
    
    # Shop Commands
    embed.add_field(
        name="🛒 Shop Commands",
        value=(
            "`/shop` - Browse available items for purchase\n"
            "`/buy <item_name> [quantity]` - Buy items from the shop"
        ),
        inline=False
    )
    
    # Info Commands
    embed.add_field(
        name="📊 Information Commands",
        value=(
            "`/leaderboard [page]` - View top token holders\n"
            "`!about` - Show this help message"
        ),
        inline=False
    )
    
    # Admin Commands
    if is_admin(ctx.author):
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "`/addtoken <user> <amount>` - Add tokens to user\n"
                "`/removetoken <user> <amount>` - Remove tokens from user\n"
                "`/adminbalance <user>` - Check user's balance\n"
                "`/addshop` - Manage shop items\n"
                "`/resetdata <code>` - Reset all user data\n"
                "`/config_cf` - Configure coinflip settings"
            ),
            inline=False
        )
    
    # Token Earning Info
    embed.add_field(
        name="💬 Passive Earning",
        value="You earn **1-5 tokens** automatically for each message you send in the server!",
        inline=False
    )
    
    # Rank System
    embed.add_field(
        name="🏆 Rank System",
        value=(
            "🔵 **Starter** - 0+ tokens\n"
            "🟢 **Silver** - 1,000+ tokens\n"
            "🥉 **Gold** - 5,000+ tokens\n"
            "🥈 **Premium** - 10,000+ tokens\n"
            "🥇 **VIP** - 20,000+ tokens\n"
            "💎 **Elite** - 50,000+ tokens\n"
            "🏆 **Legendary** - 100,000+ tokens"
        ),
        inline=False
    )
    
    # Giveaway Info
    embed.add_field(
        name="🎉 Giveaway System",
        value=(
            "• Anyone can host giveaways\n"
            "• Maximum prize: 5,000 tokens per giveaway\n"
            "• Maximum 5,000 tokens per day per user\n"
            "• 1-12 winners\n"
            "• 25 second duration\n"
            "• Special roles get bonus entries:\n"
            "  - <@&1410917252190179369>: +7 entries\n"
            "  - <@&1410917163933503521>: +5 entries\n"
            "  - <@&1410917146459897928>: +3 entries"
        ),
        inline=False
    )
    
    # Gift Limits
    embed.add_field(
        name="🎁 Gift Limits",
        value=(
            "• Maximum 3,000 tokens per day per user\n"
            "• 3 second cooldown between gifts\n"
            "• Check `/giveawayinfo` for your daily usage"
        ),
        inline=False
    )
    
    # Mines Game Info
    embed.add_field(
        name="💎 Mines Game",
        value=(
            "• Bet 100-1,000 tokens\n"
            "• Choose 1-24 mines on a 5x5 board\n"
            "• Click squares to reveal gems (💎)\n"
            "• Avoid mines (💣) or lose your bet\n"
            "• Multiplier increases with each safe spot found\n"
            "• Cash out anytime to collect your winnings!"
        ),
        inline=False
    )
    
    # Invite System
    embed.add_field(
        name="🔗 Invite Rewards",
        value=(
            "• Earn **300 tokens** for each valid invite\n"
            "• Invited accounts must be **30+ days old**\n"
            "• Use `/invitespanel` to manage your invites\n"
            "• Generate personal invite links\n"
            "• Track your invite statistics"
        ),
        inline=False
    )
    
    # Anti-Spam System
    embed.add_field(
        name="⚠️ Anti-Spam System",
        value=(
            "• Sending messages too quickly will deduct **50 tokens**\n"
            "• Avoid sending more than 5 messages in 10 seconds\n"
            "• System helps maintain healthy chat environment"
        ),
        inline=False
    )
    
    # Amount Formatting
    embed.add_field(
        name="💡 Amount Formatting",
        value=(
            "You can use suffixes for large amounts:\n"
            "• **1k** = 1,000 tokens\n"
            "• **1m** = 1,000,000 tokens\n"
            "• **1b** = 1,000,000,000 tokens\n"
            "• Works in all commands that accept amounts!"
        ),
        inline=False
    )
    
    # Tips
    embed.add_field(
        name="💡 Tips",
        value=(
            "• Use `/daily` every 24 hours for free tokens\n"
            "• `/work` is safe but has a 3-hour cooldown\n"
            "• `/crime` is risky but can give more tokens\n"
            "• Chat regularly to earn passive tokens\n"
            "• Check `/leaderboard` to see your ranking\n"
            "• Host giveaways to share your wealth!\n"
            "• Try the mines game for high-risk, high-reward gameplay\n"
            "• Invite friends to earn bonus tokens\n"
            "• Use amount suffixes (k, m, b) for convenience"
        ),
        inline=False
    )
    
    embed.set_footer(text="Need help? Ask an admin!")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable not found!")
        print("💡 Set it in Railway dashboard under Variables tab")
        sys.exit(1)
    
    try:
        print("🔑 Token found, connecting to Discord...")
        # Register cleanup handler
        import signal
        def handle_exit(signum, frame):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(force_save_on_exit())
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, handle_exit)
        signal.signal(signal.SIGINT, handle_exit)
        
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

import os
# DISABLE VOICE AT OS LEVEL BEFORE ANY IMPORTS
os.environ["DISCORD_INTERACTIONS"] = "0"
os.environ["PYTHONWARNINGS"] = "ignore"

# Keep-alive server first
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

@app.route('/health')
def health():
    return "OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
print("✅ Keep-alive server started")

# NOW import discord
import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import datetime
from datetime import timezone
from typing import Dict, Set, List
import asyncio
# ========== END KEEP ALIVE ==========
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Handles errors in slash commands"""
    if isinstance(error, app_commands.CommandInvokeError):
        # Get the original error
        original = error.original
        
        # Log the full error
        print(f"🚨 Command error in '{interaction.command.name}':")
        print(f"   User: {interaction.user}")
        print(f"   Error: {original}")
        print(f"   Traceback: {error}")
        
        # Send user-friendly message
        await interaction.response.send_message(
            f"❌ Command failed: {type(original).__name__}\n"
            "The bot owner has been notified.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Command error: {error}",
            ephemeral=True
        )
# ========== CONFIGURATION ==========
TOKEN = os.getenv("TOKEN") 

# Channel lists (from your configuration)
EXCLUSIVE_CHANNELS = [
    "🫳drops", "🔎reviews", "🔔entries-alerts🥬"
]

COMMON_CHANNELS = [
    "👋welcome", "📥testimonials", "🛄resources-free", "❓faq-ongoing",
    "🌌vision-purpose", "🪡upgrade-spot", "📣announcements", "🍬promo-codes",
    "🏆leaderboard", "🛖dugout-forum", "🧘‍♂️mental-emotional", "🏞️park-chat",
    "🙉whispering-wall", "🧭journey-journaling", "🎇backtests", "📊beowbu-stats",
    "🧀pnl-history", "🎁giveaways", "🎼songs-metaphors", "🐦tilt-alerts"
]

# Thread configurations
EXCLUSIVE_THREADS = [
    "IB Trades", "RY & RB Trades", "Rev ST Trades", "Kage 9 Setups Trades (Exclusive)"
]

COMMON_THREADS = [
    "Request + Complaints", "Den's Functioning", "😐Boring Wins & Neutral Reviews",
    "🧠 Pattern-Forensics", "🏄‍♂️ Urge Surfing", "📖 Story vs. Data", 
    "⚙️ Pre-Mortem & Pre-Commitment"
]

# Voice channels
EXCLUSIVE_VC = ["📈 Live Trading 🗣️", "🥦 Group Class"]
COMMON_VC = ["🕯️Live Trading 🔇", "🙉 Edgekeeper's Speculations"]

# Scoring rules
POINTS = {
    "common_channel": 5,
    "exclusive_channel": 7,
    "thread": 6,
    "reaction": 1,
    "reply_mention": 3,
    "first_message": 10,
    "voice_minute": 1  # per 5 minutes
}

# Daily limits
DAILY_LIMITS = {
    "common_channel": 2,
    "exclusive_channel": 2,
    "thread": 4,
    "reaction": 12,
    "reply_mention": 2,
    "voice_points": 60
}

# Streak rewards (days: bonus_points)
STREAK_REWARDS = {3: 18, 7: 50, 14: 110, 30: 250}

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  total_points INTEGER DEFAULT 0,
                  current_streak INTEGER DEFAULT 0,
                  longest_streak INTEGER DEFAULT 0,
                  last_active_date TEXT)''')
    
    # Daily stats table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                 (user_id INTEGER, 
                  date TEXT,
                  common_messages INTEGER DEFAULT 0,
                  exclusive_messages INTEGER DEFAULT 0,
                  thread_messages INTEGER DEFAULT 0,
                  reactions INTEGER DEFAULT 0,
                  reply_mentions INTEGER DEFAULT 0,
                  voice_points INTEGER DEFAULT 0,
                  first_message_bonus INTEGER DEFAULT 0,
                  PRIMARY KEY (user_id, date))''')
    
    # Voice tracking
    c.execute('''CREATE TABLE IF NOT EXISTS voice_sessions
                 (user_id INTEGER,
                  channel_id INTEGER,
                  join_time TEXT,
                  PRIMARY KEY (user_id, channel_id))''')
    
    conn.commit()
    return conn

# ========== BOT SETUP ==========
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)
db = init_db()

# ========== HELPER FUNCTIONS ==========
def get_today():
    return dt.now(datetime.timezone.utc).strftime("%Y-%m-%d")

def get_user_stats(user_id, date=None):
    if date is None:
        date = get_today()
    
    c = db.cursor()
    c.execute("SELECT * FROM daily_stats WHERE user_id = ? AND date = ?", (user_id, date))
    row = c.fetchone()
    
    if row:
        return {
            'common_messages': row[2],
            'exclusive_messages': row[3],
            'thread_messages': row[4],
            'reactions': row[5],
            'reply_mentions': row[6],
            'voice_points': row[7],
            'first_message_bonus': row[8]
        }
    return None

def update_daily_stat(user_id, stat_type, value=1):
    today = get_today()
    c = db.cursor()
    
    # Get existing or create new
    stats = get_user_stats(user_id, today)
    if stats is None:
        c.execute('''INSERT INTO daily_stats 
                     (user_id, date) VALUES (?, ?)''', (user_id, today))
        stats = {k: 0 for k in ['common_messages', 'exclusive_messages', 
                               'thread_messages', 'reactions', 'reply_mentions',
                               'voice_points', 'first_message_bonus']}
    
    # Check if under daily limit
    if stat_type in ['common_messages', 'exclusive_messages', 'thread_messages',
                    'reactions', 'reply_mentions']:
        limit_key = stat_type.replace('_messages', '_channel') if 'messages' in stat_type else stat_type
        limit = DAILY_LIMITS.get(limit_key, 999)
        if stats[stat_type] >= limit:
            return False, f"Daily limit reached for {stat_type.replace('_', ' ')}"
    
    # Update the stat
    c.execute(f'''UPDATE daily_stats 
                  SET {stat_type} = {stat_type} + ? 
                  WHERE user_id = ? AND date = ?''', (value, user_id, today))
    
    # Update total points
    points_to_add = POINTS.get(stat_type.replace('_messages', '_channel').replace('_bonus', ''), 0)
    if stat_type == 'first_message_bonus':
        points_to_add = POINTS['first_message']
    
    c.execute('''UPDATE users 
                 SET total_points = total_points + ? 
                 WHERE user_id = ?''', (points_to_add, user_id))
    
    db.commit()
    return True, f"+{points_to_add} points"

def check_first_message(user_id):
    today = get_today()
    c = db.cursor()
    
    # Check if user already got first message bonus today
    stats = get_user_stats(user_id, today)
    if stats and stats['first_message_bonus'] > 0:
        return False
    
    # Check if user has any messages today
    c.execute('''SELECT common_messages + exclusive_messages + thread_messages 
                 FROM daily_stats 
                 WHERE user_id = ? AND date = ?''', (user_id, today))
    result = c.fetchone()
    
    if result and result[0] > 0:
        # This is not their first message today
        return False
    
    return True

def update_streak(user_id):
    today = get_today()
    yesterday = (dt.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    c = db.cursor()
    
    # Get user's streak info
    c.execute('''SELECT current_streak, longest_streak, last_active_date 
                 FROM users WHERE user_id = ?''', (user_id,))
    row = c.fetchone()
    
    if not row:
        # New user
        c.execute('''INSERT INTO users 
                     (user_id, current_streak, longest_streak, last_active_date) 
                     VALUES (?, 1, 1, ?)''', (user_id, today))
        db.commit()
        return 1
    
    current_streak, longest_streak, last_active = row
    
    if last_active == today:
        # Already updated today
        return current_streak
    
    if last_active == yesterday:
        # Consecutive day
        current_streak += 1
    else:
        # Streak broken
        current_streak = 1
    
    # Update longest streak if needed
    if current_streak > longest_streak:
        longest_streak = current_streak
    
    # Check for streak rewards
    streak_bonus = 0
    for days, bonus in STREAK_REWARDS.items():
        if current_streak == days:
            streak_bonus = bonus
            c.execute('''UPDATE users 
                         SET total_points = total_points + ? 
                         WHERE user_id = ?''', (bonus, user_id))
            break
    
    # Update user record
    c.execute('''UPDATE users 
                 SET current_streak = ?, longest_streak = ?, last_active_date = ? 
                 WHERE user_id = ?''', 
                 (current_streak, longest_streak, today, user_id))
    
    db.commit()
    return current_streak, streak_bonus

def get_weekend_multiplier():
    today = dt.utcnow()
    if today.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return 1.5
    return 1.0

# ========== EVENT HANDLERS ==========
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    reset_daily_stats.start()
    check_voice_channels.start()

@bot.event
async def on_message(message):
    # Ignore bot messages and DMs
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    # Check if it's a command
    if message.content.startswith('/'):
        await bot.process_commands(message)
        return
    
    user_id = message.author.id
    channel_name = message.channel.name if hasattr(message.channel, 'name') else ""
    
    # Determine channel type and points
    points_awarded = 0
    stat_type = None
    is_thread = isinstance(message.channel, discord.Thread)
    
    if is_thread:
        thread_name = message.channel.name
        if thread_name in EXCLUSIVE_THREADS:
            stat_type = 'thread_messages'
        elif thread_name in COMMON_THREADS:
            stat_type = 'thread_messages'
        else:
            # Threads not in our list get no points
            await bot.process_commands(message)
            return
    else:
        if channel_name in EXCLUSIVE_CHANNELS:
            stat_type = 'exclusive_messages'
        elif channel_name in COMMON_CHANNELS:
            stat_type = 'common_messages'
        else:
            # Channel not in our list gets no points
            await bot.process_commands(message)
            return
    
    # Apply weekend multiplier
    multiplier = get_weekend_multiplier()
    
    # Check first message bonus
    first_msg_bonus = 0
    if check_first_message(user_id):
        success, msg = update_daily_stat(user_id, 'first_message_bonus')
        if success:
            first_msg_bonus = POINTS['first_message'] * multiplier
    
    # Update message count
    success, msg = update_daily_stat(user_id, stat_type)
    if success:
        base_points = POINTS[stat_type.replace('_messages', '_channel')]
        points_awarded = base_points * multiplier
        
        # Check for reply/mention bonus
        reply_mention_bonus = 0
        if message.reference or any(m.mention in message.content for m in message.mentions if m != message.author):
            reply_success, reply_msg = update_daily_stat(user_id, 'reply_mentions')
            if reply_success:
                reply_mention_bonus = POINTS['reply_mention'] * multiplier
        
        # Update streak
        streak_info = update_streak(user_id)
        streak_bonus = streak_info[1] if isinstance(streak_info, tuple) else 0
        
        total_points = points_awarded + first_msg_bonus + reply_mention_bonus + streak_bonus
        
        # Send success message (optional, can remove)
        if total_points > 0:
            bonus_text = ""
            if first_msg_bonus > 0:
                bonus_text += f" (+{first_msg_bonus} first message)"
            if reply_mention_bonus > 0:
                bonus_text += f" (+{reply_mention_bonus} reply/mention)"
            if streak_bonus > 0:
                bonus_text += f" (+{streak_bonus} streak bonus)"
            
            if multiplier > 1:
                bonus_text += f" (Weekend {multiplier}x)"
            
            if len(bonus_text) > 0:
                try:
                    await message.channel.send(f"🎯 {message.author.mention}: {points_awarded}pts{bonus_text}", delete_after=5)
                except:
                    pass
    
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Check if user has already reacted to this message 2 times
    message = reaction.message
    user_reactions = [r for r in message.reactions if user in await r.users().flatten()]
    
    if len(user_reactions) > 2:
        return  # Max 2 reactions per message
    
    user_id = user.id
    
    # Check daily reaction limit
    stats = get_user_stats(user_id)
    if stats and stats['reactions'] >= DAILY_LIMITS['reaction']:
        return
    
    # Award points
    success, msg = update_daily_stat(user_id, 'reactions')
    if success:
        points = POINTS['reaction'] * get_weekend_multiplier()
        update_streak(user_id)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    c = db.cursor()
    
    # User joined a voice channel
    if after.channel and after.channel.name in EXCLUSIVE_VC + COMMON_VC:
        # Check if at least 3 users in channel
        if len(after.channel.members) >= 3:
            c.execute('''INSERT OR REPLACE INTO voice_sessions 
                         (user_id, channel_id, join_time) 
                         VALUES (?, ?, ?)''', 
                         (member.id, after.channel.id, dt.utcnow().isoformat()))
            db.commit()
    
    # User left a voice channel
    elif before.channel:
        c.execute('''SELECT join_time FROM voice_sessions 
                     WHERE user_id = ? AND channel_id = ?''', 
                     (member.id, before.channel.id))
        row = c.fetchone()
        
        if row:
            join_time = dt.fromisoformat(row[0])
            duration = (dt.utcnow() - join_time).total_seconds() / 60  # in minutes
            
            # Calculate points: 1pt per 5 minutes
            points_earned = int(duration / 5)
            
            if points_earned > 0:
                # Check daily voice limit
                stats = get_user_stats(member.id)
                current_voice = stats['voice_points'] if stats else 0
                
                # Apply limit
                points_earned = min(points_earned, DAILY_LIMITS['voice_points'] - current_voice)
                
                if points_earned > 0:
                    # Apply weekend multiplier
                    points_earned = int(points_earned * get_weekend_multiplier())
                    
                    # Update points
                    success, msg = update_daily_stat(member.id, 'voice_points', points_earned)
                    if success:
                        update_streak(member.id)
            
            # Remove session
            c.execute('''DELETE FROM voice_sessions 
                         WHERE user_id = ? AND channel_id = ?''', 
                         (member.id, before.channel.id))
            db.commit()

# ========== BACKGROUND TASKS ==========
@tasks.loop(minutes=1)
async def check_voice_channels():
    c = db.cursor()
    
    # Get all active voice sessions
    c.execute('''SELECT user_id, channel_id, join_time FROM voice_sessions''')
    sessions = c.fetchall()
    
    for user_id, channel_id, join_time_str in sessions:
        join_time = dt.fromisoformat(join_time_str)
        duration = (dt.utcnow() - join_time).total_seconds() / 60  # minutes
        
        # Award points every 5 minutes
        if duration >= 5:
            # Check channel still has ≥3 users
            try:
                channel = bot.get_channel(channel_id)
                if channel and len(channel.members) >= 3:
                    # Check daily limit
                    stats = get_user_stats(user_id)
                    current_voice = stats['voice_points'] if stats else 0
                    
                    if current_voice < DAILY_LIMITS['voice_points']:
                        points = 1 * get_weekend_multiplier()
                        success, msg = update_daily_stat(user_id, 'voice_points', points)
                        
                        if success:
                            update_streak(user_id)
                            
                            # Update join time for next interval
                            new_join_time = (dt.utcnow() - datetime.timedelta(
                                minutes=duration % 5)).isoformat()
                            c.execute('''UPDATE voice_sessions 
                                         SET join_time = ? 
                                         WHERE user_id = ? AND channel_id = ?''',
                                         (new_join_time, user_id, channel_id))
                            db.commit()
            except:
                pass

@tasks.loop(hours=24)
async def reset_daily_stats():
    # This runs daily at midnight UTC
    await bot.wait_until_ready()
    
    # Reset all daily counters in application memory
    # The database uses date-based tracking, so no reset needed
    print("Daily reset completed. New day started!")
    
    # Announce in leaderboard channel if it exists
    for guild in bot.guilds:
        leaderboard_channel = discord.utils.get(guild.channels, name="🏆leaderboard")
        if leaderboard_channel:
            await leaderboard_channel.send("🌅 New day! Daily counters have been reset. Good luck everyone!")

# ========== COMMANDS ==========
@bot.tree.command(name="leaderboard", description="Show the top 10 users")
@app_commands.describe(period="Time period: 'daily' or 'all-time'")
async def leaderboard(interaction: discord.Interaction, period: str = "all-time"):
    c = db.cursor()
    
    if period.lower() in ["day", "today", "daily"]:
        today = get_today()
        c.execute('''SELECT u.user_id, u.total_points - 
                     (SELECT COALESCE(SUM(d.common_messages * ? + d.exclusive_messages * ? + 
                     d.thread_messages * ? + d.reactions * ? + d.reply_mentions * ? + 
                     d.voice_points + d.first_message_bonus), 0)
                      FROM daily_stats d 
                      WHERE d.user_id = u.user_id AND d.date < ?)
                     FROM users u
                     ORDER BY (u.total_points - 
                     (SELECT COALESCE(SUM(d.common_messages * ? + d.exclusive_messages * ? + 
                     d.thread_messages * ? + d.reactions * ? + d.reply_mentions * ? + 
                     d.voice_points + d.first_message_bonus), 0)
                      FROM daily_stats d 
                      WHERE d.user_id = u.user_id AND d.date < ?)) DESC
                     LIMIT 10''',
                     (POINTS['common_channel'], POINTS['exclusive_channel'],
                      POINTS['thread'], POINTS['reaction'], POINTS['reply_mention'],
                      today, POINTS['common_channel'], POINTS['exclusive_channel'],
                      POINTS['thread'], POINTS['reaction'], POINTS['reply_mention'], today))
        title = "📊 Today's Leaderboard"
    else:
        c.execute('''SELECT user_id, total_points FROM users 
                     ORDER BY total_points DESC LIMIT 10''')
        title = "🏆 All-Time Leaderboard"
    
    top_users = c.fetchall()
    
    embed = discord.Embed(title=title, color=0x00ff00)
    
    for i, (user_id, points) in enumerate(top_users, 1):
        user = interaction.guild.get_member(user_id)
        username = user.display_name if user else f"User {user_id}"
        
        # Get streak info
        c.execute('''SELECT current_streak, longest_streak 
                     FROM users WHERE user_id = ?''', (user_id,))
        streak_info = c.fetchone()
        streak_text = f"🔥 {streak_info[0]} day streak" if streak_info else ""
        
        embed.add_field(
            name=f"{i}. {username}",
            value=f"**{points} pts** {streak_text}",
            inline=False
        )
    
    # Add footer with reset time
    embed.set_footer(text="Daily reset at midnight UTC | Weekend: 1.5x points")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Test if bot responds")
async def ping(interaction: discord.Interaction):
    """Simple ping command"""
    await interaction.response.send_message("🏓 Pong! Bot is working!", ephemeral=False)

@bot.tree.command(name="mystats", description="Check your points, rank, and daily progress")
async def mystats(interaction: discord.Interaction):
    user_id = 	interaction.user.id
    today = get_today()
    
    c = db.cursor()
    
    # Get user's rank
    c.execute('''SELECT user_id, total_points FROM users 
                 ORDER BY total_points DESC''')
    all_users = c.fetchall()
    
    user_rank = None
    for i, (uid, points) in enumerate(all_users, 1):
        if uid == user_id:
            user_rank = i
            total_users = len(all_users)
            user_points = points
            break
    
    # Get streak info
    c.execute('''SELECT current_streak, longest_streak 
                 FROM users WHERE user_id = ?''', (user_id,))
    streak_info = c.fetchone()
    
    if not streak_info or user_rank is None:
        await interaction.response.send_message("You haven't earned any points yet! Start chatting!")
        return
    
    current_streak, longest_streak = streak_info
    
    # Get today's stats
    stats = get_user_stats(user_id, today)
    
    embed = discord.Embed(
        title=f"📊 {interaction.user.display_name}'s Stats",
        color=0x7289da
    )
    
    # Rank and points
    embed.add_field(
        name="Rank & Points", 
        value=f"**#{user_rank}** of {total_users} users\n**{user_points}** total points", 
        inline=True
    )
    
    # Streaks
    embed.add_field(
        name="Streaks", 
        value=f"🔥 **{current_streak}** day streak\n🏆 **{longest_streak}** day record", 
        inline=True
    )
    
    # Today's progress
    if stats:
        limits_text = ""
        if stats['common_messages'] > 0 or stats['exclusive_messages'] > 0 or stats['thread_messages'] > 0:
            limits_text += f"Messages: {stats['common_messages']}/{DAILY_LIMITS['common_channel']} common, "
            limits_text += f"{stats['exclusive_messages']}/{DAILY_LIMITS['exclusive_channel']} exclusive, "
            limits_text += f"{stats['thread_messages']}/{DAILY_LIMITS['thread']} thread\n"
        
        if stats['reactions'] > 0:
            limits_text += f"Reactions: {stats['reactions']}/{DAILY_LIMITS['reaction']}\n"
        
        if stats['reply_mentions'] > 0:
            limits_text += f"Reply/Mentions: {stats['reply_mentions']}/{DAILY_LIMITS['reply_mention']}\n"
        
        if stats['voice_points'] > 0:
            limits_text += f"Voice Points: {stats['voice_points']}/{DAILY_LIMITS['voice_points']}\n"
        
        if stats['first_message_bonus'] > 0:
            limits_text += "✅ First message bonus claimed today!\n"
        
        embed.add_field(
            name="📈 Today's Progress", 
            value=limits_text or "No activity today yet!", 
            inline=False
        )
    
    # Calculate remaining points
    if stats:
        remaining = 0
        # Messages
        remaining += (DAILY_LIMITS['common_channel'] - stats['common_messages']) * POINTS['common_channel']
        remaining += (DAILY_LIMITS['exclusive_channel'] - stats['exclusive_messages']) * POINTS['exclusive_channel']
        remaining += (DAILY_LIMITS['thread'] - stats['thread_messages']) * POINTS['thread']
        # Reactions
        remaining += (DAILY_LIMITS['reaction'] - stats['reactions']) * POINTS['reaction']
        # Reply mentions
        remaining += (DAILY_LIMITS['reply_mention'] - stats['reply_mentions']) * POINTS['reply_mention']
        # Voice
        remaining += (DAILY_LIMITS['voice_points'] - stats['voice_points'])
        # First message bonus
        if stats['first_message_bonus'] == 0:
            remaining += POINTS['first_message']
        
        # Apply weekend multiplier
        remaining = int(remaining * get_weekend_multiplier())
        
        if remaining > 0:
            embed.add_field(
                name="🎯 Points Available Today", 
                value=f"**{remaining}** points still up for grabs!", 
                inline=False
            )
    
    # Weekend bonus notice
    if get_weekend_multiplier() > 1:
        embed.add_field(
            name="🎉 Bonus", 
            value="Weekend 1.5x multiplier active!", 
            inline=False
        )
    
    # Add rank progress bar visualization
    if total_users > 1:
        percentile = ((total_users - user_rank) / (total_users - 1)) * 100
        progress_bar = "█" * int(percentile / 10) + "░" * (10 - int(percentile / 10))
        embed.add_field(
            name="Leaderboard Position", 
            value=f"Top **{percentile:.1f}%**\n`[{progress_bar}]`", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="top10", description="Show top 10 users")
async def top10(interaction: discord.Interaction):
    await leaderboard(interaction: discord.Interaction, "all-time")

@bot.tree.command(name="adjust", description="[ADMIN] Adjust user points")
@commands.has_permissions(administrator=True)
async def adjust_points(interaction: discord.Interaction, member: discord.Member, points: int):
    c = db.cursor()
    c.execute('''UPDATE users 
                 SET total_points = total_points + ? 
                 WHERE user_id = ?''', (points, member.id))
    
    if c.rowcount == 0:
        c.execute('''INSERT INTO users (user_id, total_points) 
                     VALUES (?, ?)''', (member.id, max(points, 0)))
    
    db.commit()
    
    action = "added" if points > 0 else "removed"
    await interaction.response.send_message(f"✅ {abs(points)} points {action} from {member.display_name}")

@bot.tree.command(name="resetuser", description="[ADMIN] Reset user's stats")
@commands.has_permissions(administrator=True)
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    c = db.cursor()
    c.execute('''DELETE FROM users WHERE user_id = ?''', (member.id,))
    c.execute('''DELETE FROM daily_stats WHERE user_id = ?''', (member.id,))
    db.commit()
    await interaction.response.send_message(f"✅ {member.display_name}'s stats have been reset")

@bot.tree.command(name="help", description="Show all commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Engagement Bot Commands",
        color=0x7289da
    )
    
    commands_list = [
        ("/leaderboard [daily/all-time]", "Show top users"),
        ("/mystats", "Check your points and daily limits"),
        ("/top10", "Show top 10 users (all-time)"),
        ("/adjust @user points", "[ADMIN] Adjust points"),
        ("/resetuser @user", "[ADMIN] Reset user stats"),
        ("/help", "Show this message")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="Points are awarded automatically for messages, reactions, and voice activity")
    await interaction.response.send_message(embed=embed)

async def update_pinned_leaderboard():
    """Updates the pinned leaderboard in the designated channel"""
    for guild in bot.guilds:
        # Find leaderboard channel (customize channel name if needed)
        leaderboard_channel = discord.utils.get(guild.channels, name="🏆leaderboard")
        if not leaderboard_channel:
            continue
        
        # Get top 10 users
        c = db.cursor()
        c.execute('''SELECT user_id, total_points, current_streak 
                     FROM users ORDER BY total_points DESC LIMIT 10''')
        top_users = c.fetchall()
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Server Leaderboard",
            description="Top 10 most engaged members\n*Updated automatically every 2 hours*",
            color=0xffd700,
            timestamp=dt.now(timezone.utc)
        )
        
        # Add top users
        emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, (user_id, points, streak) in enumerate(top_users):
            user = guild.get_member(user_id)
            username = user.display_name if user else f"User {user_id}"
            
            # Format streak if exists
            streak_text = f" 🔥 {streak}d" if streak > 1 else ""
            
            embed.add_field(
                name=f"{emojis[i] if i < len(emojis) else f'{i+1}.'} {username}",
                value=f"**{points} pts**{streak_text}",
                inline=False
            )
        
        # Add footer with reset info
        embed.set_footer(text="Points reset daily at midnight UTC • Weekend: 1.5x bonus")
        
        # Find existing pinned leaderboard message
        try:
            async for message in leaderboard_channel.history(limit=50):
                if message.author == bot.user and len(message.embeds) > 0:
                    if message.embeds[0].title == "🏆 Server Leaderboard":
                        await message.edit(embed=embed)
                        return
            
            # No existing message found, send new one and pin it
            new_message = await leaderboard_channel.send(embed=embed)
            await new_message.pin()
            
        except discord.errors.Forbidden:
            print(f"No permission to update pinned message in {leaderboard_channel.name}")

@bot.tree.command(name="resetseason", description="[ADMIN] Reset all points for new season")
@commands.has_permissions(administrator=True)
async def reset_season(interaction.response.send_message, confirm: str = None):
    if confirm != "YES":
        await interaction.response.send_message(
            "⚠️ **WARNING:** This will reset ALL points for EVERYONE!\n"
            "To confirm, type: `/resetseason YES`"
        )
        return
    
    c = db.cursor()
    c.execute('UPDATE users SET total_points = 0')
    c.execute('DELETE FROM daily_stats')
    c.execute('''CREATE TABLE IF NOT EXISTS score_history 
             (season TEXT, user_id INTEGER, total_points INTEGER)''')

    c.execute('INSERT INTO score_history SELECT ?, user_id, total_points FROM users', 
          (f"Season_{get_today()}",))
# Then reset current points
    db.commit()
    
    await interaction.response.send_message("✅ **Season reset!** All points have been set to zero.")
    await update_pinned_leaderboard()  # Update the display

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # CRITICAL: Sync commands globally
    try:
        # This registers commands with Discord
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s) globally")
    except Exception as e:
        print(f"❌ Command sync failed: {e}")
    
# Add this task with your other tasks
@tasks.loop(hours=2)
async def auto_update_leaderboard():
    await update_pinned_leaderboard()

# Wrap your main bot startup in a try-except
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except SyntaxError as e:
        print(f"🚨 CRITICAL SYNTAX ERROR: {e}")
        print("Please check your Python code for typos!")
    except Exception as e:
        print(f"🚨 Bot crashed: {e}")

# Start the task when bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    reset_daily_stats.start()
    check_voice_channels.start()
    auto_update_leaderboard.start()  # ADD THIS LINE
    await update_pinned_leaderboard()  # Update immediately on startup

# ========== START BOT ==========
if __name__ == "__main__":
    # Start the bot
    bot.run(TOKEN)

import discord
from discord import app_commands, Activity, ActivityType, ui
from discord.ext import commands, tasks
import asyncio
import json
import websockets
import logging
from datetime import datetime
import os
from typing import Optional
import platform
import psutil
import time
import aiohttp
import base64

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('token_joiner.log')
    ]
)

# Authorized user ID
AUTHORIZED_USER_ID = 1292218033208557650

class TokenJoiner(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.tokens = []
        self.active_connections = {}
        self.start_time = time.time()
        self.status_messages = [
            {"type": ActivityType.watching, "name": f"{len(self.tokens)} tokens loaded"},
            {"type": ActivityType.playing, "name": "/help | Token VC"},
            {"type": ActivityType.listening, "name": f"{len(self.active_connections)} active connections"},
            {"type": ActivityType.watching, "name": "discord.gg/nashedi"},
            {"type": ActivityType.playing, "name": "Nyx Token VC Joiner"}
        ]
        self.status_index = 0
        self.is_ready = False
        
    async def setup_hook(self):
        await self.tree.sync()
        
    @tasks.loop(seconds=10)
    async def status_task(self):
        """Update bot status every 10 seconds"""
        if not self.is_ready:
            return
            
        # Update dynamic status messages
        self.status_messages[0]["name"] = f"{len(self.tokens)} tokens loaded"
        self.status_messages[2]["name"] = f"{len(self.active_connections)} active connections"
        
        # Get current status
        status = self.status_messages[self.status_index]
        
        # Create activity
        activity = discord.Activity(
            type=status["type"],
            name=status["name"]
        )
        
        # Update presence
        await self.change_presence(activity=activity)
        
        # Move to next status
        self.status_index = (self.status_index + 1) % len(self.status_messages)

    async def connect_token(self, token: str, guild_id: str, channel_id: str):
        token_id = token.strip()[:10] + "..."
        logging.info(f"Attempting to connect with token: {token_id}")
        
        try:
            async with websockets.connect('wss://gateway.discord.gg/?v=9&encoding=json') as websocket:
                hello = await websocket.recv()
                hello_json = json.loads(hello)
                heartbeat_interval = hello_json['d']['heartbeat_interval']
                
                await websocket.send(json.dumps({
                    "op": 2,
                    "d": {
                        "token": token.strip(),
                        "properties": {
                            "os": "windows",
                            "browser": "Discord",
                            "device": "desktop"
                        }
                    }
                }))
                
                await websocket.send(json.dumps({
                    "op": 4,
                    "d": {
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "self_mute": False,
                        "self_deaf": False
                    }
                }))
                
                self.active_connections[token_id] = {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                logging.info(f"Token {token_id} joined voice channel {channel_id} in server {guild_id}")
                
                while True:
                    await asyncio.sleep(heartbeat_interval/1000)
                    try:
                        await websocket.send(json.dumps({"op": 1, "d": None}))
                    except Exception as e:
                        logging.error(f"Connection error for token {token_id}: {str(e)}")
                        if token_id in self.active_connections:
                            del self.active_connections[token_id]
                        break
                        
        except Exception as e:
            logging.error(f"Failed to connect with token {token_id}: {str(e)}")
            if token_id in self.active_connections:
                del self.active_connections[token_id]

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id == AUTHORIZED_USER_ID

bot = TokenJoiner()

@bot.event
async def on_ready():
    """Handler for bot ready event"""
    bot.is_ready = True
    bot.status_task.start()
    logging.info(f"Logged in as {bot.user.name}")
    print(f"""
╔══════════════════════════════════════════╗
║             Bot Information              ║
╠══════════════════════════════════════════╣
║ Bot Name: {bot.user.name:<29} ║
║ Bot ID: {bot.user.id:<31} ║
║ Discord.py Version: {discord.__version__:<20} ║
║ Python Version: {platform.python_version():<24} ║
║ Operating System: {platform.system():<23} ║
║ CPU Usage: {psutil.cpu_percent()}%{' ' * 26}║
║ Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB{' ' * 20}║
╚══════════════════════════════════════════╝
    """)

@bot.event
async def on_command_error(ctx, error):
    """Handler for command errors"""
    if isinstance(error, commands.errors.CommandNotFound):
        return
    logging.error(f"Command error: {str(error)}")

@bot.tree.command(name="stats", description="Show bot statistics")
async def stats(interaction: discord.Interaction):
    """Show bot statistics and information"""
    uptime = str(datetime.now() - datetime.fromtimestamp(bot.start_time)).split('.')[0]
    
    embed = discord.Embed(
        title="<:nyxxxx:1354702087895781426> Bot Statistics",
        description="Current bot status and information",
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    
    embed.add_field(
        name="🤖 Bot Info",
        value=f"```\nName: {bot.user.name}\nID: {bot.user.id}\nUptime: {uptime}\n```",
        inline=False
    )
    
    embed.add_field(
        name="📈 System Info",
        value=f"```\nPython: {platform.python_version()}\nDiscord.py: {discord.__version__}\nCPU Usage: {psutil.cpu_percent()}%\nMemory: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB\n```",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Token Info",
        value=f"```\nLoaded Tokens: {len(bot.tokens)}\nActive Connections: {len(bot.active_connections)}\n```",
        inline=False
    )
    
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="connections", description="Show active token connections")
async def connections(interaction: discord.Interaction):
    """Show currently active token connections"""
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    if not bot.active_connections:
        embed = discord.Embed(
            title="<:nyxxxx:1354702087895781426> No Active Connections",
            description="There are no tokens currently connected to voice channels.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    embed = discord.Embed(
        title="<:question:1354696409420398632> Active Connections",
        description=f"Currently active token connections: {len(bot.active_connections)}",
        color=discord.Color.green()
    )
    
    for token_id, data in bot.active_connections.items():
        embed.add_field(
            name=f"Token: {token_id}",
            value=f"```\nServer: {data['guild_id']}\nChannel: {data['channel_id']}\nConnected: {data['connected_at']}\n```",
            inline=False
        )
    
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

class JoinModal(ui.Modal, title="Join Voice Channel"):
    server_id = ui.TextInput(
        label="Server ID",
        placeholder="Enter the server ID...",
        required=True
    )
    channel_id = ui.TextInput(
        label="Voice Channel ID",
        placeholder="Enter the voice channel ID...",
        required=True
    )
    amount = ui.TextInput(
        label="Amount",
        placeholder="Enter number of tokens to use...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.is_authorized(interaction.user.id):
            embed = discord.Embed(
                title="❌ Unauthorized",
                description="You are not authorized to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            amount = int(self.amount.value)
            server_id = self.server_id.value.strip()
            channel_id = self.channel_id.value.strip()
            
            if not bot.tokens:
                embed = discord.Embed(
                    title="⚠️ No Tokens Available",
                    description="Use `/restock` to add tokens first.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            if amount > len(bot.tokens):
                embed = discord.Embed(
                    title="⚠️ Insufficient Tokens",
                    description=f"Only {len(bot.tokens)} tokens available.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            embed = discord.Embed(
                title="<:question:1354696409420398632> Joining Voice Channel",
                description=f"Starting to join with {amount} tokens...",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
            embed.add_field(name="Server ID", value=f"`{server_id}`", inline=True)
            embed.add_field(name="Channel ID", value=f"`{channel_id}`", inline=True)
            embed.add_field(name="Amount", value=f"`{amount}` tokens", inline=True)
            embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            selected_tokens = bot.tokens[:amount]
            
            tasks = []
            for token in selected_tokens:
                task = asyncio.create_task(bot.connect_token(token, server_id, channel_id))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            success_embed = discord.Embed(
                title="✅ Success",
                description=f"Successfully joined with {amount} tokens!",
                color=discord.Color.green()
            )
            success_embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
            success_embed.add_field(name="Status", value="All tokens connected successfully", inline=False)
            success_embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="Please enter valid numbers for the amount.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Join", style=discord.ButtonStyle.primary, emoji="🎙️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not bot.is_authorized(interaction.user.id):
            embed = discord.Embed(
                title="❌ Unauthorized",
                description="You are not authorized to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        await interaction.response.send_modal(JoinModal())
        
    @discord.ui.button(label="Stock", style=discord.ButtonStyle.green, emoji="📊")
    async def stock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not bot.is_authorized(interaction.user.id):
            embed = discord.Embed(
                title="❌ Unauthorized",
                description="You are not authorized to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Call the check_tokens function directly
        await check_tokens(interaction)

@bot.tree.command(name="panel", description="Open the control panel")
async def panel(interaction: discord.Interaction):
    """Open the control panel with buttons"""
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🎮 Control Panel",
        description="Use the buttons below to control the bot:",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    embed.add_field(
        name="<:question:1354696409420398632> Join",
        value="Join a voice channel with tokens",
        inline=True
    )
    embed.add_field(
        name="📊 Stock",
        value="Check token validity and status",
        inline=True
    )
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    
    await interaction.response.send_message(embed=embed, view=PanelView(), ephemeral=True)

@bot.tree.command(name="join", description="Join a voice channel with tokens")
@app_commands.describe(
    server_id="The server ID to join",
    channel_id="The voice channel ID to join",
    amount="Number of tokens to use"
)
async def join(interaction: discord.Interaction, server_id: str, channel_id: str, amount: int):
    """Join a voice channel with tokens"""
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    if not bot.tokens:
        embed = discord.Embed(
            title="⚠️ No Tokens Available",
            description="Use `/restock` to add tokens first.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    if amount > len(bot.tokens):
        embed = discord.Embed(
            title="⚠️ Insufficient Tokens",
            description=f"Only {len(bot.tokens)} tokens available.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    embed = discord.Embed(
        title="<:question:1354696409420398632> Joining Voice Channel",
        description=f"Starting to join with {amount} tokens...",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    embed.add_field(name="Server ID", value=f"`{server_id}`", inline=True)
    embed.add_field(name="Channel ID", value=f"`{channel_id}`", inline=True)
    embed.add_field(name="Amount", value=f"`{amount}` tokens", inline=True)
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    selected_tokens = bot.tokens[:amount]
    
    tasks = []
    for token in selected_tokens:
        task = asyncio.create_task(bot.connect_token(token, server_id, channel_id))
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    success_embed = discord.Embed(
        title="✅ Success",
        description=f"Successfully joined with {amount} tokens!",
        color=discord.Color.green()
    )
    success_embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    success_embed.add_field(name="Status", value="All tokens connected successfully", inline=False)
    success_embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.followup.send(embed=success_embed, ephemeral=True)

@bot.tree.command(name="restock", description="Load tokens from a file")
@app_commands.describe(
    file="tokens.txt"
)
async def restock(interaction: discord.Interaction, file: discord.Attachment):
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    if not file.filename.endswith('.txt'):
        embed = discord.Embed(
            title="❌ Invalid File",
            description="Please upload a .txt file.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    content = await file.read()
    bot.tokens = content.decode().splitlines()
    
    embed = discord.Embed(
        title="✅ Tokens Loaded",
        description=f"Successfully loaded {len(bot.tokens)} tokens!",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    embed.add_field(name="File", value=f"`{file.filename}`", inline=True)
    embed.add_field(name="Tokens", value=f"`{len(bot.tokens)}` loaded", inline=True)
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear", description="Clear all loaded tokens")
async def clear(interaction: discord.Interaction):
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    bot.tokens = []
    embed = discord.Embed(
        title="🧹 Tokens Cleared",
        description="All tokens have been cleared from memory.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="logs", description="View the latest logs")
async def logs(interaction: discord.Interaction):
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    try:
        with open('token_joiner.log', 'r') as f:
            log_content = f.read()
            if len(log_content) > 2000:
                log_content = log_content[-2000:]  # Get last 2000 characters
                
            embed = discord.Embed(
                title="📝 Latest Logs",
                description=f"```{log_content}```",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
            embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except FileNotFoundError:
        embed = discord.Embed(
            title="⚠️ No Logs Found",
            description="No log file exists yet.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="Show help information")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="<:nyxxxx:1354702087895781426> Nyx Token VC Joiner Help",
        description="A powerful tool for managing multiple Discord accounts in voice channels.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    
    commands_info = """
<:question:1354696409420398632> **Voice Commands**
`/join <server_id> <amount>` - Join voice channel with tokens
`/connections` - View active token connections

🔧 **Management Commands**
`/restock <file>` - Load tokens from .txt file
`/clear` - Clear all loaded tokens

📊 **Information Commands**
`/stats` - View bot statistics
`/logs` - View latest logs
`/help` - Show this help message
"""
    
    embed.add_field(name="Commands", value=commands_info, inline=False)
    
    features = """
• Real-time connection status
• Detailed error reporting
• Token management system
• Advanced logging system
• System statistics
• Connection tracking
"""
    embed.add_field(name="📋 Features", value=features, inline=False)
    
    security = """
• Administrator-only commands
• Secure token handling
• Masked token display
• Permission system
"""
    embed.add_field(name="🔒 Security", value=security, inline=False)
    
    embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def check_tokens(interaction: discord.Interaction):
    """Check the validity and status of tokens from tokens.txt"""
    if not bot.is_authorized(interaction.user.id):
        embed = discord.Embed(
            title="❌ Unauthorized",
            description="You are not authorized to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        with open('tokens.txt', 'r') as f:
            tokens = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        embed = discord.Embed(
            title="⚠️ No Tokens File",
            description="tokens.txt file not found.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not tokens:
        embed = discord.Embed(
            title="⚠️ No Tokens Available",
            description="tokens.txt is empty.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="🔍 Checking Token Stock",
        description="Checking validity of tokens from tokens.txt...",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    valid_tokens = []
    invalid_tokens = []
    rate_limited_tokens = []
    total_tokens = len(tokens)

    async with aiohttp.ClientSession() as session:
        for token in tokens:
            token = token.strip()
            if not token:
                continue
                
            headers = {
                'Authorization': token,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            try:
                async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        username = user_data.get('username', 'Unknown')
                        discriminator = user_data.get('discriminator', '0000')
                        user_id = user_data.get('id', 'Unknown')
                        valid_tokens.append({
                            'token': token[:10] + "...",
                            'username': f"{username}#{discriminator}",
                            'id': user_id
                        })
                    elif response.status == 429:
                        rate_limited_tokens.append(token[:10] + "...")
                    else:
                        invalid_tokens.append(token[:10] + "...")
            except Exception as e:
                invalid_tokens.append(token[:10] + "...")
                logging.error(f"Error checking token: {str(e)}")

    # Create result embed
    result_embed = discord.Embed(
        title="📊 Token Stock Results",
        description=f"Checked {total_tokens} tokens from tokens.txt",
        color=discord.Color.green()
    )
    result_embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")

    # Add valid tokens section
    if valid_tokens:
        valid_info = "\n".join([
            f"`{token['token']}` - {token['username']} ({token['id']})"
            for token in valid_tokens[:10]  # Show first 10 valid tokens
        ])
        if len(valid_tokens) > 10:
            valid_info += f"\n... and {len(valid_tokens) - 10} more"
        result_embed.add_field(
            name=f"✅ Valid Tokens ({len(valid_tokens)})",
            value=valid_info,
            inline=False
        )

    # Add invalid tokens section
    if invalid_tokens:
        invalid_info = "\n".join([
            f"`{token}`"
            for token in invalid_tokens[:10]  # Show first 10 invalid tokens
        ])
        if len(invalid_tokens) > 10:
            invalid_info += f"\n... and {len(invalid_tokens) - 10} more"
        result_embed.add_field(
            name=f"❌ Invalid Tokens ({len(invalid_tokens)})",
            value=invalid_info,
            inline=False
        )

    # Add rate limited tokens section
    if rate_limited_tokens:
        rate_limited_info = "\n".join([
            f"`{token}`"
            for token in rate_limited_tokens[:10]  # Show first 10 rate limited tokens
        ])
        if len(rate_limited_tokens) > 10:
            rate_limited_info += f"\n... and {len(rate_limited_tokens) - 10} more"
        result_embed.add_field(
            name=f"⚠️ Rate Limited Tokens ({len(rate_limited_tokens)})",
            value=rate_limited_info,
            inline=False
        )

    # Add summary
    result_embed.add_field(
        name="📈 Summary",
        value=f"```\nTotal Tokens: {total_tokens}\nValid: {len(valid_tokens)}\nInvalid: {len(invalid_tokens)}\nRate Limited: {len(rate_limited_tokens)}\n```",
        inline=False
    )

    result_embed.set_footer(text="Arox Token VC Joiner | Made by discord.gg/r1ch")
    await interaction.followup.send(embed=result_embed, ephemeral=True)

@bot.tree.command(name="stock", description="Check token validity and status")
async def stock_command(interaction: discord.Interaction):
    """Check the validity and status of tokens from tokens.txt"""
    await check_tokens(interaction)

# Run the bot
bot.run(config['bot_token']) 
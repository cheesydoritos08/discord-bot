import discord
import os
import asyncio

import handlers.database_handler as database_handler
import time
from utils.utility_functions import send_error_embed
from utils.timer import Timer
from dotenv import load_dotenv
from discord.ext import commands

discord_invite = 'https://discord.com/oauth2/authorize?client_id=1371573491391922278&scope=bot+applications.commands&permissions=414464691264'


# Secures the token as a variable
load_dotenv('.env')
TOKEN: str = (
    os.getenv('DEV_BOT_TOKEN') if os.getenv('ENV') == 'dev' else os.getenv('MAIN_BOT_TOKEN')
)

# webhook to discord channel where errors will be sent to
INFO_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

# Set the permissions for the intents and the discord bot
intents = discord.client.Intents.default()
intents.members = True
intents.message_content = True

# Creates a variable to reference the bot and sets the prefix and intent permissions
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)
bot.remove_command('help')

# Catches when the bot goes online
@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')


@bot.event
async def on_resumed():
    resume_timers()

# Resumes all current running timers
def resume_timers():
    user_profiles = database_handler.users.find({}, {"timers": 1})
    
    for profile in list(user_profiles):
        for timer, end_time in profile["timers"].items():
            start_time = round(time.time())            
            
            if end_time <= 0:
                continue
            elif (end_time - start_time) > 0:
                Timer(user_id=profile["_id"], name=timer, starttime=start_time, timer_length=end_time - start_time).create_timer()
            elif (end_time - start_time) <= 0:
                Timer(user_id=profile["_id"], name=timer, starttime=0, timer_length=0).create_timer()
                database_handler.users.update_one({"_id": profile["_id"]}, {"$set": {f"timers.{timer}": 0 }})


# Loads the cogs in the cog directory on startup
async def on_startup_load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')


# Loads the bot
async def main():
    async with bot:
        await on_startup_load()
        resume_timers()
        try:
            await bot.start(TOKEN)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = e.response.headers.get("Retry-After", 60)
                await asyncio.sleep(retry_after)
            else:
               await send_error_embed(bot=bot, error=e, ctx=None)
        except Exception as e:
            await send_error_embed(bot=bot, error=e, ctx=None)
asyncio.run(main())

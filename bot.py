import discord
import os
import asyncio
import handlers.database_handler as database_handler
import time
from utils.utility_functions import create_error_embed, log_error_embed
from utils.timer import Timer
from dotenv import load_dotenv
from discord.ext import commands
import datetime
import random
import topgg

discord_invite = 'https://discord.com/oauth2/authorize?client_id=1371573491391922278&scope=bot+applications.commands&permissions=414464691264'


# Secures the token as a variable
load_dotenv('.env')
TOKEN: str = (
    os.getenv('DEV_BOT_TOKEN') if os.getenv('ENV') == 'dev' else os.getenv('MAIN_BOT_TOKEN')
)

AUTHORIZATION_CODE = os.getenv("WEBHOOK_AUTHORIZATION")

# Set the permissions for the intents and the discord bot
intents = discord.client.Intents.default()
intents.members = True
intents.message_content = True

# Creates a variable to reference the bot and sets the prefix and intent permissions
bot = commands.Bot(command_prefix='?', activity=discord.Activity(type=discord.ActivityType.watching, name="Type ?tut to start!"), intents=intents, help_command=None)
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
    try:
        bot.topgg_webhook = topgg.WebhookManager(bot).dbl_webhook("/dblwebhook", AUTHORIZATION_CODE)
        bot.topgg_webhook.run(25869)  
    except Exception as e:
        print(e)

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
    


@bot.event
async def on_dbl_vote(data):
        try:
            user_id = int(data["user"])

            if database_handler.users.find_one({"_id": user_id}) is None:
                return
            
            user_profile = database_handler.users.find_one({"_id": user_id})
            reward = 2000
            streak = user_profile.get('vote').get('vote_streak')
            last_claim_time = user_profile.get('vote').get('last_vote_time')
            last_claim = datetime.datetime.fromtimestamp(float(last_claim_time))
            claim_time = datetime.datetime.now()   
            claim_time_timestamp = round(time.time())
            time_difference = claim_time - last_claim

            # Calculates whether to reset the streak or not
            if time_difference > datetime.timedelta(hours=24):
                database_handler.users.update_one({'_id': user_id}, {'$set': {'vote.vote_streak': 1}})
                streak = 1
            else:
                database_handler.inc_value_to_users(user_id=user_id, key='vote.vote_streak', value=1)
                streak += 1

            if streak > 40:
                rarities = {
                    'Legendary': 15,
                    'Epic': 25,
                    'Rare': 20,
                    'Common': 40,
                            }
            elif streak > 30:
                rarities = {
                    'Legendary': 12,
                    'Epic': 25,
                    'Rare': 20,
                    'Common': 43,
                            }
            elif streak > 20:
                rarities = {
                    'Legendary': 10,
                    'Epic': 20,
                    'Rare': 25,
                    'Common': 45,
                            }
            elif streak > 10:
                rarities = {
                    'Legendary': 5,
                    'Epic': 15,
                    'Rare': 30,
                    'Common': 50,
                            }
            else:
                rarities = {
                    'Legendary': 1,
                    'Epic': 9,
                    'Rare': 40,
                    'Common': 50,
                            }
            
            shard_rarity = None
            # Generates a rarity for the shard
            randomNum = random.randint(1, sum(rarities.values()))
            counter = 0
            for rarity, weight in rarities.items():
                counter += weight
                if randomNum <= counter:
                    shard_rarity = rarity
                        
            # Picks a character shard based off of the rarity
            character = random.choice(database_handler.all_characters_search(key='rarity', query=shard_rarity))
            database_handler.inc_value_to_users(user_id=user_id, key=f'inventory.shards.{character["name"]}', value=1)
            database_handler.inc_value_to_users(user_id=user_id, key='economy.yen', value=reward)


            member = await bot.fetch_user(user_id)
            await member.send(f"You have received 2000 yen and a {character['name']} shard from voting!")
            database_handler.users.update_one({"_id": user_id}, {"$set": {"vote.last_vote_time": claim_time_timestamp}})
            
            Timer(user_id=user_id, name="bot_vote", starttime=claim_time_timestamp, timer_length=60 * 60 * 12)
            
        except Exception as e:
            create_error_embed(error=e)
            

@bot.event
async def on_dbl_test(data):
    bot.dispatch('on_dbl_vote')



# Loads the bot
async def main():
    async with bot:
        log_error_embed.start(bot)
        await on_startup_load()
        resume_timers()

        try:
            await bot.start(TOKEN)


        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = e.response.headers.get("Retry-After", 60)
                await asyncio.sleep(retry_after)
            else:
               await create_error_embed(error=e, ctx=None)
        except Exception as e:
            await create_error_embed(error=e, ctx=None)
        finally:
            bot.topgg_webhook.close()
asyncio.run(main())

import time
import asyncio
import handlers.database_handler as database_handler
import discord
import os
from discord.ext import commands
from utils.converters import InventoryConverter, UseChipConverter
from utils.buttons import InviteButton
from utils.utility_functions import update_quests, cooldown_calculator, create_error_embed
from utils.timer import Timer
import datetime
import random
import topgg


TOKEN: str = (
    os.getenv('DEV_BOT_TOKEN') if os.getenv('ENV') == 'dev' else os.getenv('MAIN_BOT_TOKEN')
)
AUTHORIZATION_CODE = os.getenv("WEBHOOK_AUTHORIZATION")


class Utilites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        bot.topgg_webhook = topgg.WebhookManager(bot=self.bot).dbl_webhook("/dblwebhook", AUTHORIZATION_CODE)
        bot.topgg_webhook.run(25869)

    # Allows users to use xp and yen boosts
    @commands.command(name="boost")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def use_boost(self, ctx, *, item : InventoryConverter):
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
   
        
        user_profile = database_handler.users.find_one({"_id": ctx.author.id})
        inventory = user_profile.get("inventory")
       
        if item != "yen_booster" and item != "xp_booster":
            return await ctx.send("Not a valid boost item.")
    
        # Determines what to do based on the item mentioned
        if inventory.get(item, None):
            if inventory[item]["amount"] == 0:
                return await ctx.send("Can't use what you don't have. This isn't rocket science.")
            elif user_profile["buffs"][item]["active"]:
                return await ctx.send("Isn't one buff enough for you?")
            
            await ctx.send(f"You have used a {item.replace("_", " ").title().replace("Xp", "XP")}")
            start_time = round(time.time())

            database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item}.amount", value=-1)
            database_handler.users.update_one({"_id": ctx.author.id}, {"$set": {f"buffs.{item}.multiplier": inventory[item]["multiplier"]}})
            database_handler.users.update_one({"_id": ctx.author.id}, {"$set": {f"buffs.{item}.active": True}})

            if item == "yen_booster":
                update_quests(user_id=ctx.author.id, quest_id="use_yen_booster", amount=1)
            elif item == "xp_booster":
                update_quests(user_id=ctx.author.id, quest_id="use_xp_booster", amount=1)

            timer = Timer(user_id=ctx.author.id, name=item, starttime=start_time, timer_length=60 * inventory[item]["time_period"])
            timer.create_timer()
        else:
            return await ctx.send("Can't use what you don't have. This isn't rocket science.")


    # Allows users to use chips to upgrade characters faster
    @commands.command(name="chip",
                      help="This command lets you use XP chips to level up your characters. Each XP chip gives 1000 XP points. The format for this command is `?chip <character name> <amount>`. If your character goes over the level cap when you use your chips, you will **not** be refunded the leftover chips so be careful.")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def use_chip(self, ctx, *, arg : UseChipConverter):
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
  
        character, amount = arg
        user_profile = database_handler.users.find_one({"_id": ctx.author.id})
        inventory = user_profile["inventory"]

        if not inventory.get("xp_chip") or inventory.get("xp_chip", {}).get("amount", 0) == 0 or inventory.get("xp_chip", {}).get("amount", 0) < amount:
            return await ctx.send("You don't even have enough chips. Sad.")

        database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.xp_chip.amount", value=-amount)

        for char in user_profile["characters"]:
            if char["name"] == character:
                leveling_cap = 30
                if char['LVL'] == leveling_cap:
                    return await ctx.send(f'You can\'t go past level {leveling_cap}.')
                
                database_handler.increment_character_xp(user_id=ctx.author.id, xp=amount * 1000, character=character)
                database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.xp_chip.amount", value=-amount)
                update_quests(user_id=ctx.author.id, quest_id="use_xp_chip", amount=1)
                return await ctx.send(f"{character} has been leveled up.")

    # Displays the current timers and how much time is left on them
    @commands.command(name="timers",
                      help="This command displays all the timers you have currently. Use this to check how much time left you have on your boosters or to see when your daily quests reset!")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def display_timers(self, ctx):
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        user_profile= database_handler.users.find_one({"_id": ctx.author.id})
        user_timers = user_profile["timers"]

        embed = discord.Embed(title="₊˚ ✧ ━━━━━━━━━⊱ Timers ⊰━━━━━━━━━━ ✧ ₊˚",
                      colour=0xb78ed2)
        
        for timer in user_timers:
            if user_timers[timer] == 0 and (timer == "daily_quests" or timer == "daily_claim"):
                embed.add_field(name=f"{timer.replace("_", " ").title().replace("Xp", "XP")}: Ready!",
                value="",
                inline=False)
            elif user_timers[timer] == 0:
                 embed.add_field(name=f"{timer.replace("_", " ").title().replace("Xp", "XP")}: Not Active",
                value="",
                inline=False)               
            else:
                time_remaining = user_timers[timer] - round(time.time())
                embed.add_field(name=f"{timer.replace("_", " ").title().replace("Xp", "XP")}: {cooldown_calculator(time_to_calculate=time_remaining)}",
                value="",
                inline=False)                


        embed.set_footer(text="₊˚ ✧ ━━━━━━━━━━━━━━━━━⊱𝄞⊰━━━━━━━━━━━━━━━━━ ✧ ₊˚")

        await ctx.send(embed=embed)

    @commands.command(name="invite",
                      help="This command sends a link to invite the bot to your server and for you to join the bot's official server!")
    async def invite_bot(self, ctx):
        view = InviteButton()
        embed = discord.Embed(title="Invites",
                              description="Join the bot's official server if you have any questions or if you want to report a bug! Users who report bugs will be granted a reward when they are fixed!")
        await ctx.send(embed=embed, view=view)
        
    @commands.command(name="vote",
                      help="This command lets you vote for the bot on top.gg! Voting for the bot rewards you 2000 yen and one shard of a random rarity, all the way up to Legendary!")
    async def vote_for_bot(self, ctx):
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return await ctx.send("No profile")
            
        user_profile = database_handler.users.find_one({"_id": ctx.author.id})
        if user_profile.get("timers", {}).get("bot_vote") != 0:
                return await ctx.send("You've voted")
            
        view = discord.ui.View()
        button = discord.ui.Button(style=discord.ButtonStyle.url, url="https://top.gg/bot/1371573491391922278", label="Vote for the bot!")
        view.add_item(button)

        embed = discord.Embed(title="Vote for the Lookism Bot!",
                                description="By voting for the bot on Top.gg, you get 2000 yen and \na random fragment of your choice. The greater your vote\nstreak, the higher the chance of you getting a legendary\nfragment whenever you vote.")

        embed.set_footer(text=f"Vote Streak: {user_profile.get("vote_streak")}")
        
        await ctx.send(view=view, embed=embed)
        
        # Checks to see if they have a vote timer ongoingg
        # sends an embed linking website and telling user to vote


    
    @vote_for_bot.error
    @invite_bot.error
    @display_timers.error
    @use_chip.error
    @use_boost.error
    async def cooldown_error(self, ctx, error):
        # Sends a cooldown message if command is reused when on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            user_id = ctx.author.id
            cooldown_string = cooldown_calculator(round(error.retry_after))

            if user_id not in self.warned_cooldown_users:
                self.warned_cooldown_users.add(user_id)
                await ctx.send(f'Can\'t you be patient and wait for {cooldown_string}')
            
            # cleanup after cooldown
            async def remove_after():
                await asyncio.sleep(error.retry_after)
                self.warned_cooldown_users.discard(user_id)

            asyncio.create_task(remove_after())
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            create_error_embed(ctx=ctx, error=error)
            

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        try:
            print("i ran ig")
            if database_handler.users.find_one({"id": data["user"]}) is None:
                return
            
            user_profile = database_handler.users.find_one({"id": data["user"]})
            streak = user_profile.get('vote').get('vote_streak')
            last_claim_time = user_profile.get('vote').get('last_vote_time')
            last_claim = datetime.datetime.fromtimestamp(float(last_claim_time))
            claim_time = datetime.datetime.now()   
            time_difference = claim_time - last_claim

                # Calculates whether to reset the streak or not
            if time_difference > datetime.timedelta(hours=24):
                database_handler.users.update_one({'_id': data["user"]}, {'$set': {'vote.vote_streak': 1}})
                streak = 1
            else:
                database_handler.inc_value_to_users(user_id=data["user"], key='vote.vote_streak', value=1)
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
            database_handler.inc_value_to_users(user_id=data["user"], key=f'inventory.shards.{character["name"]}', value=1)

            member = self.bot.fetch_user(data['user'])
            member.send(f"You have received 2000 yen and a {character['name']} shard fromn voting!")
            
            # Timer(user_id=ctx.author.id, name="bot_vote", starttime=round(time.time()), timer_length=60 * 60 * 12)
            
            print(data)
        except Exception as e:
            create_error_embed(error=e)

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        print("i too ran")
        return self.bot.dispatch('dbl_vote', data)

async def setup(bot):
    await bot.add_cog(Utilites(bot))
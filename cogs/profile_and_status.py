import discord
import asyncio
import random
import time
import os
import sys
import handlers.database_handler as database_handler
from utils.utility_functions import cooldown_calculator, create_error_embed
from utils.timer import Timer
from discord.ext import commands


# Controls profile commands
class Profile_and_Status(commands.Cog):
    # Initializes the class
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    # The profile command
    @commands.command(help="This command displays your profile for the bot!")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def profile(self, ctx, *, member: discord.Member = None):
        # Checks to make sure the target has a profile and isn't a bot
        if member is None and not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        elif member is None:
            user = ctx.author
        elif not await database_handler.check_existing_profile(ctx=ctx, user_id=member.id, another_user=True):
            return
        elif member and not member.bot:
            user = member

        # Stores the profile in a variable
        user_profile = database_handler.users.find_one({'_id': user.id})
        if user_profile is None:
            return await ctx.send('This member does not have a profile.')

        # Sets the embed with all the profile info and formats it
        embed = discord.Embed(
            title=f"{user}'s Profile",
            description='This is where all of your stats are displayed.',
            colour=discord.Color.dark_red(),
        )

        embed.set_author(name='Profile')

        embed.add_field(
            name='Character Rarities',
            value=f'Common: {user_profile.get("common_characters")}        \nEpic: {user_profile.get("epic_characters")}\nRare: {user_profile.get("rare_characters")}                 \nLegendary: {user_profile.get("legendary_characters")}',
            inline=True,
        )
        embed.add_field(
            name='Character Thresholds',
            value=f'1T: {user_profile.get("threshold_one_characters")}\n2T: {user_profile.get("threshold_two_characters")}\n3T: {user_profile.get("threshold_three_characters")}\n4T: {user_profile.get("threshold_four_characters")}',
            inline=True,
        )
        embed.add_field(
            name='',
            value='',
            inline=False,
        )
        embed.add_field(
            name='Battle Stats',
            value=f'Wins: {user_profile.get("wins")} \nLosses: {user_profile.get("losses")}\nELO: {user_profile.get('elo').get('score')}\nELO Ranking: {user_profile.get('elo').get('ranking')}\nRaid Level: {user_profile.get('raid_level')}',
            inline=True,
        )
        embed.add_field(
            name='Other',
            value=f'Pity: {user_profile.get("pity")}\nBalance: ₩{user_profile.get("economy").get("won")}\nVote Streak: {user_profile.get("vote", {}).get('vote_streak')}',
            inline=True,
        )

        embed.set_thumbnail(url=f'{user.display_avatar}')

        # Sends the message
        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='quests',
                      help="This command shows all of your daily quests. For every quest completed, you gain 1000 won and 2 standard banner tickets. Quests reset every 24 hours.")
    async def generate_quests(self, ctx):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        
        user_quests = database_handler.users.find_one({"_id": ctx.author.id}).get("quests")

        # If the user currently has no quests, randomly selects three from the quest
        # database and adds it to the user
        if user_quests == []:
            all_quests = []
            for quest in database_handler.quests.find({}):
                    all_quests.append(quest)

            for x in range(3):
                quest = all_quests[random.randint(0, len(all_quests) - 1)]
                database_handler.add_array_to_users(user_id=ctx.author.id, key="quests", array=quest)
                all_quests.remove(quest)
            
            Timer(user_id=ctx.author.id, starttime=round(time.time()), timer_length=60 * 60 * 24, name="daily_quests").create_timer()
        
        user_quests = database_handler.users.find_one({"_id": ctx.author.id}).get("quests")

        # Creates an embed displaying user quests
        embed = discord.Embed(title="┈ • ୨ Daily Quests ୧ • ┈",
                      colour=0xece48e)

        for quest in user_quests:
            embed.add_field(name=f"➻ {quest['description']}",
                    value=f"Progress: {quest['total_completed']}/{quest['total_needed']}",
                    inline=False)

        embed.set_footer(text="Completing all your quests grants you 5 free limited time banner tickets!")

        await ctx.send(embed=embed)

    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name="leaderboard", 
                      aliases=["lb"],
                      help="This command displays the global leaderboard for the ELO ranking of all players. Win fights against high ELO players to increase your ELO and get on the leaderboard!")
    async def view_leaderboard(self, ctx, type = None):
        # Gets the top ten players based on ELO
        top_ten_users = database_handler.users.aggregate([
            {"$sort": {"elo": -1}},
            {"$limit": 10}
    
        ])

        leaderboard_string = ""
        # Adds a medal next to the name if the user is in the top 3 and numbers the rest
        # normally
        for i, user in enumerate(top_ten_users):
                if i == 0:
                    leaderboard_string += f"🥇 {await self.bot.fetch_user(user["_id"])} ---> {user["elo"]["score"]} ELO\n"
                elif i == 1:
                    leaderboard_string += f"🥈 {await self.bot.fetch_user(user["_id"])} ---> {user["elo"]["score"]} ELO\n"
                elif i == 2:
                    leaderboard_string += f"🥉 {await self.bot.fetch_user(user["_id"])} ---> {user["elo"]["score"]} ELO\n"
                else:
                    leaderboard_string += f"{i+1}. {await self.bot.fetch_user(user["_id"])} ---> {user["elo"]["score"]} ELO\n"

        
        # Creates an embed to display the leaderboard
        embed = discord.Embed(title="₊˚ ✧ ━━⊱ Leaderboard ⊰━━ ✧ ₊˚",
                            colour=0xb78ed2)

        embed.add_field(name="",
                        value=leaderboard_string,
                        inline=False)

        embed.set_footer(text="₊˚ ✧ ━━━━━━━━━━⊱𝄞⊰━━━━━━━━━━ ✧ ₊˚")
        await ctx.send(embed=embed)

    @view_leaderboard.error
    @generate_quests.error
    @profile.error
    async def error_handler(self, ctx, error):
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
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno
            file_name = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]

            await create_error_embed(ctx=ctx, error=error, msg=f"This occured on line {line_num} in {file_name}")
        
async def setup(bot):
    await bot.add_cog(Profile_and_Status(bot))

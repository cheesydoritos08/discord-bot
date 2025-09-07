import discord
import asyncio
from utils.utility_functions import create_error_embed, cooldown_calculator
from discord.ext import commands
import random
import os
import sys

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(name='quote',
                      help="This command gives out a random quote from a random lookism character. You can also suggest a quote to add to this command by going to the support server. To get the invite link, type ?invite.")
    async def random_quote_generator(self, ctx):
        try:
            # Creates a list of quotes
            quotes = [
                    "> But if I have to abandon what I wanted to protect to get that power, what good would that do? In the end, you'll be left on your own. \n > *— Daniel Park*",
                    "> It was better than the best night I had with any woman. \n > *— Gun Park*",
                    "> I promised myself I would never lose to a bad guy. \n > *— Vasco*",
                    "> The world only cares about results. \n > *— Gun Park*",
                    "> Be proud and confident of yourself. I learned that lesson a little bit too late.  \n > *— Gongseob Ji*",
                    "> The world won't care about you even if you cry.\n > *— Samuel Seo*" ,
                    "> What made you powerful is the strong faith you had in yourself. \n > *— James Lee*",
                    "> It's an unfair world. I just have to try harder! \n > *— Daniel Park*",
                    "> I don't care about becoming the strongest. I don't fight to win. There is only one reason I use my fist, it's because I'm a man. Anyone can become the strongest, not anyone can be a real man. \n > *— Taesoo Ma*",
                    "> Believe in yourself. Strong faith. If you don’t start off believing in yourself, you’ll never beat anyone. \n > *— Taesoo Ma*"
                    ]
            
            # Creates an embed to house the quote
            embed = discord.Embed(title= "Random Quote",
                                description= quotes[random.randint(0, len(quotes) - 1 )],
                                color= discord.Color.dark_magenta())
            
            embed.set_footer(text = "Feel free to suggest more quotes in the support server! To get the link, type ?invite.")
            
            return await ctx.send(embed=embed)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while using the quote command on line {line_num}")


    @commands.command(name='whowouldwin',
                      aliases = ['www'],
                      help="This command **randomly** decides between the two opponents presented who would win in a fight. The command can only accept two opponents at a time. Make sure the names of the opponents are separated by a comma else the output might look funky. The format for this command is `?whowouldwin <name1>, <name2>`.")
    async def who_would_win(self, ctx, *, user_input : str = None):
        try:
            # Makes sure the user provides input
            if user_input is None:
                return await ctx.send("Give me two opponents for me to pick from. The format is `?whowouldwin <name1>, <name2>`.")
            
            # Formats the opponents sent by the user and ensures that only two opponents are given
            opponents_list = [x.strip().title() for x in user_input.split(",")]

            if len(opponents_list) != 2:
                return await ctx.send("I can only pick from two opponents. No more, no less.")
            
            # Creates a list of responses with corresponding gifs
            response_list = [
                [" would get absolutely obliterated by ", "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExNnh6enlrYXA1OXVxMGZidmU2enhlbWJ3cW16emI4dnI3dXF4Ymw0YyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/NuiEoMDbstN0J2KAiH/giphy.gif"],
                [" would get bodied by ", "https://i.imgur.com/JmzyW2T.gif"],
                [" would get turned into a punching bag by ", "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExZGtjNnp6eDZucnltemd0ZDhjdDB5ODN1bmxmNjRvbHYybmkxN2psMCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/NY3tXwOBUwQYq7lbXx/giphy.gif"],
                [" would humble ", "https://i.imgur.com/rLLmiAm.gif"],
                [" would no-diff ", "https://i.imgur.com/yPvRIbF.gif"], 
                [" wouldn't stand a chance against ", "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExdDVsb2Z2ZTI5ZnQ3aXB2MmpocXlyam5xMWs2eDJxb3R3ODVvb3ZrNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xULW8G5jO9gxUsGGQg/giphy.gif"],
                [" wouldn't land a single hit on ", "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExejd0NDBmZ2szNWpjeXp6YXp2dmVzanM4N2VtZTh0M2ZrdmFlaXQ2ZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/hzx9toaSQPHRm/giphy.gif"],
                [" would defintely low-diff ", "https://i.imgur.com/MZD5y6d.gif"] ,
                [" would get stomped with zero effort by ", "https://i.imgur.com/8BHnbJB.gif"],
                [" would get turned into a statistic by ", "https://i.imgur.com/aqUZ94Z.gif"],
                [" can't even get past Kenta. Why would he even be able to touch ", "https://i.imgur.com/io6CwI0.gif"]
            ]

            # Randomly chooses the order in which the opponents will appear in the response
            first_opponent = opponents_list[random.randint(0, 1)]
            opponents_list.remove(first_opponent)
            second_opponent = opponents_list[0]
            response = response_list[random.randint(0, len(response_list) - 1)]

            # Creates an embed displaying the text and gif
            embed = discord.Embed(title=f"{first_opponent}{response[0]}{second_opponent}")
            embed.set_footer(text = "Feel free to suggest more gifs in the support server! To get the link, type ?invite.")
            embed.set_image(url=response[1]) 

            return await ctx.send(embed = embed)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while checking who would win on line {line_num}")


    
    
    
    
    
    @random_quote_generator.error
    @who_would_win.error
    async def error_handler(self, ctx, error):
        # Sends a cooldown message if command is reused when on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            user_id = ctx.author.id
            cooldown_string = cooldown_calculator(round(error.retry_after))

            if user_id not in self.warned_cooldown_users:
                self.warned_cooldown_users.add(user_id)
                await ctx.send(f'Can\'t you be patient and wait for {cooldown_string}?')
            
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
    await bot.add_cog(Fun(bot))
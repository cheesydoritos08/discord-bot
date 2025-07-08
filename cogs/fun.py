import discord
import asyncio
from utils.utility_functions import create_error_embed, cooldown_calculator
from discord.ext import commands
import random

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.command(name='quote',
                      help="This command gives out a random quote from a random lookism character. You can also suggest a quote to add to this command by going to the support server. To get the invite link, type ?invite.")
    async def random_quote_generator(self, ctx):
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
        
        embed = discord.Embed(title= "Random Quote",
                              description= quotes[random.randint(0, len(quotes) - 1 )],
                              color= discord.Color.dark_magenta())
        
        embed.set_footer(text = "Feel free to suggest more quotes in the support server! To get the link, type ?invite.")
        
        return await ctx.send(embed=embed)

    @random_quote_generator.error
    async def cooldown_error(self, ctx, error):
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
            await create_error_embed(ctx=ctx, error=error)

async def setup(bot):
    await bot.add_cog(Fun(bot))
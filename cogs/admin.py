from discord.ext import commands
import handlers.database_handler as database_handler

class Owner_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Test command to check leveling
    @commands.command(name = "lvlup")
    async def level_up(self, ctx, *, character_name):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            xp = 30 * 2000
            character_xp_level = database_handler.increment_character_xp(user_id=ctx.author.id, xp=xp, character=character_name, return_xp=True)
                
            await ctx.send(f"{character_name.title()} currently has {character_xp_level}/2000.")

    # Loads the specified extension
    @commands.command()
    async def load(self, ctx, extension):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            await self.bot.load_extension(f'cogs.{extension}')
            await ctx.send(f'Loaded {extension} cog')


    # Unloads the specified extension
    @commands.command()
    async def unload(self, ctx, extension):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            await self.bot.unload_extension(f'cogs.{extension}')
            await ctx.send(f'Unloaded {extension} cog')

    # Reloads the specified extension
    @commands.command()
    async def reload(self, ctx, extension):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            await self.bot.reload_extension(f'cogs.{extension}')
            await ctx.send(f'Reloaded {extension} cog')

    @commands.command(name="add")
    async def add_item(self, ctx, *, item):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            database_handler.add_item(ctx=ctx, item=item)
            await ctx.send(f"{item} has been added.")


async def setup(bot):
    await bot.add_cog(Owner_Commands(bot))
from discord.ext import commands
import handlers.database_handler as database_handler
from utils.utility_functions import cooldown_calculator, create_error_embed
import asyncio

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

    # Searches for a character and changes their stat for all users
    @commands.command(name="updchar")
    async def update_character(self, ctx, character, stat, value, convertToInt = ""):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            if convertToInt.lower() == "t":
                value = int(value)
        
            database_handler.users.update_many({"characters.name": character.replace("_", " ").title()}, {"$set": {f"characters.$.{stat}": value}})
            return await ctx.send(f"{character} has had {stat} changed to {value}")
        
    # Removes a stat from a character    
    @commands.command(name="unupdchar")
    async def un_update_character(self, ctx, character, stat):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
        
            database_handler.users.update_many({"characters.name": character.replace("_", " ").title()}, {"$unset": {f"characters.$.{stat}": ""}})
            return await ctx.send(f"{character} has had {stat} changed to None")

    # Searches the effects of the given character and updates them for all users
    @commands.command(name="updeffect")
    async def update_effects_in_support_characters(self, ctx, character, effect, key, value, convertToInt = ""):
        if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
            if convertToInt.lower() == "t":
                value = int(value)

            index = None

            user_char = database_handler.users.find_one({"characters.name": character.replace("_", " ").title()}, { "characters.$": 1})

            for i, char_effect in enumerate(user_char['characters'][0]['effects']):
                if effect == char_effect['stat']:
                    index = i
            
            if index is None:
                return await ctx.send("Something went wrong.")

            database_handler.users.update_many({"characters.name": character.replace("_", " ").title()}, {"$set": {f"characters.$.effects.{index}.{key}": value}})
            return await ctx.send(f"{character}'s {effect} has had {key} changed to {value}")


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

    
    @update_character.error
    @un_update_character.error
    @update_effects_in_support_characters.error
    @unload.error
    @load.error
    @reload.error
    @add_item.error
    @level_up.error
    async def cooldown_error(self, ctx, error):
        # Sends a cooldown message if command is reused when on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            user_id = ctx.author.id
            cooldown_string = cooldown_calculator(round(error.retry_after))

            if user_id not in self.warned_cooldown_users:
                self.warned_cooldown_users.add(user_id)
                await ctx.send(f'Can\'t you be patient and just wait for {cooldown_string}')
            
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
    await bot.add_cog(Owner_Commands(bot))
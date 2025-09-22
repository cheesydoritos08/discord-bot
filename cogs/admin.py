from discord.ext import commands
import handlers.database_handler as database_handler
from utils.utility_functions import cooldown_calculator, create_error_embed
from utils.buttons import ViewGuildsButton
import asyncio
import os
import sys

class Owner_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Test command to check leveling
    @commands.command(name = "lvlup")
    async def level_up(self, ctx, *, character_name):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                xp = 50 * 2000
                character_xp_level = database_handler.increment_character_xp(user_id=ctx.author.id, xp=xp, character=character_name, return_xp=True)
                    
                await ctx.send(f"{character_name.title()} currently has {character_xp_level}/2000.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")


    # Test command to add character to my team
    @commands.command(name = "addchar")
    async def add_character(self, ctx, *, character_name):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                user_id = ctx.author.id

                user_character = database_handler.user_character_finder(user_id=user_id, character_name=character_name.strip().title())
                
                if user_character is not None:
                    return await ctx.send(f"You already own {character_name.title()}")

                character = database_handler.all_characters.find_one({"name": character_name.title()})

                database_handler.add_array_to_users(
                    user_id=user_id, key='characters', array=character
                )
                
                await ctx.send(f"{character_name.title()} has been added.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

    # Loads the specified extension
    @commands.command()
    async def load(self, ctx, extension):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                await self.bot.load_extension(f'cogs.{extension}')
                await ctx.send(f'Loaded {extension} cog')
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")


    # Searches for a character and changes their stat for all users
    @commands.command(name="updchar")
    async def update_character(self, ctx, character, stat, value, convertToInt = ""):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                if convertToInt.lower() == "t":
                    value = int(value)
            
                database_handler.users.update_many({"characters.name": character.replace("_", " ").title().replace("Ui", "UI")}, {"$set": {f"characters.$.{stat}": value}})
                database_handler.users.update_many({"team.name": character.replace("_", " ").title().replace("Ui", "UI")}, {"$set": {f"team.$.{stat}": value}})

                print(f"{character} has had {stat} changed to {value}")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

        
    # Removes a stat from a character    
    @commands.command(name="unupdchar")
    async def un_update_character(self, ctx, character, stat):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
            
                database_handler.users.update_many({"characters.name": character.replace("_", " ").title().replace("Ui", "UI")}, {"$unset": {f"characters.$.{stat}": ""}})
                database_handler.users.update_many({"team.name": character.replace("_", " ").title().replace("Ui", "UI")}, {"$unset": {f"team.$.{stat}": ""}})

                print(f"{character} has had {stat} changed to None")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

    # Searches the effects of the given character and updates them for all users
    @commands.command(name="updeffect")
    async def update_effects_in_support_characters(self, ctx, character, effect, key, value, convertValueToInt = ""):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                if convertValueToInt.lower() == "true":
                    value = int(value)

                index = None

                user_char = database_handler.users.find_one({"characters.name": character.replace("_", " ").title()}, { "characters.$": 1})

                for i, char_effect in enumerate(user_char['characters'][0]['effects']):
                    if effect == char_effect['stat']:
                        index = i
                
                if index is None:
                    return await ctx.send("Something went wrong.")

                database_handler.users.update_many({"characters.name": character.replace("_", " ").title()}, {"$set": {f"characters.$.effects.{index}.{key}": value}})
                database_handler.users.update_many({"team.name": character.replace("_", " ").title()}, {"$set": {f"team.$.effects.{index}.{key}": value}})

                return await ctx.send(f"{character}'s {effect} has had {key} changed to {value}")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

    # Searches the effects of the given character and updates them for all users
    @commands.command(name="unupdeffect")
    async def un_update_effects_in_support_characters(self, ctx, character, effect, key):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                index = None

                user_char = database_handler.users.find_one({"characters.name": character.replace("_", " ").title()}, { "characters.$": 1})

                for i, char_effect in enumerate(user_char['characters'][0]['effects']):
                    print(char_effect['stat'])
                    if effect == char_effect['stat']:
                        index = i
                
                if index is None:
                    return await ctx.send("Something went wrong.")

                database_handler.users.update_many({"characters.name": character.replace("_", " ").title()}, {"$unset": {f"characters.$.effects.{index}.{key}": ""}})
                database_handler.users.update_many({"team.name": character.replace("_", " ").title()}, {"$unset": {f"team.$.effects.{index}.{key}": ""}})

                return await ctx.send(f"{character}'s {effect} has had {key} changed to None")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")



    # Unloads the specified extension
    @commands.command()
    async def unload(self, ctx, extension):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                await self.bot.unload_extension(f'cogs.{extension}')
                await ctx.send(f'Unloaded {extension} cog')
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")


    # Reloads the specified extension
    @commands.command()
    async def reload(self, ctx, extension):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                await self.bot.reload_extension(f'cogs.{extension}')
                await ctx.send(f'Reloaded {extension} cog')
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")


    # Adds an item to the user inventory
    @commands.command(name="add")
    async def add_item(self, ctx, *, item):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285 or ctx.author.id == 1414654749705371768:
                database_handler.add_item(user_id= ctx.author.id, item=item)
                await ctx.send(f"{item} has been added.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")


    # Returns an embed with all the guilds that my bot is in
    @commands.command(name="viewguild")
    async def view_guild_info(self, ctx, id : int = None):
        try:
            if ctx.author.id == 867217023125553162 or ctx.author.id == 1031552625734324285:
                
                if id:
                    guilds = []
                    guilds.append(self.bot.get_guild(id))
                else:
                    guilds = self.bot.guilds

                view = ViewGuildsButton(bot=self.bot, guilds=guilds, ctx=ctx)

                await ctx.send(embed=await view.create_embed(guilds[0]), view=view)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

        

async def setup(bot):
    await bot.add_cog(Owner_Commands(bot))
from discord.ext import commands
from utils.utility_functions import create_error_embed, cooldown_calculator
import asyncio
from handlers import database_handler

class Setup(commands.Cog):
    # Initializes the class
    def __init__(self, bot):
        self.bot = bot

    # Adds a prefix entered by the user into their list of prefixes
    @commands.command(help="With this command, you can add a prefix to your server! Prefixes entered must be wrapped in brackets ([]) and will be case sensitive. The default prefix is '?'. You must have admin permissions to use this command.",
                      name="addprefix",
                      aliases=["addpfx"])
    @commands.has_permissions(administrator = True)
    async def add_prefix(self, ctx, *, prefix):
        # Ensures the command format is followed
        for x in range(2):
            if (x == 0 and prefix.find('[') != 0) or (x == 1 and prefix.rfind(']') != (len(prefix)-1)):
                return await ctx.send('Please surround the prefix you want to add in brackets ([])')
            
            if x == 0:
                prefix = prefix.replace('[', '', 1)   
            elif x == 1:
                prefix = prefix[0: prefix.rfind(']')] 
        
        # Sends a confirmation message to user 
        await ctx.send(f"Are you sure you want to add `{prefix}` into your list of server prefixes for this bot? Reply with Y/N")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout = 10)
            
            # Checks to see if they confirmed their choice or not
            if msg.content.lower() == "y":
                
                # Adds the new prefix to the list of guild prefixes
                new_guild_prefixes = []
                guild_prefixes = database_handler.guild_prefixes.find_one({"_id": ctx.guild.id})
                
                if guild_prefixes is None:
                    new_guild_prefixes = ["?", f"{prefix}"]
                elif guild_prefixes is not None:
                    new_guild_prefixes = guild_prefixes["prefixes"]
                    new_guild_prefixes.append(f"{prefix}")


                # Saves the new prefix based on their decision
                database_handler.guild_prefixes.update_one({"_id": ctx.guild.id}, {"$set": {"prefixes": new_guild_prefixes}})
                return await ctx.send(f"`{prefix}` has been added to the list of server prefixes.")
                            
            # Cancels command if the response is not yes
            elif msg.content.lower() == "n":
                return await ctx.send("Command has been cancelled")
            else:
                return await ctx.send("Invalid response")

        except asyncio.TimeoutError:
            return await ctx.send("Command timed out. Try again.")
        except Exception as e:
            create_error_embed(error=e, ctx=ctx, msg="This occured while someone tried to add a prefix to a server.")

    @commands.command(help="With this command, you can remove a prefix from your server! Prefixes are case sensitive and must be wrapped in brackets ([]) when using the command. You must have admin permissions to use this command.",
                      name="removeprefix",
                      aliases=["removepfx"])
    @commands.has_permissions(administrator = True)
    async def remove_prefix(self, ctx, *, prefix):
        # Ensures the command format is followed
        for x in range(2):
            if (x == 0 and prefix.find('[') != 0) or (x == 1 and prefix.rfind(']') != (len(prefix)-1)):
                return await ctx.send('Please surround the prefix you want to add in brackets ([])')
            
            if x == 0:
                prefix = prefix.replace('[', '', 1)   
            elif x == 1:
                prefix = prefix[0: prefix.rfind(']')] 
                
        # Confirms the prefix they want removed from the server
        await ctx.send(f"Are you sure you want to remove `{prefix}` from the server prefix list? Please reply with Y/N")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', timeout = 10, check=check)
            
            # Depending on the response, the prefix is removed
            if msg.content.lower() == "y":
                guild_prefixes = database_handler.guild_prefixes.find_one({"_id": ctx.guild.id})

                if guild_prefixes is not None:
                    # Checks to see if they only have one prefix left
                    if len(guild_prefixes['prefixes']) == 1:
                        return await ctx.send("You only have one prefix left. Please don't try to remove any more.")
                    
                    prefix_found = False 

                    for guild_prefix in guild_prefixes['prefixes']:
                        # Finds the prefix and removes it from the list
                        if guild_prefix == prefix:
                            guild_prefixes['prefixes'].remove(guild_prefix)
                            database_handler.guild_prefixes.update_one({"_id": ctx.guild.id}, {"$set": {"prefixes": guild_prefixes['prefixes']}})
                            prefix_found = True
                    
                    # Checks to see if the prefix was found and was removed from the server list
                    if prefix_found:
                        return await ctx.send(f"`{prefix}` has been removed from the server list.")
                    else:
                        return await ctx.send(f"`{prefix}` was not found in server list.")                   

            elif msg.content.lower() == "n":
                return await ctx.send("Command cancelled.")
            else:
                return await ctx.send("Invalid response.")

        except asyncio.TimeoutError:
            return await ctx.send("Command timed out.")
        except Exception as e:
            create_error_embed(error=e, ctx=ctx)


    @remove_prefix.error
    @add_prefix.error
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
            create_error_embed(ctx=ctx, error=error)
            

async def setup(bot):
    await bot.add_cog(Setup(bot))
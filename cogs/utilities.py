import time
import asyncio
import handlers.database_handler as database_handler
import discord
import os
import sys
from discord.ext import commands
from utils.converters import InventoryConverter, UseChipConverter, BuySellConverter
from utils.buttons import InviteButton, CraftingButtons, AnnouncementButton
from utils.utility_functions import update_quests, cooldown_calculator, create_error_embed
from utils.timer import Timer

class Utilites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    # Allows users to use xp and won boosts
    @commands.command(name="boost")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def use_boost(self, ctx, *, item : InventoryConverter):
        try:
            # Checks to see if the user exists and gets their inventory
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
    
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})
            inventory = user_profile.get("inventory")
        
        # Makes sure only won and xp boosters are being used
            if item != "won_booster" and item != "xp_booster":
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

                if item == "won_booster":
                    update_quests(user_id=ctx.author.id, quest_id="use_won_booster", amount=1)
                elif item == "xp_booster":
                    update_quests(user_id=ctx.author.id, quest_id="use_xp_booster", amount=1)

                # Creates a timer for the boost
                timer = Timer(user_id=ctx.author.id, name=item, starttime=start_time, timer_length=60 * inventory[item]["time_period"])
                timer.create_timer()
            else:
                return await ctx.send("Can't use what you don't have. This isn't rocket science.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to use a booster on line {line_num}")


    # Allows users to use chips to upgrade characters faster
    @commands.command(name="chip",
                      help="This command lets you use XP chips to level up your characters. Each XP chip gives 1000 XP points. The format for this command is `?chip <character name> <amount>`. If your character goes over the level cap when you use your chips, you will **not** be refunded the leftover chips so be careful.")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def use_chip(self, ctx, *, arg : UseChipConverter):
        try:
            # Checks to see if the user exists
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
    
            # Sets variables based on the converter
            character, amount = arg
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})
            inventory = user_profile["inventory"]

            # Checks to see if the user has enough chips
            if not inventory.get("xp_chip") or inventory.get("xp_chip", {}).get("amount", 0) == 0 or inventory.get("xp_chip", {}).get("amount", 0) < amount:
                return await ctx.send("You don't even have enough chips. Sad.")

            if amount < 1:
                return await ctx.send("Doesn't work like that.")

            # Increases the level of the character if owned
            for char in user_profile["characters"]:
                if char["name"].lower() == character.lower():
                    leveling_cap = 30
                    if char['LVL'] == leveling_cap:
                        return await ctx.send(f'You can\'t go past level {leveling_cap}.')
                    
                    database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.xp_chip.amount", value=-amount)
                    database_handler.increment_character_xp(user_id=ctx.author.id, character=character.lower(), xp= 1000 * amount)
                    update_quests(user_id=ctx.author.id, quest_id="use_xp_chip", amount=1)

                    char_level = database_handler.users.find_one({"_id": ctx.author.id, "characters.name": character.title()}, {'characters.$': 1}).get('characters')[0]['LVL']

                    return await ctx.send(f"{character} has been leveled up. They are currently level {char_level}")
            
            return await ctx.send(f"You don't own {character} stupid.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to use an xp chip on line {line_num}")


    # Displays the current timers and how much time is left on them
    @commands.command(name="timers",
                      help="This command displays all the timers you have currently. Use this to check how much time left you have on your boosters or to see when your daily quests reset!")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def display_timers(self, ctx):
        try:
            # Checks to see if the user exists and gets the profile
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return

            user_profile= database_handler.users.find_one({"_id": ctx.author.id})
            user_timers = user_profile["timers"]

            # Creates an embed displaying the timer based on their current state
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
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to display timers on line {line_num}")


    @commands.command(name="invite",
                      help="This command sends a link to invite the bot to your server and for you to join the bot's official server!")
    async def invite_bot(self, ctx):
        try:
            # Creates an embed with buttons to invite the bot to the server
            view = InviteButton()
            embed = discord.Embed(title="Invites",
                                description="Join the bot's official server if you have any questions or if you want to report a bug! Users who report bugs will be granted a reward when they are fixed!")
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to run the invite command on line {line_num}")

            
    @commands.command(name="vote",
                      help="This command lets you vote for the bot on top.gg! Voting for the bot rewards you 2000 won and one shard of a random rarity, all the way up to Legendary!")
    async def vote_for_bot(self, ctx):
        try:
            # Checks to see if the user exists
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                    return 
                
            # Sets the variables of the profile and the voting buttons
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})
                
            view = discord.ui.View()
            button = discord.ui.Button(style=discord.ButtonStyle.url, url="https://top.gg/bot/1371573491391922278", label="Vote for the bot!")
            button2 = discord.ui.Button(style=discord.ButtonStyle.url, url="https://top.gg/discord/servers/723715072636399616", label="Vote for the server!")

            view.add_item(button)
            view.add_item(button2)

            # Creates an embed telling you to vote for the server and bot
            embed = discord.Embed(title="Vote for the Lookism Bot and the server!",
                                    description="By voting for the bot and the server on Top.gg, you get 2000 won and \na random fragment of your choice. The greater your vote\nstreak, the higher the chance of you getting a legendary\nfragment whenever you vote. Voting for the server doesn't\ngive you anything but is much appreciated!")

            embed.set_footer(text=f"Vote Streak: {user_profile.get("vote", {}).get("vote_streak")}")
            
            await ctx.send(view=view, embed=embed)
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to vote for the bot on line {line_num}")


    @commands.command(name="viewprefixes",
                      aliases=["viewpfxs"],
                      help="With this command, you can view all the prefixes that can be used with this bot in your server!")
    async def view_prefixes(self, ctx):
        try:
            # Retrieves a list of the guild prefixes 
            guild_prefixes = database_handler.guild_prefixes.find_one({"_id": ctx.guild.id}).get("prefixes")

            embed = discord.Embed(title="Prefixes for this Server",
                                description=f"{guild_prefixes}",
                                color=discord.Color.dark_purple())
            
            await ctx.send(embed=embed)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to view prefixes on line {line_num}")


    @commands.command(name="craft",
                      help="This command allows you to craft items with the materials that you have. The format for this command is ?craft <item name> <amount> To see all crafting recipes, just type ?craft. ")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def craft_item(self, ctx, *, arg : BuySellConverter = None):
        try:
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            if arg is None:
                # Sends an embed containing all the crafting recipes
                items = [item for item in database_handler.items.find({"crafting": {"$exists": True}})]
                crafting_buttons = CraftingButtons(items=items, ctx=ctx)
                embed = crafting_buttons.create_embed()
                return await ctx.send(embed=embed, view=crafting_buttons)

            else:
                # Gets the item and the amount the user wants to craft
                item, amount_wanted = arg
                item = database_handler.items.find_one({'name': item}, {'crafting': 1, 'name': 1, '_id': 0})

                if item is None:
                    return await ctx.send("Not craftable. Check craftables by just typing `?craft`.")
                
                materials_needed = item.get('crafting')

                user_inventory = database_handler.users.find_one({"_id": ctx.author.id}, {"_id": 0, "inventory": 1}).get('inventory')

                # Checks to see if the user has the required material in order to craft the item(s)
                for material_name, material_amount in materials_needed.items():
                    materials_needed[material_name] *= amount_wanted

                    item_found = False

                    for inventory_item, item_details in user_inventory.items():
                        if inventory_item == material_name and item_details['amount'] < material_amount:
                            return await ctx.send(f"You don't have enough {material_name.replace("_", " ")}(s) to craft this item. Poor.")
                        
                        elif inventory_item == material_name and item_details['amount'] >= material_amount:
                            item_found = True
                    
                    if not item_found:
                            return await ctx.send(f"You don't have enough {material_name.replace("_", " ")}(s) to craft this item. Poor.")
                        
                # Decrements the materials needed for the item
                for material_name, material_amount in materials_needed.items():
                    database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{material_name}.amount", value=-material_amount)

                # Checks to see if the user already has the item in their inventory
                # and if so, adds the item they want crafted to their inventory
                for inventory_item, item_details in user_inventory.items():
                    if inventory_item == item["name"]:
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item['name']}.amount", value=amount_wanted)
                        return await ctx.send(f"You crafted {amount_wanted} {item_details['emoji']} {item["name"].replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")}(s).")

                # Adds the item to the user's inventory if they don't already have it
                # then adds the number of items they want
                database_handler.add_item(user_id=ctx.author.id, item=item['name'])
                database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item['name']}.amount", value=amount_wanted)
                return await ctx.send(f"You crafted {amount_wanted} {item_details['emoji']} {item["name"].replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")}(s).")
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to craft an item on line {line_num}")

    @commands.command(name="announcements",
                      aliases=["anns"],
                      help="With this command, you can view any announcements from the creator! If you want to be the first to know about any events or prizes, join the support server with the !invite command.")
    async def view_announcements(self, ctx):
        try:
            button = AnnouncementButton()
            embed = button.create_embed()

            # Sends the announcement embed
            return await ctx.send(embed=embed, view=button)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to view announcements on line {line_num}")




    @craft_item.error
    @vote_for_bot.error
    @view_prefixes.error
    @vote_for_bot.error
    @invite_bot.error
    @display_timers.error
    @use_chip.error
    @use_boost.error
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
    await bot.add_cog(Utilites(bot))
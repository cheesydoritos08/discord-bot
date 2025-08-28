import discord
from discord.ext import commands
import math
import random
import sys
import asyncio
from utils.utility_functions import create_error_embed
import handlers.database_handler as database_handler

#TO DO: MAKE CHALLENGE ITEMS WORK

# Buttons for the inventory command
class InventoryButtons(discord.ui.View):
    def __init__(self, *, timeout = 180, items, ctx, display_for_item_command = False, user = None):
        super().__init__(timeout=timeout)
        self.index = 0
        self.items = items
        self.num_on_items_per_page = 5
        self.ctx = ctx
        self.user = user
        self.display_for_item_command = display_for_item_command
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Makes sure the person interacting the sender of the command
        if interaction.user != self.ctx.author:
            await interaction.response.send_message('Only the author of the command can perform this action.', ephemeral=True,)
            return False
        return True

    async def create_embed(self, item = None):
        try:
            items_display_string = ""
            user_name = self.user if self.user is not None else self.ctx.author
        
        # If no item is specifically searched for, displays all the items in self.item
            if item is None:
                embed = discord.Embed(title=f"{user_name}'s Inventory",
                        description="∘₊✧─── ──── ──── ───✧₊∘",
                        colour=0xcb7667)
                
                position = 1
                displayable_items = [item for item in self.items if self.items.get(item, {}).get("amount") > 0]
                
                for item in displayable_items[self.index * self.num_on_items_per_page: (self.index + 1) * self.num_on_items_per_page]:
                    # Adds a position to the items if they are supposed to be displayed
                    # in a fighting command
                        item_name = item.replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")

                        if self.display_for_item_command:
                            item_name = f"{position}. {item_name}"
                            position += 1
                        
                        # Adds the item and the emoji to the display string
                        items_display_string += f"**{self.items[item]['emoji']} {item_name}**: {self.items[item]['amount']}\n"

                if items_display_string == "":
                    if not self.display_for_item_command:
                        # Tells the user that there's nothing in the inventory if the items
                        # aren't being displayed for a fighting command
                        await self.ctx.send("You have nothing in your inventory.")
                    return False
                
                embed.add_field(name="",
                    value=items_display_string,
                    inline=False)

                embed.set_thumbnail(url=user_name.display_avatar)

                embed.set_footer(text="∘₊✧──── ───── ───── ────✧₊∘")
                
                # Adds insturctions if the embed is being called during a fight
                if self.display_for_item_command:
                    embed.set_footer(text="∘₊✧ Type the number corresponding to the item you wanted to use. ✧₊∘")


            else:
                # Creates an embed showing just the item sent to the embed
                embed = discord.Embed(title=f"{user_name}'s Inventory",
                        description="∘₊✧─── ──── ──── ───✧₊∘",
                        colour=0xcb7667)
                
                if self.items.get(item) is None:
                    return await self.ctx.send("Search for a valid item.")
                elif self.items[item]["amount"]:
                    item_name = item.replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")
                    items_display_string += f"**{item_name}**: {self.items[item]['amount']}\n"
                else:
                    return await self.ctx.send("You do not have this item.")

                embed.add_field(name="",
                    value=items_display_string,
                    inline=False)

                embed.set_thumbnail(url=user_name.display_avatar)

                embed.set_footer(text="∘₊✧──── ───── ───── ────✧₊∘")
                
            return embed
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for the inventory buttons on line {line_num}")

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red)
    async def back_button(self, interaction, button):
        self.index = (self.index - 1) % (math.ceil(len(self.items) /  self.num_on_items_per_page))
        await interaction.response.edit_message(embed=await self.create_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.red)
    async def next_button(self, interaction, button):
        self.index = (self.index + 1) % (math.ceil(len(self.items) /  self.num_on_items_per_page))
        await interaction.response.edit_message(embed=await self.create_embed(), view=self)

# Buttons for the shop command
class ShopButtons(discord.ui.View):
    def __init__(self, *, timeout = 180, items, ctx):
        super().__init__(timeout=timeout)
        self.index = 0
        self.items = items
        self.num_of_items_per_page = 3
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message('Only the author of the command can perform this action.', ephemeral=True,)
            return False
        return True

    def create_embed(self):
        try:
            # Creates an embed displaying the items in the shop
            embed = discord.Embed(title="•─•°• Shop •°•─•")

            for item in self.items[int(self.index * self.num_of_items_per_page):int(((self.index * self.num_of_items_per_page) + self.num_of_items_per_page))]:
                embed.add_field(name=f"°˖✧ {item["emoji"]} {item["name"].replace("_", " ").title().replace("Xp", "XP")} ✧˖°",
                    value=f"`Buy Price:` ₩{item["buy_price"]}\n`Sell Price:` ₩{item.get('sell_price', "Not sellable")}",
                    inline=True)

            embed.set_footer(text="•─•°• To buy or sell an item, type ?buy/sell <item name> <amount> •°•─•")

            return embed
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for the shop on line {line_num}")

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red)
    async def back_button(self, interaction, button):
        try:
            self.index = (self.index - 1) % (math.ceil(len(self.items) / self.num_of_items_per_page))
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the back button for the shop buttons on line {line_num}")


    @discord.ui.button(label="Next", style=discord.ButtonStyle.red)
    async def next_button(self, interaction, button):
        try:
            self.index = (self.index + 1) % (math.ceil(len(self.items) / self.num_of_items_per_page))
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the next button for the shop buttons on line {line_num}")

# Buttons for the shop command
class CraftingButtons(discord.ui.View):
    def __init__(self, *, timeout = 180, items, ctx):
        super().__init__(timeout=timeout)
        self.index = 0
        self.items = items
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message('Only the author of the command can perform this action.', ephemeral=True,)
            return False
        return True

    def create_embed(self):
        try:
            # Creates an embed displaying the craftable items and their requirements
            crafting_requirements = database_handler.items.find_one({"name": self.items[self.index]['name']}).get('crafting')

            crafting_string = "**Crafting Requirements:**\n"

            for material_name, material_amount in crafting_requirements.items():
                crafting_string += f"{material_name.replace('_', " ").title()}: {material_amount}\n"

            embed = discord.Embed(title=f"{self.items[self.index]['name'].title().replace("_", " ").replace("Ev", "EV")}",
                                  description=f"**Description:**\n {self.items[self.index]['description']}\n\n{crafting_string}")

            embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{self.items[self.index]['emoji'][self.items[self.index]['emoji'].rfind(":") + 1:self.items[self.index]['emoji'].rfind(">")]}.webp?size=64&quality=lossless")
            embed.set_footer(text="•─•°• To craft an item, type ?craft <item name> <amount> •°•─•")

            return embed
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() 
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for crafting on line {line_num}")

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red)
    async def back_button(self, interaction, button):
        try:
            self.index = (self.index - 1) % (len(self.items))
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the back button for the crafting buttons on line {line_num}")


    @discord.ui.button(label="Next", style=discord.ButtonStyle.red)
    async def next_button(self, interaction, button):
        try:
            self.index = (self.index + 1) % (len(self.items))
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the next button for the crafting buttons on line {line_num}")

# Buttons for the mychars commands
class CharacterButton(discord.ui.View):
        def __init__(self, characters, ctx=None):
            super().__init__()
            self.index = 0
            self.characters = characters
            self.ctx = ctx

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.ctx.author:
                await interaction.response.send_message('Only the author of the command can perform this action.',ephemeral=True)
                return False
            return True

        # Returns the decorative items needed to indicate rarity
        def set_rarity_indicators(self, character):

            colors = {
                'Common': (discord.Color.green(),'https://files.catbox.moe/fen419.png',),
                'Rare': (discord.Color.blue(), 'https://files.catbox.moe/5s6egv.png'),
                'Epic': (discord.Color.purple(), 'https://files.catbox.moe/xt0w36.png'),
                'Legendary': (discord.Color.gold(),'https://files.catbox.moe/8hy2hm.png',),
            }

            return colors.get(character['rarity'])

        # Creates the embed for the pages
        def create_embed(self, character):
            try:
                # Sets the colors for the page
                bar_color, rarity_icon = self.set_rarity_indicators(character)
                if character['class'] == 'Support':
                    desc = f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **Threshold:** {character["threshold"]}\n> **Effect:** {character["description"]}'
                else:
                    special_effect = ""
                    special_effect_description = ""
                    if character.get('stun_chance'):
                        special_effect = "Stuns"
                        special_effect_description = f"Gives the character a {character['stun_chance']}% chance to stun the opposing team for {character['stun_duration']} turns"
                    elif character.get('crit_chance'):
                        special_effect = "Critical Hits"
                        special_effect_description = f"Gives the character a {character['crit_chance']}% chance to do {character['crit_damage']} times their normal damage"
                    elif character.get('dodge_chance'):
                        special_effect = "Dodging"
                        special_effect_description = f"Gives the character a {character['dodge_chance']}% to dodge all attacks for {character['dodge_duration']} turn(s)"


                    desc = f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **ATK:** {character["ATK"]}\n> **HP:** {character["HP"]}\n> **SPD:** {character["SPD"]}\n> **LVL:** {character["LVL"]}\n> **Threshold:** {character["threshold"]}\n> **Special Effect**: {special_effect}\n> **Special Effect Description**: {special_effect_description}\n> **XP:** {character["XP"]}/2000'

                embed = discord.Embed(title=character['name'], description=desc, color=bar_color)
                embed.set_image(url=character['image_url'])
                embed.set_footer(text=f'Page {self.index + 1}/{len(self.characters)}')
                if rarity_icon:
                    embed.set_thumbnail(url=rarity_icon)
                return embed
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
                line_num = exc_traceback.tb_lineno

                create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for the character buttons on line {line_num}")

        # Controls the back button
        @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
        async def previous_message(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                # Cycles through the list of chracters and sets the new embed to the corresponding page
                self.index = (self.index - 1) % len(self.characters)
                embed = self.create_embed(self.characters[self.index])
                await interaction.response.edit_message(embed=embed, view=self)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
                line_num = exc_traceback.tb_lineno

                create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the back button for the character buttons on line {line_num}")
            
        # Controls the extra info
        @discord.ui.button(label='More Info', style=discord.ButtonStyle.gray)
        async def display_more_info(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                # Gets the current character on the page
                character = database_handler.all_characters.find_one({"name": self.characters[self.index]['name']})
        
                # Creates an embed for the threshold requires for the character
                embed = discord.Embed(title="-ˋˏ ༻ Threshold Requirements ༺ ˎˊ-")

                for threshold in character.get('threshold_requirements').keys():
                    threshold_reqs_string = ""
                    for item, value in character['threshold_requirements'].get(threshold).items():
                        if item == "won":
                            threshold_reqs_string += f"> ❥ {item.replace("_", " ").title()}: ₩{value}\n"
                        elif item[-5:] == "shard":
                            emoji_dict = {
                                "Common": "<:common_shard:1390037115362087013>",
                                "Rare": "<:rare_shard:1390037161293774993>",
                                "Epic": "<:epic_shard:1390037195485610115>",
                                "Legendary": "<:legendary_shard:1390037232982954027>",
                            }
                            shard_emoji = emoji_dict[character.get("rarity")]
                            threshold_reqs_string += f"> ❥ {item.replace("_", " ").title()} {shard_emoji}: {value}\n"
                        elif item == "characters":
                            for char in character['threshold_requirements'][threshold]["characters"]:
                                character_emoji = database_handler.all_characters.find_one({"name": char['name']}).get("emoji")
                                threshold_reqs_string += f"> ❥ {char['threshold']}T {char['name']} {character_emoji}\n"
                        else:
                            item_emoji = database_handler.items.find_one({"name": item}).get("emoji")
                            threshold_reqs_string += f"> ❥ {item.replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")} {item_emoji}: {value}\n"


                    embed.add_field(name=f"-ˋˏ ༻ {threshold.replace("_", " ").title()} ༺ ˎˊ-",
                                    value=threshold_reqs_string,
                                    inline=False)

                embed.set_thumbnail(url=character.get('image_url'))

                embed.set_footer(text="Unlocking new thresholds makes your characters much stronger!")

                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
                line_num = exc_traceback.tb_lineno

                create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for the character display more info button on line {line_num}")


        # Controls the next button
        @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
        async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                self.index = (self.index + 1) % len(self.characters)
                embed = self.create_embed(self.characters[self.index])
                await interaction.response.edit_message(embed=embed, view=self)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
                line_num = exc_traceback.tb_lineno

                create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when pressing the next button for the character buttons on line {line_num}")

# Buttons for the view guilds command
class ViewGuildsButton(discord.ui.View):
        def __init__(self, bot, guilds, ctx=None):
            super().__init__()
            self.index = 0
            self.bot = bot
            self.guilds = guilds
            self.ctx = ctx

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.ctx.author:
                await interaction.response.send_message(
                    'Only the author of the command can perform this action.',
                    ephemeral=True,
                )
                return False
            return True

        # Creates the embed for the pages
        async def create_embed(self, guild):
            guild = await self.bot.fetch_guild(guild.id, with_counts=True)
                    
            embed = discord.Embed(title=guild.name,
                                    color=discord.Color.pink())
            embed.add_field(name="Info",
                                value=f"Owner Name: {await self.bot.fetch_user(guild.owner_id)}\nOwner ID: {guild.owner_id}\nDescription: {guild.description}\nOnline Members: {guild.approximate_presence_count}\nTotal Members: {guild.approximate_member_count}\nDay Created: {guild.created_at}\nUnavailable?: {guild.unavailable}")
                
            embed.set_thumbnail(url=guild.icon)
            embed.set_footer(text=f"{self.index+1} / {len(self.guilds)}")
            return embed

        # Controls the back button
        @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
        async def previous_message(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            # Cycles through the list of chracters and sets the new embed to the corresponding page
            self.index = (self.index - 1) % len(self.guilds)
            embed = await self.create_embed(self.guilds[self.index])
            await interaction.response.edit_message(embed=embed, view=self)

        # Controls the next button
        @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
        async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.index = (self.index + 1) % len(self.guilds)
            embed = await self.create_embed(self.guilds[self.index])
            await interaction.response.edit_message(embed=embed, view=self)

# Creates the buttons sent for the tutorial
class TutorialButton(discord.ui.View):
    def __init__(self, *, timeout=60):
        super().__init__(timeout=timeout)
        self.index = 0
        self.button = discord.ui.Button(label="Join the bot's official server!", style=discord.ButtonStyle.url, url="https://discord.gg/EaaF8aMCxG")

        # Stores all the messages the tutorial will cycle through
        self.titles = [
            'Welcome to the Lookism Bot!',
            'Setting up the Bot (Pt. 1)',
            'Setting up the Bot (Pt. 2)',
            'Setting up the Bot (Pt. 3)',
            'Buying Tickets',
            'Rolling for New Characters',
            'Rolling on the Standard Banner vs the Limited Time Banner',
            'Rolling Duplicates',
            'Creating a Team',
            'Fighting Other Players',
            'ELO Scores and Rankings',
            'Global ELO Leaderboard',
            'Going on Raids',
            'Gaining More Money',
            'Trading with Other Players',
            'End of the Tutorial'
        ]
        self.descriptions = [
            "Welcome to the Lookism Bot! This tutorial goes the core mechanics of the bot so feel free to revisit it as much as you want! If you ever want to find out more about a command, use the ?help command. DISCLAIMER: This bot was meant to be used in a server. Using the bot in direct messages may lead to the bot working incorrectly. Do so at your own risk. (Pictures are unrelated to the tutorial, they just look cool. All credits go to the original creators.)",
            "Setting up the bot is really easy! If you're not an adminstrator, you can skip the next two pages. If you're an administrator, you can type ?addprefix [prefix] to add a prefix to the server. The square brackets are required for the command to work and the characters typed inside of them are case sensitive so be careful! If you want a space between your prefix and the commands, make sure to include it in the brackets as well.",
            "To view the list of prefixes you currently have set, type ?viewprefixes. Adding a prefix to the bot will not remove other prefixes so make sure to remove any unwanted prefixes!",
            "To remove a prefix, type ?removeprefix [prefix]. Once again, the command is case sensitive so make sure to type the prefix exactly as it's show in the viewprefixes command!",
            "Finally, you can get to the fun part, gambling! To gamble for characters, you need to buy some tickets. You already have some money in your wallet so use the ?shop command to buy some standard tickets. To buy an item, type ?buy <item name> <amount>. You can also sell items in the shop if you type ?sell <item name> <amount>. (The <>s are not included in the command.)",
            "After you buy some tickets, roll on the standard banner to get characters. To roll on the standard banner, type ?roll standard. You can only roll one character at a time.",
            "Rolling on the limited time banner grants you the chance to roll the legendary character for the week. The legendary character on the banner rotates from week to week and you can check the current legendary by visiting the bot's support server! Limited tickets can only be obtained from raids so if you want the legendary, try and complete some raids!",
            "When you roll duplicates, you get shards which will be stored in your inventory. These shards are used to unlock character thresholds! To see the requirements for each threshold for each character, click the 'More Info' button when you type ?mycharacters or ?allcharacters.",
            "After rolling your characters, you can add them to your team with ?addteammember <character full name> (<>s not included). Each team consists of three fighters and one support! Your team can then be used to challenge other players or to fight in raids.",
            "To challenge a player, type ?challenge <@user> (<>s not included). Challenging other players grants you money and xp which helps you level up your characters!",
            "Besides granting you won and xp, challenging players also increases your ELO score on every win! By increasing your ELO score, you can unlock new ranks which given you *permanent* money boosts to your account. To check your ELO score and rank, you can use the ?profile command!",
            "There's a global leaderboard that displays the current all time highest ELOs across the entire bot database! If you're strong enough, you could end up on there!",
            "If you don't have any friends to challenge, you can run the raid command by typing ?raid! Going on raids grants you xp and items that can be used on yourself or on your team members! Raid levels are also replayable so once you beat a level, you can always go back and start from it by typing ?raid <level> (<>s not included).",
            'Besides challenging players to fights, you can earn money through completeling daily quests with the ?quests command, claiming your daily reward with the ?daily command, voting for bot on Top.gg with the ?vote command, gambling your money with the ?coinflip command and playing higher or lower with the ?highlow command!',
            "You can also trade with other players! To find out more about trading, type ?help trade!",
            'That\'s it for the tutorial! If you have any question, join the official bot server!'
                  ]
        self.image_urls = [
            'https://i.pinimg.com/736x/80/e0/ac/80e0ace80f573d27333a042e6e51d211.jpg',
            'https://i.pinimg.com/736x/36/3b/14/363b140a2c18951cb7098b4ca3029a29.jpg',
            'https://i.pinimg.com/736x/a6/3b/70/a63b70b5844d615c15dafa00a4e6e5fc.jpg',
            'https://i.pinimg.com/736x/e4/19/22/e41922b040e2497540338354d2abf642.jpg',
            'https://i.pinimg.com/736x/cd/00/59/cd005980e8bdfa6555c363da7f60828b.jpg',
            'https://i.pinimg.com/736x/c7/24/b1/c724b17aeef7f4425d84e42b7e25edf7.jpg',
            'https://i.pinimg.com/736x/b6/75/d9/b675d9808666b86f70329dc54b2ce1c2.jpg',
            'https://i.pinimg.com/736x/62/fa/cd/62facd814343f993ecf7d06410ea9dcd.jpg',
            'https://i.pinimg.com/736x/81/0b/d8/810bd837a04dde0979c14feb993bba7f.jpg',
            'https://i.pinimg.com/736x/a6/3b/70/a63b70b5844d615c15dafa00a4e6e5fc.jpg',
            'https://i.pinimg.com/736x/c6/b0/0f/c6b00f5812531a034034982c406558e7.jpg',
            'https://i.pinimg.com/736x/3f/d9/89/3fd989bef5b46bd37b89dac3175a34ac.jpg',
            'https://i.pinimg.com/736x/a7/6b/23/a76b2365283c13b66f6ba94b3fe2afd8.jpg',
            'https://i.pinimg.com/736x/ab/24/5e/ab245ef29ef379c752a278887ee9d41c.jpg',
            'https://i.pinimg.com/736x/80/0d/81/800d8184407ff3842139c6ecbd259e52.jpg',
            'https://i.pinimg.com/736x/c8/e4/97/c8e4979d162d9ce3df3cd4317a147027.jpg',

        ]

    # Adds the invite button based on the page
    def add_invite_button(self):
        if self.index == 6 or self.index == 15:
            self.add_item(self.button)


    # Controls the back button
    @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
    async def previous_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cycles through the list of message and sets the new embed to the corresponding page
        self.index = (self.index - 1) % len(self.titles)

        self.remove_item(self.button)
        self.add_invite_button()

        embed = discord.Embed(
            title=self.titles[self.index],
            description=self.descriptions[self.index],
            color=discord.Color.purple(),
        )
        embed.set_image(url=self.image_urls[self.index])
        await interaction.response.edit_message(embed=embed, view=self)

    # Controls the next button
    @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
    async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cycles through the list of message and sets the new embed to the corresponding page
        self.index = (self.index + 1) % len(self.titles)
        self.remove_item(self.button)
        self.add_invite_button()

        embed = discord.Embed(
            title=self.titles[self.index],
            description=self.descriptions[self.index],
            color=discord.Color.purple(),
        )
        embed.set_image(url=self.image_urls[self.index])
        await interaction.response.edit_message(embed=embed, view=self)

# Creates the buttons pressed by the user
class GameFighterButton(discord.ui.Button):
    def __init__(self, label, character, game):
        super().__init__(label=label, style=discord.ButtonStyle.red)
        self.character = character
        self.game = game

    async def on_button_click(self, interaction: discord.Interaction, simulated_click = False, embed_message_id = None):   
        try:
       # Sets the current team to nothing     
            current_team = None
            game_over = False

            # Sends the info from the button press to the game to determine the logic
            if self.game.turn == "team_1":
                current_team = self.game.player_two_team
                self.game.player_one_character = self.character
                self.game.turn = "team_2"
            else:
                current_team = self.game.player_one_team
                self.game.player_two_character = self.character
                self.game.turn = "team_1"
                self.game.determine_final_damage()
            

            # Creates an embed displaying the current fight
            embed = self.game.create_embed()
            view = self.game.create_character_buttons(team=current_team)
            
            if self.game.game_type == "challenge":
                # Checks to see if any of the players won
                if await self.game.check_player_win(self.game.player_one_team) or await self.game.check_player_win(self.game.player_two_team):
                    game_over = True
                    self.game.send_timeout_message = False

                # Sends the new view if the game hasn't ended yet
                if not game_over:
                        next_player = self.game.player_one if self.game.turn == "team_1" else self.game.player_two
                        
                        # Sends a message to indicate who can go next
                        if not simulated_click:
                            await interaction.response.send_message(
                                content=f"It is {next_player.mention}'s turn to choose a character!",
                                embed=embed,
                                view=view,
                            )
                        else:
                            await interaction.followup.send(
                                content=f"It is {next_player.mention}'s turn to choose a character!",
                                embed=embed,
                                view=view,
                            )

                        self.game.combat_log = ["Awaiting player actions..."]

            
            else:                    
                if current_team == self.game.player_one_team:
                    embed.set_footer(text="Choose your fighter!")
                else:
                    embed.set_footer(text="Choose which enemy to attack!")

                # Checks to see if the level ended or if the raid ended
                self.game.check_level_end()
                game_over = await self.game.check_raid_end(interaction)

                if not game_over:
                        # Sends a message to indicate who can go next
                    if not simulated_click:
                        await interaction.response.edit_message(embed=embed, view=view)
                    else:
                        await interaction.followup.edit_message(message_id=embed_message_id, embed=embed, view=view)
                
                    self.game.combat_log = ["Awaiting player actions..."]


                elif game_over:
                    self.game.send_timeout_message = False
        

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.game.ctx, msg=f"This occured when clicking the character button in a fight between users on line {line_num}")

class GameItemButton(discord.ui.Button):
    def __init__(self, label, game):
        super().__init__(label=label, style=discord.ButtonStyle.red)
        self.game = game
        self.pressed = False

    async def prompt_user_for_item(self, interaction, inventory_embed, inventory_view, inventory_length, embed_message_id):
        for x in range(3):
            def check(msg):
                return msg.author == interaction.user and msg.channel == interaction.channel

            try:
                msg = await self.game.bot.wait_for('message', timeout=10, check=check)
                self.pressed = False

                item_number = int(msg.content)
                
                if item_number < 1 or item_number > inventory_length:
                    if x == 2:
                        raise asyncio.TimeoutError
                    
                    await interaction.followup.send("Please enter the number for the corresponding item you want to use.", ephemeral = True)
                    continue
                else:
                    # Gets the items stored in the inventory view
                    inventory_items = inventory_view.items
                    # Gets the item chosen by the user
                    item = {k:v for k, v in inventory_items.items() if k == list(inventory_items.keys())[item_number - 1]}
                    # Gets the item name
                    item_name = list(item.keys())[0]

                    # Adds the item to the items in use in order to check duration and applies the boosts from the item
                    if self.game.turn == "team_1":
                        self.game.p1_items_in_use.append(item)
                        self.game.combat_log.append(f"{interaction.user} used 1x {item_name.replace("_", " ").title()}. They can use {3 - (self.game.p1_num_of_items_used + 1)} more items.")
                    elif self.game.game_type == "challenge" and self.game.turn == "team_2":
                        self.game.p2_items_in_use.append(item)
                        self.game.combat_log.append(f"{self.game.player_two} used 1x {item_name.replace("_", " ").title()}. They can use {3 - (self.game.p2_num_of_items_used + 1)} more items.")

                    self.game.apply_item_boosts(item=item)
                    database_handler.inc_value_to_users(user_id=interaction.user.id, key=f"inventory.{item_name}.amount", value=-1)

                    # Selects a random character for the enemy to target                    
                    for button in self.view.children:
                        if button.label == "Items":
                            self.view.remove_item(button)
                            break

                    random_num = random.randint(0, (len(self.view.children) - 1))
                    button = self.view.children[random_num]
                    
                    await button.on_button_click(interaction=interaction, simulated_click = True, embed_message_id = embed_message_id)
                    break
                    
            except asyncio.TimeoutError as e:
                    # Moves on to the next turn
                    for button in self.view.children:
                        if button.label == "Items":
                            self.view.children.remove(button)
                            continue

                    random_num = random.randint(0, len(self.view.children) - 1)
                    button = self.view.children[random_num]
                    
                    await button.on_button_click(interaction=interaction, simulated_click = True, embed_message_id = embed_message_id)
                    break

            except TypeError as e:
                    # Makes sure that the user enters a number within the range
                    if x == 2:
                        raise asyncio.TimeoutError
                    
                    await interaction.followup.send("Please enter the number for the corresponding item you want to use.", ephemeral=True, view = inventory_view, embed = inventory_embed)
                    continue
            except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info() 
                    line_num = exc_traceback.tb_lineno

                    create_error_embed(error=e, ctx=self.game.ctx, msg=f"This occured when prompting the user to pick an item for the raid on line {line_num}")

    async def on_button_click(self, interaction: discord.Interaction): 
        try:
            await interaction.response.defer()
            # Debounce to prevent clicking multiple times
            if self.pressed:
                return

            int_message = interaction.message
            embed_message_id = int_message.id
            self.pressed = True

            for child in self.game.view.children:
                if child.label != "Items":
                    child.disabled = True

            user_profile = database_handler.users.find_one({"_id": interaction.user.id})
            item_inventory = {x['name']: x for x in database_handler.items.find({}) if "effects" in x}
            user_inventory = user_profile.get('inventory')

            # Gets all the items in the user's inventory
            user_item_inventory = {item_name: info for (item_name, info) in user_inventory.items() if "effects" in info}
            user_item_inventory = {item_name: info for (item_name, info) in item_inventory.items() if user_item_inventory.get(item_name, {}).get("amount", -1) > 0}
            
            # Makes sure that the items in the list have the correct amounts from the user since the dict user_item_inventory
            # pulls from the database which automatically sets all amounts to 0
            for item_name, info in user_item_inventory.copy().items():
                user_item_inventory[item_name]['amount'] =  user_inventory[item_name]['amount']

            # Creates the embed for the items
            view = InventoryButtons(items=user_item_inventory, ctx=self.game.ctx, display_for_item_command=True)
            embed = await view.create_embed()

            if self.game.game_type == "challenge":
                num_of_items_used = self.game.p1_num_of_items_used if self.game.turn == "team_1" else self.game.p2_num_of_items_used
            else:
                num_of_items_used = self.game.p1_num_of_items_used

            # Prevents the user from using more than three items
            if not embed or num_of_items_used >= 3:
                for child in self.game.view.children:
                    if child.label != "Items":
                        child.disabled = False
                    else:
                        child.disabled = True

                return await interaction.followup.edit_message(message_id = embed_message_id, view=self.game.view)

            # Keeps prompting the user up to 3 times to enter a number
            asyncio.create_task(self.prompt_user_for_item(interaction=interaction, inventory_embed=embed, inventory_view=view, inventory_length=len(user_item_inventory.keys()), embed_message_id= embed_message_id))

            await interaction.followup.send(embed = embed, view = view, ephemeral= True)
            await int_message.edit(view=self.game.view)

        except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info() 
                line_num = exc_traceback.tb_lineno

                create_error_embed(error=e, ctx=self.game.ctx, msg=f"This occured in the raid item button on line {line_num}")



        # make it so that the bot prompts the user to choose an item 3 times before skipping their turn

# Creates the button for the invite command
class InviteButton(discord.ui.View):
    def __init__(self, *, timeout = 10):
        # Creates the invite buttons and adds them to the view
        super().__init__(timeout=timeout)
        server_button = discord.ui.Button(label="Join the bot's official server!", style=discord.ButtonStyle.url, url="https://discord.gg/EaaF8aMCxG")
        invite_button = discord.ui.Button(label='Invite the bot!', style=discord.ButtonStyle.url, url="https://discord.com/oauth2/authorize?client_id=1371573491391922278&scope=bot+applications.commands&permissions=414464691264")

        self.add_item(server_button)
        self.add_item(invite_button)

# Creates the buttons sent for the tutorial
class CrewUpgradesButton(discord.ui.View):
    def __init__(self, ctx, crew_upgrades_dictionary, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.index = 0
        self.crew_upgrades_dictionary : dict = crew_upgrades_dictionary
        self.num_of_items_per_page = 5

    # Creates the embed for the upgrades
    async def create_embed(self):
        try:
            embed = discord.Embed(title="Crew Upgrades")

            for x in range((self.index * self.num_of_items_per_page), (self.index * self.num_of_items_per_page) + self.num_of_items_per_page):
                embed.add_field(name=self.crew_upgrades_dictionary[x + 1]['name'],
                                value=self.crew_upgrades_dictionary[x + 1]['value'],
                                inline=False)
            
            return embed
       
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno 

            await create_error_embed(ctx=self.ctx, error=e, msg=f"This occured while trying to create the embed for the upgrade crew requirements button on line {line_num}")


    # Controls the back button
    @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
    async def previous_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Cycles through the list of message and sets the new embed to the corresponding page
            self.index = (self.index - 1) % (math.ceil(len(self.crew_upgrades_dictionary.keys()) / self.num_of_items_per_page)) 

            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
       
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=self.ctx, error=e, msg=f"This occured while trying to press the back button on the upgrade crew requirements button on line {line_num}")

    # Controls the next button
    @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
    async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Cycles through the list of message and sets the new embed to the corresponding page
            self.index = (self.index + 1) % (math.ceil(len(self.crew_upgrades_dictionary.keys()) / self.num_of_items_per_page)) 
            

            embed = await self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
     
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=self.ctx, error=e, msg=f"This occured while trying to press the next button on the upgrade crew requirements button on line {line_num}")

import discord
from discord.ext import tasks
import handlers.database_handler as database_handler
import random
import sys
import time
import os
import asyncio
from utils.utility_functions import cooldown_calculator, update_quests, create_error_embed, num_to_words_dict
from utils.buttons import CharacterButton, InventoryButtons
from utils.converters import InventoryConverter
from discord.ext import commands


# Creates a class to handle all commands related to rolling new characters
class User_Collection(commands.Cog):
    # Initalizes the class
    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.warned_cooldown_users = set()
        self.current_legendary_of_the_week = ""
        # Create an if statement to check to see if the current legendary of the week is empty and replaces it

        if not self.send_legendary_of_the_week_embed.is_running():
            self.send_legendary_of_the_week_embed.start()


    # Creates a loop that runs every 12 hours to check whether it's time to update the legendary of the week  
    @tasks.loop(hours=12.0, reconnect=True)
    async def send_legendary_of_the_week_embed(self):
        try:
            # Gets the last legendary of the week from the embed
            amount_of_seconds_in_a_week = 60 * 60 * 24 * 7
            legendary_of_the_week_channel = self.bot.get_channel(1383605542764679268)
            last_message_sent = await legendary_of_the_week_channel.fetch_message(legendary_of_the_week_channel.last_message_id)
            next_message_timestamp = last_message_sent.created_at.timestamp() + amount_of_seconds_in_a_week
            current_time = time.time()
            last_legendary_of_the_week = last_message_sent.embeds[0].footer.text

            # Checks to see if a week has passed yet
            if current_time >= next_message_timestamp:
                possible_legendaries = list(database_handler.all_characters.find({"rarity": "Legendary"}))

                # Makes sure that the LOTW doesn't repeat or use a special character
                for legendary in possible_legendaries:
                    if legendary['name'] == "Jihu Seo" or legendary['name'] == last_legendary_of_the_week:
                        possible_legendaries.remove(legendary)

                # Sets the new legendary of the week
                self.current_legendary_of_the_week = possible_legendaries[random.randint(0, len(possible_legendaries) - 1)]['name']
                legendary_of_the_week = next(iter(database_handler.all_characters.find({"name": self.current_legendary_of_the_week})))
                embed = CharacterButton(characters=legendary_of_the_week).create_embed(character=legendary_of_the_week)
                embed.set_footer(text=self.current_legendary_of_the_week)

                await legendary_of_the_week_channel.send(content="||<@&1382932955051327579>||\nThe next legendary of the week is:",embed=embed)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(error=e, msg=f"This occured while sending the LOTW embed on line {line_num}")

    # Ensures that the bot is ready before running loop
    @send_legendary_of_the_week_embed.before_loop
    async def before_send(self):
        await self.bot.wait_until_ready()

    # Adds the newly rolled character to the player's inventory
    async def add_character_to_inventory(self, rarity, user_id):
        # Chooses a character based off of the rarity
        # TODO Change the footer to match the new character
        if self.current_legendary_of_the_week == "":
            legendary_of_the_week_channel = self.bot.get_channel(1383692657238347806)
            last_message_sent = await legendary_of_the_week_channel.fetch_message(legendary_of_the_week_channel.last_message_id)
            last_legendary_of_the_week = last_message_sent.embeds[0].footer.text

            self.current_legendary_of_the_week = last_legendary_of_the_week

        if rarity == "Legendary":
            rolled_character = database_handler.all_characters.find_one({"name": self.current_legendary_of_the_week})
            rolled_character.pop('threshold_requirements')
        else:
            rolled_character = random.choice(database_handler.all_characters_search('rarity', rarity))
            rolled_character.pop('threshold_requirements')
        user_character = database_handler.user_character_finder(
            user_id=user_id, character_name=rolled_character['name']
        )

        if rarity == "Epic":
            update_quests(user_id=user_id, quest_id="roll_epic_character", amount=1)

        # Checks if the user already owns character
        if user_character is not None:
            # Adds a shard for that character if already owned
            shard = rarity.lower() + "_shard"
            user_inventory = database_handler.users.find_one({"_id": user_id}).get('inventory')
            for user_item in user_inventory:
                if user_item == shard:
                    database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.{shard}.amount", value=1)
                    update_quests(user_id=user_id, quest_id="roll_five_characters", amount=1)
                    return rolled_character, True

            database_handler.add_item(user_id=user_id, item=shard)
            database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.{shard}.amount", value=1)
            update_quests(user_id=user_id, quest_id="roll_five_characters", amount=1)
            return rolled_character, True
        
        else:
            # Adds character to user inventory if unowned
            database_handler.add_array_to_users(
                user_id=user_id, key='characters', array=rolled_character
            )
            update_quests(user_id=user_id, quest_id="roll_five_characters", amount=1)
            return rolled_character, False

    # Manages what happens when the user rolls on the standard banner
    def standard_banner_roll(self, user_id):
        # Creates a new profile for user if they don't already have one
        database_handler.create_new_profile(user_id=user_id)

        # Rolls the rarity of the character
        def choose_rarity():
            rarities = {
                'Epic': 1,
                'Rare': 9,
                'Common': 90,
            }

            randomNum = random.randint(1, sum(rarities.values()))
            counter = 0
            for rarity, weight in rarities.items():
                counter += weight
                if randomNum <= counter:
                    return rarity

        rarity = choose_rarity()

        update_quests(user_id=user_id, quest_id="roll_standard_banner", amount=1)


        return self.add_character_to_inventory(rarity=rarity, user_id=user_id)

    # Manages what happens when the user rolls on the limited time banner
    def limited_time_banner_roll(self, user_id):
        # Creates a new profile for user if they don't already have one
        database_handler.create_new_profile(user_id=user_id)

        # Rolls the rarity of the character
        user_profile = database_handler.users.find_one({'_id': user_id})
        pity = user_profile.get('pity')

            # Determines the rarity of each tier depending on current pity
        if pity > 99:
                rarities = {'Legendary': 100}
                database_handler.users.update_one(
                    filter={'_id': user_id}, update={'$set': {'pity': 0}}
                )
        elif pity > 69:
                rarities = {
                    'Legendary': 5,
                    'Epic': 10,
                    'Rare': 20,
                    'Common': 65,
                }
                database_handler.inc_value_to_users(user_id=user_id, key='pity', value=1)
        else:
                rarities = {
                    'Legendary': 1,
                    'Epic': 4,
                    'Rare': 15,
                    'Common': 80,
                }
                database_handler.inc_value_to_users(user_id=user_id, key='pity', value=1)

        randomNum = random.randint(1, sum(rarities.values()))
        counter = 0
        for rarity, weight in rarities.items():
            counter += weight
            if counter >= randomNum:
                chosen_rarity = rarity
                break


        update_quests(user_id=user_id, quest_id="roll_limited_banner", amount=1)

        return self.add_character_to_inventory(rarity=chosen_rarity, user_id=user_id)

    # Evolves the fighting character based on their rarity and class
    def evolve_fighter_character(self, user_id, character):     
        evolution_dictionary = {
            "Common": {
                "stun_chance": 3,
                "crit_chance": 3,
                "crit_damage": 0.2,
                "dodge_chance": 3,
                "Striker": {
                    "ATK": 1.15,
                    "HP": 1.10,
                    "SPD": 1.05,
                },
                "Grappler": {
                    "ATK": 1.10,
                    "HP": 1.15,
                    "SPD": 1.05,
                },
                "Weaver": {
                    "ATK": 1.05,
                    "HP": 1.10,
                    "SPD": 1.15,
                }
            },
            "Rare": {
                "stun_chance": 5,
                "crit_chance": 5,
                "crit_damage": 0.3,
                "dodge_chance": 5,
                "Striker": {
                    "ATK": 1.20,
                    "HP": 1.15,
                    "SPD": 1.10,
                },
                "Grappler": {
                    "ATK": 1.15,
                    "HP": 1.20,
                    "SPD": 1.10,
                },
                "Weaver": {
                    "ATK": 1.10,
                    "HP": 1.15,
                    "SPD": 1.20,
                }
            },
            "Epic": {
                "stun_chance": 7,
                "crit_chance": 7,
                "crit_damage": 0.4,
                "dodge_chance": 7,
                "Striker": {
                    "ATK": 1.25,
                    "HP": 1.20,
                    "SPD": 1.15,
                },
                "Grappler": {
                    "ATK": 1.20,
                    "HP": 1.25,
                    "SPD": 1.15,
                },
                "Weaver": {
                    "ATK": 1.15,
                    "HP": 1.20,
                    "SPD": 1.25,
                }
            },
            "Legendary": {
                "stun_chance": 10,
                "crit_chance": 10,
                "crit_damage": 0.5,
                "dodge_chance": 10,
                "Striker": {
                    "ATK": 1.30,
                    "HP": 1.25,
                    "SPD": 1.20,
                },
                "Grappler": {
                    "ATK": 1.25,
                    "HP": 1.30,
                    "SPD": 1.20,
                },
                "Weaver": {
                    "ATK": 1.20,
                    "HP": 1.25,
                    "SPD": 1.30,
                }
            },#FINISH EVO
        }
        user_profile = database_handler.users.find_one({"_id": user_id})
        user_characters = user_profile.get('characters')
        user_team = user_profile.get('team')


        for i, user_character in enumerate(user_characters):
            # Goes through the character list and increases the stats of the corresponding character
            if user_character['name'] == character['name']:
                character['ATK'] = round(character['ATK'] * evolution_dictionary[character['rarity']][character['class']]['ATK'])
                character['HP'] = round(character['HP'] * evolution_dictionary[character['rarity']][character['class']]['HP'])
                character['SPD'] = round(character['SPD'] * evolution_dictionary[character['rarity']][character['class']]['SPD'])
            
                if character['class'] == "Striker":
                    character['crit_chance'] = round(character['crit_chance'] + evolution_dictionary[character['rarity']]['crit_chance'], 1)
                    character['crit_damage'] += evolution_dictionary[character['rarity']]['crit_damage']
                
                elif character['class'] == "Weaver":
                    character['dodge_chance'] += evolution_dictionary[character['rarity']]['dodge_chance']
                    
                    if character['threshold'] == 2:
                        character['dodge_duration'] += 1

                elif character['class'] == "Grappler":
                    character['stun_chance'] += evolution_dictionary[character['rarity']]['stun_chance']
                    
                    if character['threshold'] == 2:
                        character['stun_duration'] += 1
            
                character['threshold'] += 1
                database_handler.users.update_one({"_id": user_id}, {"$set": {f"characters.{i}": character}})
                break
        
        # Goes through the team character list and increases the stats of the corresponding character
        for i, user_character in enumerate(user_team):
            if user_character['name'] == character['name']:
                character['current_hp'] = character['HP']
                database_handler.users.update_one({"_id": user_id}, {"$set": {f"team.{i}": character}})
    
    # Evolves the support character based on rarity
    def evolve_support_character(self, user_id, character):
        evolution_dictionary = {
            "Common": {
                "buff": 3,
                "daily": 50
                      },
            "Rare": {
                "buff": 5,
                "daily": 100
                    },
            "Epic": {
                "buff": 8,
                "daily": 150
                    },
            "Legendary": {
                "buff": 10,
                "daily": 200
                    },
        }

        user_profile = database_handler.users.find_one({"_id": user_id})
        user_characters = user_profile.get('characters')
        user_team = user_profile.get('team')

        for i, user_character in enumerate(user_characters):
            # Goes through the character list and increases the effects/change the descriptions for the effects
            if user_character['name'] == character['name']:
                description_string = ""
                for index, effect in enumerate(character.get('effects')):
                    if index == len(character.get('effects')) - 1 and index != 0:
                        description_string += " and "
                        pass

                    effect['amount'] += evolution_dictionary[character['rarity']][effect['type']]

                    if effect['stat'] == "crit_chance" or effect['stat'] == "dodge_chance" or effect['stat'] == "stun_chance":
                        description_string += f"increases the {effect['stat'].replace("_", " ")} of all eligible team members by {effect['amount']}%, "
                    elif effect['type'] == "buff": 
                        description_string += f"increases the {effect['stat'].upper()} of all team members by {effect['amount']}%, "
                    elif effect['type'] == "daily":
                        description_string += f"increases the amount received from the daily command by {effect['amount']}, "

                description_string = description_string[0].upper() + description_string[1:-2] 
                character['description'] = description_string
                character['threshold'] += 1

                database_handler.users.update_one({"_id": user_id}, {"$set": {f"characters.{i}": character}})
                break
        
        # Goes through the character list and increases the effects/change the descriptions for the effects
        for i, user_character in enumerate(user_team):
            if user_character['name'] == character['name']:
                database_handler.users.update_one({"_id": user_id}, {"$set": {f"team.{i}": character}})

    # The roll command
    @commands.command(help="This command allows you to roll on the standard or limited time banner. The format for this command is `?roll <banner name>`")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def roll(self, ctx, *, banner=None):
        # Determines what happens depending on the banner chosen
        user = ctx.author
        user_profile = database_handler.users.find_one({'_id': user.id})
        if user_profile is None:
            database_handler.create_new_profile(user_id=user.id)
            user_profile = database_handler.users.find_one({'_id': user.id})
        pity = None
        thumbnail_url = ''
        banner_name = ''
        banner_icon_url = ''

        if banner is None:
            return await ctx.send(
                "Either 'limited' or 'standard'. Pick one."
            )

        # Runs when the user selects standard banner
        if banner.lower() == 'standard':
            banner_name = 'Standard Banner'
            banner_icon_url = (
                'https://i.pinimg.com/736x/4e/ef/e1/4eefe1689bf53550078ecd3097ea0f56.jpg'
            )

            # Checks to see if the user has enough tickets for the banner
            user_tickets = user_profile.get('inventory').get('standard_ticket')

            if user_tickets is None:
                return await ctx.send("You don't even have enough tickets to roll. Sad. Go buy some tickets first.")
            elif user_tickets["amount"] == 0:
                return await ctx.send("You don't even have enough tickets to roll. Sad. Go buy some tickets first.")
            else:
                database_handler.inc_value_to_users(
                    user_id=user.id, key='inventory.standard_ticket.amount', value=-1
                )
                

            # Gets the character rolled on the banner and checks if it's a duplicate
            character, is_duplicate = self.standard_banner_roll(user.id)

        # Runs when the user selected limited time banner
        elif banner.lower() == 'limited':
            user_profile = database_handler.users.find_one({'_id': user.id})

            banner_name = 'Limited Time Banner'
            banner_icon_url = (
                'https://i.pinimg.com/736x/71/34/67/713467662d8bc26e382a8e3720def168.jpg'
            )

            # Checks to see if the user has enough tickets for the banner
            user_tickets = user_profile.get('inventory').get('limited_ticket')

            if user_tickets is None:
                return await ctx.send("You don't even have enough tickets to roll. Sad. Go buy some tickets first.")
            elif user_tickets["amount"] == 0:
                return await ctx.send("You don't even have enough tickets to roll. Sad. Go buy some tickets first.")
            else:
                database_handler.inc_value_to_users(
                    user_id=user.id, key='inventory.limited_ticket.amount', value=-1
                )
                

            # Gets the character rolled on the banner
            character, is_duplicate = self.limited_time_banner_roll(user_id=user.id)

            # Gets the pity of the user
            user_profile = database_handler.users.find_one({'_id': user.id})
            pity = user_profile.get('pity')

        # Updates the database with profile stats
        def update_user_profile_stats(rarity):
            database_handler.inc_value_to_users(user_id=user.id, key=f'{rarity.lower()}_characters', value=1)
            database_handler.inc_value_to_users(user_id=user.id, key='threshold_one_characters', value=1)

            if rarity.lower() == "legendary":
                database_handler.users.update_one({"_id": user.id}, {"$set": {"pity": 0}})

        # Determines the color of the side bar on the embed based on rarity
        if character['rarity'] == 'Common':
            bar_color = discord.Color.green()
            thumbnail_url = 'https://files.catbox.moe/fen419.png'
            if not is_duplicate:
                update_user_profile_stats(rarity=character["rarity"])

        elif character['rarity'] == 'Rare':
            bar_color = discord.Color.blue()
            thumbnail_url = 'https://files.catbox.moe/5s6egv.png'
            if not is_duplicate:
                update_user_profile_stats(rarity=character["rarity"])

        elif character['rarity'] == 'Epic':
            bar_color = discord.Color.purple()
            thumbnail_url = 'https://files.catbox.moe/xt0w36.png'
            if not is_duplicate:
                update_user_profile_stats(rarity=character["rarity"])

        else:
            thumbnail_url = 'https://files.catbox.moe/8hy2hm.png'
            bar_color = discord.Color.gold()
            database_handler.users.update_one({"_id": user.id}, {"$set": {"pity": 0}})
            if not is_duplicate:
                update_user_profile_stats(rarity=character["rarity"])

        # Creates the embed and sends it
        if character['class'] == 'Support':
            embed = discord.Embed(
                title=f'{character["name"]}',
                description=f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **Effect:** {character["description"]}',
                color=bar_color,
            )
        else:
            embed = discord.Embed(
                title=f'{character["name"]}',
                description=f'> **Rarity:** {character["rarity"]} \n> **Class:** {character["class"]}\n> **ATK:** {character["ATK"]}\n> **HP:** {character["HP"]}\n> **SPD:** {character["SPD"]}',
                color=bar_color,
            )

        # Checks to see if the pity should be displayed
        if pity is not None:
            embed.set_footer(text=f'Pity: {pity}/100 | Rolled by {user} | Current Legendary of the Week: {self.current_legendary_of_the_week}')
        else:
            embed.set_footer(text=f'Rolled by {user}')

        embed.set_thumbnail(url=thumbnail_url)
        embed.set_image(url=character['image_url'])
        embed.set_author(name=banner_name, icon_url=banner_icon_url)

        await ctx.send(embed=embed)

        # Sends an additonal method about gaining a shard if they are a duplicate
        if is_duplicate:
            update_quests(user_id=ctx.author.id, quest_id="obtain_one_character_shard", amount=1)
            await ctx.send(
                f"{character['emoji']} {character['name']} is a duplicate. You have received 1 shard instead."
            )
        
    # Returns the character list for the called function
    async def return_character_list(self, ctx, characters, filter): 
        # Determines the order in which rarities are displayed
        rarity_order = {
            'Common': 4,
            'Rare': 3,
            'Epic': 2,
            'Legendary': 1,
        }

        # Automatically sort characters based on rarity and their name
        user_characters = sorted(
            characters,
            key=lambda character: (
                rarity_order.get(character['rarity'], 999),
                character['name'],
            ),
            reverse=False,
        )

        # Returns only the characters of a particular rarity if an argument is given
        if filter is not None and (
            filter.lower() == 'common'
            or filter.lower() == 'rare'
            or filter.lower() == 'epic'
            or filter.lower() == 'legendary'
        ):
            user_characters = [
                c for c in user_characters if c.get('rarity').lower() == filter.lower()
            ]
        elif filter is not None:
            user_characters = [c for c in user_characters if c['name'].lower() == filter.lower()] 
        elif type(filter) is str:
            return await ctx.send(
                f'{filter} isn\'t an argument.'
            )

        # Returns a statement if no characters meet the criteria
        if user_characters == []:
            return await ctx.send('None of your owned characters meet this criteria.')

        return CharacterButton(characters=user_characters).create_embed(
            user_characters[0]
        ), user_characters

    # Gets the characters owned by the user, allowing them to sort by rarity if they choose so
    @commands.command(name='mycharacters', 
                      aliases=['mychars'],
                      help="This command displays all of your characters. You can sort by a specific character or rarity by typing `?mycharacters epic` or `?mycharacters mary kim`")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def user_character_collection(self, ctx, *, filter=None):
        # Gets the user id and the user characters
        user_id = ctx.author.id
        user_characters = database_handler.users.find_one({'_id': user_id}).get('characters')
        if not user_characters:
            return await ctx.send('Not a character to your name. Pathetic.')

        embed, user_characters = await self.return_character_list(
            ctx=ctx, characters=user_characters, filter=filter
        )

        if embed:
            await ctx.send(
                embed=embed,
                view=CharacterButton(characters=user_characters, ctx=ctx),
            )

    # Gets all the characters, allowing them to sort by rarity if they choose so
    @commands.command(name='allcharacters', 
                      aliases=['allchars'],
                      help="This command displays all characters currently in the bot. You can sort by a specific character or rarity by typing `?allcharacters epic` or `?allcharacters mary kim`")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def all_character_collection(self, ctx, *, filter=None):
        # Gets the user characters
        user_characters = database_handler.all_characters.find({})

        embed, user_characters = await self.return_character_list(
            ctx=ctx, characters=user_characters, filter=filter
        )

        if embed:
            await ctx.send(
                embed=embed,
                view=CharacterButton(characters=user_characters, ctx=ctx),
            )

    # Displays the inventory of the user
    @commands.command(name="inventory", 
                      aliases=["inv"],
                      help = "This command displays all the items in your inventory. You can search for a specific item by typing `?inventory <item name>`.")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def display_inventory(self, ctx, *, searched_item : InventoryConverter = None):
        # Checks to see if the user already has a profile
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        
        inventory = database_handler.users.find_one({"_id": ctx.author.id}).get("inventory")
        view = InventoryButtons(ctx=ctx, items=inventory)
       
       # Checks to see if the user is looking for a specific item
        if searched_item is None:
            embed = await view.create_embed()
        else:
            embed = await view.create_embed(item = searched_item)
 
            
        await ctx.send(view=view, embed=embed)  

    # Allows the user to evolve their character to a new threshold
    @commands.command(name="evolve",
                      help="This command allows you to evolve your character to the next threshold if you meet the requirements. The format for this command is ?evolve <character name>")
    async def evolve_character(self, ctx, *, character=None):
        # Checks to see if an argument was passed
        if character is None:
            return await ctx.send("Enter a character.")
        
        # Checks to see if the user owns the character given
        user_character = database_handler.user_character_finder(user_id=ctx.author.id, character_name=character)

        if user_character is None:
            return await ctx.send("You can't evolve a character you don't have.")
        
        if user_character.get('threshold') >= 4:
            return await ctx.send("You can't surpass more than four thresholds.")

        
        # Gets the threshold requirements and defines user variables
        character_threshold_requirements = database_handler.all_characters.find_one({'name': user_character['name']}, {"threshold_requirements": 1, "_id": 0 })['threshold_requirements'].get(f'threshold_{num_to_words_dict[user_character["threshold"] + 1]}')
        user_profile = database_handler.users.find_one({"_id": ctx.author.id})
        user_inventory = user_profile.get('inventory')
        user_balance = user_profile.get('economy').get('won')

        # Creates an embed to be displayed showing all the met requirements
        embed = discord.Embed(title="-ˋˏ ༻ Threshold Requirements ༺ ˎˊ-")
        threshold_reqs_string = ""

        threshold_level_reqs = {
            1: 50,
            2: 100,
            3: 150
        }

        # Sets variables
        requirements = 0
        met_requirements = 0

        if user_character['class'] != "Support":
            requirements += 1
            # Checks to see if the level requirement is met by non support characters
            if user_character['LVL'] < threshold_level_reqs[user_character['threshold']]:
                threshold_reqs_string += f"> ❥ Level: {threshold_level_reqs[user_character['threshold']]} ❌\n"
            else:
                threshold_reqs_string += f"> ❥ Level: {threshold_level_reqs[user_character['threshold']]} ✅\n"
                met_requirements += 1

        # Checks each requirement for evolution in the character
        for req, value in character_threshold_requirements.items():
            if req == "characters": 
                # Checks to see if the user meets the individual threshold requirements               
                for item in character_threshold_requirements.get('characters'):
                    requirements += 1
                    req_character = database_handler.user_character_finder(user_id=ctx.author.id, character_name=item['name'])

                    if req_character is None:
                        threshold_reqs_string += f"> ❥ {item['threshold']}T {item['name']} ❌\n"
                    elif req_character['threshold'] < item['threshold']:
                        threshold_reqs_string += f"> ❥ {item['threshold']}T {item['name']} ❌\n"
                    else:
                        threshold_reqs_string += f"> ❥ {item['threshold']}T {item['name']} ✅\n"
                        met_requirements += 1

                continue
            
            # Checks to see if the user has enough money
            if req == "won":
                requirements += 1
                if user_balance < value:
                    threshold_reqs_string += f"> ❥ Won: ₩{value} ❌\n"
                else:
                    met_requirements += 1
                    threshold_reqs_string += f"> ❥ Won: ₩{value} ✅\n"

                continue
            
            # Checks to see if the user has enough of an item for evolution
            item_found = False

            for item_name, item_info  in user_inventory.items():
                if item_name == req and item_info['amount'] >= value:  
                    threshold_reqs_string += f"> ❥ {req.replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")}: {value} ✅\n"
                    met_requirements += 1
                    item_found = True

            if not item_found:
                threshold_reqs_string += f"> ❥ {req.replace("_", " ").title().replace("Xp", "XP").replace("Ev", "EV")}: {value} ❌\n"
            
            requirements += 1

        # Sends a list of requirements that still needs to be met if
        # not all the requirements are met
        if met_requirements != requirements:
            embed.add_field(name="",
                            value=threshold_reqs_string)
            
            return await ctx.send(embed=embed)

        # Deducts the items and money from the user if the requirements
        # are met
        for req, value in character_threshold_requirements.items():
            if req == "won":
                user_profile['economy']['won'] -= value
                continue
            
            if req == "characters":
                continue

            for item_name, item_info  in user_inventory.items():
                if item_name == req:  
                    item_info['amount'] -= value

        # Updates the profile stats of the user
        user_profile[f'threshold_{num_to_words_dict[user_character['threshold']]}_characters'] -= 1
        user_profile[f'threshold_{num_to_words_dict[user_character['threshold'] + 1]}_characters'] += 1

        database_handler.users.replace_one({"_id": ctx.author.id}, user_profile)

        # Evolves the character
        if user_character['class'] != "Support":
            self.evolve_fighter_character(user_id=ctx.author.id, character=user_character)
            return await ctx.send(f"{user_character['name']} has been evolved")
        else:
            self.evolve_support_character(user_id=ctx.author.id, character=user_character)
            return await ctx.send(f"{user_character['name']} has been evolved")
        

    @display_inventory.error
    @evolve_character.error
    @all_character_collection.error
    @user_character_collection.error
    @roll.error
    async def error_handler(self, ctx, error):
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
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno
            file_name = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]

            await create_error_embed(ctx=ctx, error=error, msg=f"This occured on line {line_num} in {file_name}")

async def setup(bot):
    await bot.add_cog(User_Collection(bot))




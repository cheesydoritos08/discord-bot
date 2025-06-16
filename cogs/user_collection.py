import discord
import handlers.database_handler as database_handler
import random
import asyncio
from utils.utility_functions import cooldown_calculator, update_quests, create_error_embed
from utils.buttons import CharacterButton, ShardInventoryButton
from utils.converters import InventoryConverter
from discord.ext import commands


# Creates a class to handle all commands related to rolling new characters
class User_Collection(commands.Cog):
    # Initalizes the class
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    def add_character_to_inventory(self, rarity, user_id):
        # Chooses a character based off of the rarity
        rated_up_legendary_character = "Kitae Kim"

        if rarity == "Legendary":
            rolled_character = database_handler.all_characters.find_one({"name": rated_up_legendary_character})
        else:
            rolled_character = random.choice(database_handler.all_characters_search('rarity', rarity))
        
        user_character = database_handler.user_character_finder(
            user_id=user_id, character_name=rolled_character['name']
        )

        if rarity == "Epic":
            update_quests(user_id=user_id, quest_id="roll_epic_character", amount=1)

        # Checks if the user already owns character
        if user_character is not None:
            # Adds a shard for that character if already owned
            database_handler.inc_value_to_users(
                user_id=user_id,
                key=f'inventory.shards.{rolled_character["name"]}',
                value=1,
            )
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
                'Epic': 5,
                'Rare': 15,
                'Common': 80,
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

        def choose_rarity():
            # Determines the rarity of each tier depending on current pity
            if pity > 189:
                rarities = {'Legendary': 100}
                database_handler.users.update_one(
                    filter={'_id': user_id}, update={'$set': {'pity': 0}}
                )
            elif pity > 169:
                rarities = {
                    'Legendary': 10,
                    'Epic': 5,
                    'Rare': 30,
                    'Common': 55,
                }
                database_handler.inc_value_to_users(user_id=user_id, key='pity', value=1)
            else:
                rarities = {
                    'Legendary': 1,
                    'Epic': 99,
                    'Rare': 200,
                    'Common': 700,
                }
                database_handler.inc_value_to_users(user_id=user_id, key='pity', value=1)

            randomNum = random.randint(1, sum(rarities.values()))
            counter = 0
            for rarity, weight in rarities.items():
                counter += weight
                if randomNum <= counter:
                    return rarity

        rarity = choose_rarity()

        update_quests(user_id=user_id, quest_id="roll_limited_banner", amount=1)

        return self.add_character_to_inventory(rarity=rarity, user_id=user_id)

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

        # Determines the color of the side bar on the embed based on rarity
        if character['rarity'] == 'Common':
            bar_color = discord.Color.green()
            thumbnail_url = 'https://files.catbox.moe/fen419.png'
            if not is_duplicate:
                database_handler.inc_value_to_users(
                    user_id=user.id, key='common_characters', value=1
                )
                database_handler.inc_value_to_users(
                    user_id=user.id, key='threshold_one_characters', value=1
                )
        elif character['rarity'] == 'Rare':
            bar_color = discord.Color.blue()
            thumbnail_url = 'https://files.catbox.moe/5s6egv.png'
            if not is_duplicate:
                database_handler.inc_value_to_users(user_id=user.id, key='rare_characters', value=1)
                database_handler.inc_value_to_users(
                    user_id=user.id, key='threshold_one_characters', value=1
                )
        elif character['rarity'] == 'Epic':
            bar_color = discord.Color.purple()
            thumbnail_url = 'https://files.catbox.moe/xt0w36.png'
            if not is_duplicate:
                database_handler.inc_value_to_users(user_id=user.id, key='epic_characters', value=1)
                database_handler.inc_value_to_users(
                    user_id=user.id, key='threshold_one_characters', value=1
                )
        else:
            thumbnail_url = 'https://files.catbox.moe/8hy2hm.png'
            bar_color = discord.Color.gold()
            if not is_duplicate:
                database_handler.inc_value_to_users(
                    user_id=user.id, key='legendary_characters', value=1
                )
                database_handler.inc_value_to_users(
                    user_id=user.id, key='threshold_one_characters', value=1
                )
                database_handler.users.update_one({"_id": user.id}, {"$set": {"pity": 0}})
                pity = 0

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

        if pity is not None:
            embed.set_footer(text=f'Pity: {pity}/190 | Rolled by {user}')
        else:
            embed.set_footer(text=f'Rolled by {user}')

        embed.set_thumbnail(url=thumbnail_url)
        embed.set_image(url=character['image_url'])
        embed.set_author(name=banner_name, icon_url=banner_icon_url)

        await ctx.send(embed=embed)
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
        print(filter)
        user_characters = database_handler.all_characters.find({})

        embed, user_characters = await self.return_character_list(
            ctx=ctx, characters=user_characters, filter=filter
        )

        if embed:
            await ctx.send(
                embed=embed,
                view=CharacterButton(characters=user_characters, ctx=ctx),
            )

    # Displays all the shards the user currently owns
    @commands.command(name='shards',
                      help = "This command displays all the shards you currently own. You can also check the shards of any other user by doing `?shards <user>`")
    @commands.cooldown(rate=1, per=50, type=commands.BucketType.user)
    async def shard_inventory(self, ctx, member: discord.Member = None):
         # Checks to make sure the target has a profile and isn't a bot
        if member is None and not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        elif member is None:
            user = ctx.author
        elif not await database_handler.check_existing_profile(ctx=ctx, user_id=member.id, another_user=True):
            return
        elif member and not member.bot:
            user = member

        # Gets the shards and displays the characters that have more than one shard
        shards = database_handler.users.find_one({'_id': user.id}).get('inventory').get('shards')
        shards = {k: v for k, v in shards.items() if v != 0}
        total_shards = sum(list(shards.values()))

        if total_shards == 0:
            return await ctx.send("You don't have any shards.")
        
        view = ShardInventoryButton(shards=shards, total_shards=total_shards, ctx=ctx)

        embed =  view.create_embed(shards=dict(list(shards.items())[0:5]))

        await ctx.send(
            view=view,
            embed=embed,
        )

    # Displays the inventory of the user
    @commands.command(name="inventory", 
                      aliases=["inv"],
                      help = "This command displays all the items in your inventory. You can search for a specific item by typing `?inventory <item name>`.")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def display_inventory(self, ctx, *, arg : InventoryConverter = None):
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        inventory = database_handler.users.find_one({"_id": ctx.author.id}).get("inventory")
        embed = None
        inventory_display_string = ""

       
        if arg is None:
            embed = discord.Embed(title=f"{ctx.author}'s Inventory",
                      description="∘₊✧─── ──── ──── ───✧₊∘",
                      colour=0xcb7667)

            for item in inventory:
                if item != "shards" and inventory.get(item, {}).get("amount"):
                    item_name = item.replace("_", " ").title().replace("Xp", "XP")
                    inventory_display_string += f"**{inventory[item]['emoji']} {item_name}**: {inventory[item]['amount']}\n"

            if inventory_display_string == "":
                return await ctx.send("You have nothing in your inventory.")

            embed.add_field(name="",
                value=inventory_display_string,
                inline=False)

            embed.set_thumbnail(url=ctx.author.display_avatar)

            embed.set_footer(text="∘₊✧──── ───── ───── ────✧₊∘")

        else:
            item = arg

            embed = discord.Embed(title=f"{ctx.author}'s Inventory",
                      description="∘₊✧─── ──── ──── ───✧₊∘",
                      colour=0xcb7667)
            
            if inventory.get(item) is None:
                return await ctx.send("Search for a valid item.")
            elif item != "shards" and inventory[item]["amount"]:
                item_name = item.replace("_", " ").title().replace("Xp", "XP")
                inventory_display_string += f"**{item_name}**: {inventory[item]['amount']}\n"
            else:
                return await ctx.send("You do not have this item.")

            
            embed.add_field(name="",
                value=inventory_display_string,
                inline=False)

            embed.set_thumbnail(url=ctx.author.display_avatar)

            embed.set_footer(text="∘₊✧──── ───── ───── ────✧₊∘")
            
        await ctx.send(embed=embed)   

    @display_inventory.error
    @shard_inventory.error
    @all_character_collection.error
    @user_character_collection.error
    @roll.error
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
    await bot.add_cog(User_Collection(bot))

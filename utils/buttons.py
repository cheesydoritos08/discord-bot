import discord
import math
import handlers.database_handler as database_handler

# Buttons for the shop command
class ShopButtons(discord.ui.View):
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
        embed = discord.Embed(title="•─•°• Shop •°•─•")

        for item in self.items[int(self.index * 3):int(((self.index * 3) + 3))]:
            embed.add_field(name=f"°˖✧ {item["emoji"]} {item["name"].replace("_", " ").title().replace("Xp", "XP")} ✧˖°",
                value=f"`Buy Price:` ¥{item["buy_price"]}\n`Sell Price:` ¥{item["sell_price"]}",
                inline=True)

        embed.set_footer(text="•─•°• To buy or sell an item, type ?buy/sell <item name> <amount> •°•─•")

        return embed

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red)
    async def back_button(self, interaction, button):
        self.index = (self.index - 1) % (len(self.items) / 3)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.red)
    async def next_button(self, interaction, button):
        self.index = (self.index + 1) % (len(self.items) / 3)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

 # Buttons for the my characters command

# Buttons for the mychars commands
class CharacterButton(discord.ui.View):
        def __init__(self, characters, ctx=None):
            super().__init__()
            self.index = 0
            self.characters = characters
            self.ctx = ctx

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.ctx.author:
                await interaction.response.send_message(
                    'Only the author of the command can perform this action.',
                    ephemeral=True,
                )
                return False
            return True

        # Returns the decorative items needed to indicate rarity
        def set_rarity_indicators(self, character):
            colors = {
                'Common': (
                    discord.Color.green(),
                    'https://files.catbox.moe/fen419.png',
                ),
                'Rare': (discord.Color.blue(), 'https://files.catbox.moe/5s6egv.png'),
                'Epic': (discord.Color.purple(), 'https://files.catbox.moe/xt0w36.png'),
                'Legendary': (
                    discord.Color.gold(),
                    'https://files.catbox.moe/8hy2hm.png',
                ),
            }
            return colors.get(character['rarity'], (discord.Color.default(), None))

        # Creates the embed for the pages
        def create_embed(self, character):
            bar_color, rarity_icon = self.set_rarity_indicators(character)
            if character['class'] == 'Support':
                desc = f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **Effect:** {character["description"]}'
            else:
                special_effect = ""
                special_effect_description = ""
                if character.get('stun_chance'):
                    special_effect = "Stuns"
                    special_effect_description = f"Gives the character a {character['stun_chance']}% chance to stun the opposing team for {character['stun_duration']} turns"
                elif character.get('crit_chance'):
                    special_effect = "Critical Hits"
                    special_effect_description = f"Gives the character a {character['crit_chance']}% chance to do {character['crit_damage']} times their normal damage"
                elif character.get('reflect_chance'):
                    special_effect = "Reflection"
                    special_effect_description = f"Gives the character a {character['reflect_chance']}% to reflect {character['reflect_percent']}% chance of the damage dealt to them back to their attacker"


                desc = f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **ATK:** {character["ATK"]}\n> **HP:** {character["HP"]}\n> **SPD:** {character["SPD"]}\n> **LVL:** {character["LVL"]}\n> **Special Effect**: {special_effect}\n> **Special Effect Description**: {special_effect_description}\n> **XP:** {character["XP"]}/2000'

            embed = discord.Embed(title=character['name'], description=desc, color=bar_color)
            embed.set_image(url=character['image_url'])
            embed.set_footer(text=f'Page {self.index + 1}/{len(self.characters)}')
            if rarity_icon:
                embed.set_thumbnail(url=rarity_icon)
            return embed

        # Controls the back button
        @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
        async def previous_message(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            # Cycles through the list of chracters and sets the new embed to the corresponding page
            self.index = (self.index - 1) % len(self.characters)
            embed = self.create_embed(self.characters[self.index])
            await interaction.response.edit_message(embed=embed, view=self)

        # Controls the next button
        @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
        async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.index = (self.index + 1) % len(self.characters)
            embed = self.create_embed(self.characters[self.index])
            await interaction.response.edit_message(embed=embed, view=self)

# Buttons for the shard inventory command
class ShardInventoryButton(discord.ui.View):
        def __init__(self, shards, total_shards, ctx=None):
            super().__init__()
            self.index = 0
            self.shards = shards
            self.ctx = ctx
            self.total_shards = total_shards

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.ctx.author:
                await interaction.response.send_message(
                    'Only the author of the command can perform this action.',
                    ephemeral=True,
                )
                return False
            return True

        # Creates the embed for the pages
        def create_embed(self, shards):
            embed = discord.Embed(
                description='This is where all of your shards are stored! In the future,\nyou can use shards to upgrade your characters to new \nthresholds!',
                color=discord.Color.dark_orange(),
            )

            for k, v in shards.items():
                char = database_handler.all_characters.find_one({'name': k})
                rarity = char.get('rarity')
                embed.add_field(name='', value=f'**{char["emoji"]} {k}** ({rarity}): {v} ', inline=False)

            embed.set_author(
                name=f"{self.ctx.author}'s Shard Inventory",
                url='https://i.pinimg.com/736x/02/5d/fb/025dfb85f3c8e4e05a99624c9ad666d8.jpg',
            )
            embed.set_footer(
                text=f'Page {self.index + 1}/{math.ceil(len(self.shards) / 5)} | Total Shards: {self.total_shards}'
            )
            embed.set_thumbnail(url=f'{self.ctx.author.display_avatar}')
            return embed

        # Controls the back button
        @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
        async def previous_message(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            # Cycles through the list of chracters and sets the new embed to the corresponding page
            self.index = (self.index - 1) % (math.ceil(len(self.shards) / 5))
            shards_on_current_page = dict(
                list(self.shards.items())[self.index * 5 : ((self.index * 5) + 5)]
            )
            embed = self.create_embed(shards=shards_on_current_page)
            await interaction.response.edit_message(embed=embed, view=self)

        # Controls the next button
        @discord.ui.button(label='Next', style=discord.ButtonStyle.red)
        async def next_message(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.index = (self.index + 1) % (math.ceil(len(self.shards) / 5))
            shards_on_current_page = dict(
                list(self.shards.items())[self.index * 5 : ((self.index * 5) + 5)]
            )
            embed = self.create_embed(shards=shards_on_current_page)
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
            "Welcome to the Lookism Bot! This tutorial goes the core mechanics of the bot so feel free to revisit it as much as you want! If you ever want to find out more about a command, use the ?help command. (Pictures are unrelated to the tutorial, they just look cool. All credits go to the original creators.)",
            "Setting up the bot is really easy! If you're not an adminstrator, you can skip the next two pages. If you're an administrator, you can type ?addprefix [prefix] to add a prefix to the server. The square brackets are required for the command to work and the characters typed inside of them are case sensitive so be careful! If you want a space between your prefix and the commands, make sure to include it in the brackets as well.",
            "To view the list of prefixes you currently have set, type ?viewprefixes. Adding a prefix to the bot will not remove other prefixes so make sure to remove any unwanted prefixes!",
            "To remove a prefix, type ?removeprefix [prefix]. Once again, the command is case sensitive so make sure to type the prefix exactly as it's show in the viewprefixes command!",
            "Finally, you can get to the fun part, gambling! To gamble for characters, you need to buy some tickets. You already have some money in your wallet so use the ?shop command to buy some standard or limited banner tickets. To buy an item, type ?buy <item name> <amount>. You can also sell items in the shop if you type ?sell <item name> <amount>. (The <>s are not included in the command.)",
            "After you buy some tickets, roll on either banner to get characters. To roll on the limited banner, type ?roll limited and to roll on the standard banner, type ?roll standard. You can only roll one character at a time.",
            "Rolling on the limited time banner grants you the chance to roll the legendary character for the week. The legendary character on the banner rotates from week to week and you can check the current legendary by visiting the bot's support server!",
            "When you roll duplicates, you get shards which will be stored in your shard inventory. To see your shard inventory, type ?shards. Though these don\'t do anything now, in the near future they will be very important in unlocking character thresholds so make sure to save up a lot of them because you're going to need them!",
            "After rolling your characters, you can add them to your team with ?addteammember <character full name> (<>s not included). Each team consists of three fighters and one support! Your team can then be used to challenge other players or to fight in raids.",
            "To challenge a player, type ?challenge <@user> (<>s not included). Challenging other players grants you money and xp which helps you level up your characters!",
            "Besides granting you yen and xp, challenging players also increases your ELO score on every win! By increasing your ELO score, you can unlock new ranks which given you *permanent* money boosts to your account. To check your ELO score and rank, you can use the ?profile command!",
            "There's a global leaderboard that displays the current all time highest ELOs across the entire bot database! If you're strong enough, you could end up on there!",
            "If you don't have any friends to challenge, you can run the raid command by typing ?raid! Going on raids grants you xp and items that can be used on yourself or on your team members! Raid levels are also replayable so once you beat a level, you can always go back and start from it by typing ?raid <level> (<>s not included).",
            'Besides challenging players to fights, you can earn money through completeling daily quests with the ?quests command, claiming your daily reward with the ?daily command, voting for bot on Top.gg with the ?vote command, gambling your money with the ?coinflip command and playing higher or lower with the ?highlow command!',
            "You can also trade with other players! As of right now, you can only trade money and shards but in the near future, items will be included as well! To find out more about trading, type ?help trade!",
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
class FighterButton(discord.ui.Button):
    def __init__(self, label, character, game):
        super().__init__(label=label, style=discord.ButtonStyle.red)
        self.character = character
        self.game = game

    async def on_button_click(self, interaction: discord.Interaction):        
        current_team = None
        game_over = False

        # Sends the info from the button press to the game to determine the logic
        if interaction.user == self.game.player_one:
            current_team = self.game.player_two_team
            self.game.player_one_character = self.character
            self.game.turn = self.game.player_two
        else:
            current_team = self.game.player_one_team
            self.game.player_two_character = self.character
            self.game.turn = self.game.player_one
            self.game.determine_final_damage()
        
        # Creates an embed displaying the current fight
        embed = self.game.create_embed()
        view = self.game.create_character_buttons(
                team=current_team
            )
        
        if await self.game.check_player_win(self.game.player_one_team):
            game_over = True
            self.game.send_timeout_message = False
        if await self.game.check_player_win(self.game.player_two_team):
            game_over = True
            self.game.send_timeout_message = False

        if not game_over:
                # Sends a message to indicate who can go next
                await interaction.response.send_message(
                    content=f"It is {self.game.turn.mention}'s turn to choose a character!",
                    embed=embed,
                    view=view,
                )
                self.game.combat_log = ["Awaiting player actions..."]

class InviteButton(discord.ui.View):
    def __init__(self, *, timeout = 10):
        super().__init__(timeout=timeout)
        server_button = discord.ui.Button(label="Join the bot's official server!", style=discord.ButtonStyle.url, url="https://discord.gg/EaaF8aMCxG")
        invite_button = discord.ui.Button(label='Invite the bot!', style=discord.ButtonStyle.url, url="https://discord.com/oauth2/authorize?client_id=1371573491391922278&scope=bot+applications.commands&permissions=414464691264")

        self.add_item(server_button)
        self.add_item(invite_button)
    

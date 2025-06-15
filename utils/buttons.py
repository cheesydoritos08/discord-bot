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
                desc = f'> **Rarity:** {character["rarity"]}\n> **Class:** {character["class"]}\n> **ATK:** {character["ATK"]}\n> **HP:** {character["HP"]}\n> **SPD:** {character["SPD"]}\n> **LVL:** {character["LVL"]}\n> **XP:** {character["XP"]}/2000'

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
            'Collecting New Characters',
            'Rolling on the Standard Banner vs the Limited Time Banner',
            'Creating a Team and Fighting',
            'Using Items',
            'Gaining More Money',
            'Rolling Duplicates',
            'End of the Tutorial'
        ]
        self.descriptions = [
            "Welcome to the Lookism Bot! This tutorial goes over only the bare basics of the bot! If you ever want to find out more about a command, use the ?help command. (Pictures are unrelated to the tutorial, they just look cool)",
            "To start off, you need characters! You already have some money in your wallet so use the ?shop command to buy some  standard or limited banner tickets.",
            "After that, roll on either banner to get characters. Rolling on the limited time banner grants you the chance to roll the legendary character for the week. The legendary character on the banner rotates from week to week and you can check the current legendary by checking the bot's support server.",
            'After rolling your characters, you can add them to your team with the ?addteammember command. Your team can then be used to challenge other players or to fight in raids. Challenging other players grants you money while completing raids grants you items.',
            'You can use items such as yen boosters to increase the amount of money you get for a certain period of time',
            'You can also use commands like ?coinflip and ?highlow to gain more money.',
            'When you roll duplicates, you get shards which will be stored in your shard inventory. Though these don\'t do anything now, in the near future they will be very important in unlocking character thresholds so save up some!',
            'That\'s it for the tutorial! If you have any question, join the official bot server!'
                  ]
        self.image_urls = [
            'https://i.pinimg.com/736x/80/e0/ac/80e0ace80f573d27333a042e6e51d211.jpg',
            'https://i.pinimg.com/736x/36/3b/14/363b140a2c18951cb7098b4ca3029a29.jpg',
            'https://i.pinimg.com/736x/a6/3b/70/a63b70b5844d615c15dafa00a4e6e5fc.jpg',
            'https://i.pinimg.com/736x/e4/19/22/e41922b040e2497540338354d2abf642.jpg',
            'https://i.pinimg.com/736x/c7/24/b1/c724b17aeef7f4425d84e42b7e25edf7.jpg',
            'https://i.pinimg.com/736x/62/fa/cd/62facd814343f993ecf7d06410ea9dcd.jpg',
            'https://i.pinimg.com/736x/a6/3b/70/a63b70b5844d615c15dafa00a4e6e5fc.jpg',
            'https://i.pinimg.com/736x/c6/b0/0f/c6b00f5812531a034034982c406558e7.jpg'

        ]

    def add_invite_button(self):
        if self.index == 2 or self.index == 7:
            self.add_item(self.button)


    # Controls the back button
    @discord.ui.button(label='Back', style=discord.ButtonStyle.red)
    async def previous_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cycles through the list of message and sets the new embed to the corresponding page
        self.index -= 1
        self.remove_item(self.button)
        self.add_invite_button()

        if self.index < 0:
            self.index = len(self.titles) - 1
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
        self.index += 1
        self.remove_item(self.button)
        self.add_invite_button()

        if self.index >= len(self.titles):
            self.index = 0
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
    

import discord
from discord.ext import commands
import asyncio
from utils.utility_functions import cooldown_calculator, create_error_embed
import handlers.database_handler as database_handler
import handlers.fight_handler as fight_handler
import handlers.raid_handler as raid_handler


class Fighting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(help="This command allows you to challenge another user to a fight! The format for this command is `?challenge <user>`")
    async def challenge(self, ctx, other_player: discord.Member):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        # Checks to see if the user challenged has a profile or not
        if not await database_handler.check_existing_profile(
            ctx=ctx, user_id=other_player.id, another_user=True
        ):
            return

        # Prevents the user from challenging bots and themselves
        if other_player.bot:
            return await ctx.send("Are you that bad that you have to challenge a bot?")
        if other_player == ctx.author:
            return await ctx.send("Don't you have any friends? Go challenge them instead.")

        # Prevents the user from entering another challenge if they are already in one
        if database_handler.users.find_one({'_id': ctx.author.id}).get('in_challenge'):
            return await ctx.send('Finish your fight first.')
        elif database_handler.users.find_one({'_id': other_player.id}).get('in_challenge'):
            return await ctx.send('Let them finish their fight first. No 2v1s.')

        player_one_team = database_handler.users.find_one({'_id': ctx.author.id}).get('team', [])
        player_two_team = database_handler.users.find_one({'_id': other_player.id}).get('team', [])

        if not player_one_team or not player_two_team:
            return await ctx.send("One of you doesn't have a team set up.")

        database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_challenge': True}})
        database_handler.users.update_one({'_id': other_player.id}, {'$set': {'in_challenge': True}})

        await ctx.send(f'{other_player.mention}, type `accept` or `decline` to respond to the challenge.')


        # Makes sure only the one propositioned can respond to a challenge
        def check(m):
            return m.author == other_player and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=15.0, check=check)
            # Determines what happens when the other player accepts/declines
            if msg.content.lower() == 'accept':
                game = fight_handler.GameInstance(ctx, ctx.author, other_player, player_one_team, player_two_team)
                embed = game.create_embed()
                view = game.create_character_buttons(
                    player_one_team
                )

                game.view = view

                await ctx.send(
                    embed=embed,
                    view=view,
                    content=f"It is {ctx.author.mention}'s turn to choose a character.",
                )
            elif msg.content.lower() == 'decline':
                database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_challenge': False}})
                database_handler.users.update_one({'_id': other_player.id}, {'$set': {'in_challenge': False}})
                await ctx.send(f'{other_player.mention} declined the challenge.')

            else:
                database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_challenge': False}})
                database_handler.users.update_one({'_id': other_player.id}, {'$set': {'in_challenge': False}})
                await ctx.send('Wrong response.')

        except asyncio.TimeoutError:
            database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_challenge': False}})
            database_handler.users.update_one({'_id': other_player.id}, {'$set': {'in_challenge': False}})
            await ctx.send('I have better things to do than sit and wait for you.')
        except Exception as e:
            create_error_embed(error=e, ctx=ctx, msg="This occurred when a user tried to send a message accepting/declining a challenge.")
    
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(help="This command allows you to start a raid. The format for this command is `?raid <level> (Optional)`. If you decide to put in a level, it will start you off at that level as long as you've already completed it once. Else, the command will start you off at your current level.")
    async def raid(self, ctx, level : int = None):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        
        user_profile = database_handler.users.find_one({"_id": ctx.author.id})
        user_inventory = user_profile["inventory"]

        # Checks to see if the user has token
        if user_inventory.get("raid_token") is None:
            return await ctx.send("Go buy some token first.")
        elif user_inventory["raid_token"]["amount"] == 0:
            return await ctx.send("Go buy some token first.")
        
        # Checks to see if user is already in a raid
        if user_profile.get("in_raid"):
            return await ctx.send("Finish your raid first.")
        
        # 
        if level is None:
            level = user_profile["raid_level"]
        elif user_profile["raid_level"] < level:
            return await ctx.send("You're too weak for that level.")
        
        user_team = user_profile.get("team")
        fighter_characters = [char for char in user_team if char["class"] != "Support"]

        # Starts the raid if user has a team
        if fighter_characters != []:
            database_handler.inc_value_to_users(user_id=ctx.author.id, key="inventory.raid_token.amount", value=-1)

            raid = raid_handler.RaidInstance(level=level, team = user_team, ctx = ctx, bot = self.bot)
            embed = raid.create_embed()
            view = raid.create_character_buttons(team=user_team)
           # database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_raid': True}})
            await ctx.send(embed=embed, view = view)
        else:
            return await ctx.send("You need a team to run this command.")

    # Adds a character to a team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='addteammember', 
                      aliases=['addtm'],
                      help="This command allows you to add a team member to your team. A team consists of three fighter characters and one support character. The format for this command is `?addteammember <character name>`")
    async def add_to_team(self, ctx, *, character_name):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        # Gets the current team and the character that is to be added to the team as well as creating some checker variables
        user_team = database_handler.users.find_one({'_id': ctx.author.id}).get('team')
        character = database_handler.user_character_finder(
            user_id=ctx.author.id, character_name=character_name
        )
        support_members = 0
        fighting_members = 0
        fighting_effects = 0

        # Adds the character to the team
        async def add_character():
            if character['class'] != 'Support':
                character['current_hp'] = character['HP']
            database_handler.add_array_to_users(user_id=ctx.author.id, key='team', array=character)
            await ctx.send(f'You have added {character["name"]} to your team.')

        if character:
            # Counts how many support and fighter characters are currently in the team
            for member in user_team:
                if member['class'] == 'Support':
                    support_members += 1
                else:
                    fighting_members += 1

                # Checks to see if a character is already in the team
                if member == character:
                    return await ctx.send('You can\'t add the same character twice genius.')

            # Determines whether to add a character to the team based off of certain criteria
            if character['class'] == 'Support' and support_members == 1:
                return await ctx.send('You already have a support character. Too weak for just one?')
            elif fighting_members == 3 and character['class'] != 'Support':
                return await ctx.send('You already have three fighter characters. You don\'t need a whole army.')
            elif character['class'] == 'Support':
                # Checks to see if the support character has any combat effects
                for effect in character['effects']:
                    if effect['type'] != 'daily':
                        fighting_effects += 1
                if fighting_effects < 1:
                    return await ctx.send('Supports with no fighting buffs can\'t be used in a fight. Not like that changes much for you.')

                # Adds character to team if they pass the check
                await add_character()
            else:
                # Adds character to team if they pass the check
                await add_character()
        else:
            await ctx.send(f'You do not own {character_name.title()}!')

    # Removes a character from the team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='removeteammember', 
                      aliases=['removetm'],
                      help="This command allows you to remove a character from your team. The format for this command is `?removeteammember <character name>`")
    async def remove_from_team(self, ctx, *, character_name):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        # Gets the user team from the user database
        user_team = database_handler.users.find_one({'_id': ctx.author.id}).get('team')
        removed_member = None

        # Checks to see if the character mentioned matches any character in the current team
        for member in user_team:
            # If they match, removes the team member and updates the members according
            if character_name.lower() == member['name'].lower():
                removed_member = member
                user_team.remove(member)
                database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'team': user_team}})

        # Sends a message to the user indicating the removal of the character
        if removed_member:
            await ctx.send(f'{removed_member["name"]} has been removed.')
        else:
            await ctx.send(f'{character_name.title()} is not on your team.')

    # Displays the user's current team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='viewteam', 
                      aliases=['team'],
                      help="This command allows you to view all of the current members on your team. Your team can be used to challenge other players or to fight in raids.")
    async def view_team(self, ctx, *, member: discord.Member = None):
        # Checks to make sure the target has a profile and isn't a bot
        if member is None and not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return
        elif member is None:
            user = ctx.author
        elif not await database_handler.check_existing_profile(ctx=ctx, user_id=member.id, another_user=True):
            return
        elif member and not member.bot:
            user = member

        # Separates the fighting and support characters in the team
        user_team = database_handler.users.find_one({'_id': user.id}).get('team')
        support_characters = []
        fighting_characters = []

        for member in user_team:
            if member['class'] == 'Support':
                character_string = f"{member['emoji']} {member['name']}"
                support_characters.append(character_string)
            else:
                character_string = f"{member['emoji']} {member['name']} ({member['class']})"
                fighting_characters.append(character_string)

        # Creates the embed to display the current team
        embed = discord.Embed(color=discord.Color.dark_teal())

        embed.set_author(
            name=f"{user}'s Team",
            icon_url='https://i.pinimg.com/736x/08/db/e7/08dbe77381a2fd043327703bf4954471.jpg',
        )

        embed.set_thumbnail(url=user.display_avatar)

        embed.add_field(
            name='**Fighting Characters**',
            value='\n'.join(fighting_characters),
            inline=False,
        )

        embed.add_field(
            name='**Support Character**',
            value='\n'.join(support_characters),
            inline=True,
        )

        embed.set_footer(text='Use ?addtm or ?removetm to edit your team members!')

        await ctx.send(embed=embed)

    @view_team.error
    @remove_from_team.error
    @add_to_team.error
    @challenge.error
    @raid.error
    async def error_handler(self, ctx, error):
        # Sends a cooldown message if command is reused when on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            user_id = ctx.author.id
            cooldown_string = cooldown_calculator(round(error.retry_after))

            if user_id not in self.warned_cooldown_users:
                self.warned_cooldown_users.add(user_id)
                await ctx.send(f'Can\'t you be patient and wait for {cooldown_string}?')
            
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
    await bot.add_cog(Fighting(bot))

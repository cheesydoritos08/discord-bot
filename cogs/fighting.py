import discord
from discord.ext import commands
import asyncio
import os
import sys
from utils.utility_functions import cooldown_calculator, create_error_embed
import handlers.database_handler as database_handler
import handlers.fighting_handler as fighting_handler
import handlers.boss_raid_handler as boss_raid_handler


class Fighting(commands.Cog):
    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(help="This command allows you to challenge another user to a fight! The format for this command is `?challenge <user>`")
    async def challenge(self, ctx, other_player: discord.Member):
        try:
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

            team_one_fighter_characters = [char for char in player_one_team if char["class"] != "Support"]
            team_two_fighter_characters = [char for char in player_two_team if char["class"] != "Support"]


            if team_one_fighter_characters == [] or team_two_fighter_characters == []:
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
                    game = fighting_handler.ChallengeInstance(ctx=ctx, bot=self.bot, player_one=ctx.author, player_two=other_player, player_one_team=player_one_team, player_two_team=player_two_team)
                    
                    embed = game.create_embed()
                    view = game.create_character_buttons(player_one_team)

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
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was trying to challenge another user on line {line_num}")    
    
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(help="This command allows you to start a raid. The format for this command is `?raid <level> (Optional)`. If you decide to put in a level, it will start you off at that level as long as you've already completed it once. Else, the command will start you off at your current level.")
    async def raid(self, ctx, level : int = None):
        try:
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

                raid = fighting_handler.RaidInstance(level=level, team = user_team, ctx = ctx, bot = self.bot)
                embed = raid.create_embed()
                view = raid.create_character_buttons(team=user_team)
                database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'in_raid': True}})
                await ctx.send(embed=embed, view = view)
            else:
                return await ctx.send("You need a team to run this command.")
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was starting a raid on line {line_num}")

  # @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
  #  @commands.command(name="bossraid",
#                   help="This command allows you to start a raid. The format for this command is `?raid <level> (Optional)`. If you decide to put in a level, it will start you off at that level as long as you've already completed it once. Else, the command will start you off at your current level.")
    async def boss_raid(self, ctx, player_two : discord.Member, player_three : discord.Member):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            # Checks to see if the player two has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=player_two.id, another_user=True):
                return
            
            # Checks to see if the player three has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=player_three.id, another_user=True):
                return
            
            # Checks to see if the user is in a boss raid already
            if database_handler.users.find_one({"_id": ctx.author.id}).get('in_boss_raid'):
                return await ctx.send("You are already in a boss raid. Finish that first.")
            
            # Checks to see if playter two is in a boss raid already
            if database_handler.users.find_one({"_id": player_two.id}).get('in_boss_raid'):
                return await ctx.send(f"{player_two} is already in a boss raid. Let them finish that first.")
            
            # Checks to see if playter three is in a boss raid already
            if database_handler.users.find_one({"_id": player_three.id}).get('in_boss_raid'):
                return await ctx.send(f"{player_three} is already in a boss raid. Let them finish that first.")
            
            # Gets the character the player will use in the raid
            async def get_character(player : discord.Member):
                await ctx.send(f"{player.mention}, type the full name of the character you would like to use. Supports can't be used in boss raids.")

                def check(m):
                    return m.channel == ctx.channel and m.author == player
                
                msg = await self.bot.wait_for('message', check=check, timeout=20.0)
    
                character = database_handler.user_character_finder(user_id = player.id, character_name = msg.content.title())

                if character is None:
                    await ctx.send("Invalid character. Try again later.")
                    return None
                
                elif character['class'] == "Support":
                    await ctx.send("Supports can't be used in raids.")
                    return None
                
                return character
        
            def set_in_boss_raid_to_true():
                database_handler.users.update_one({"_id": ctx.author.id}, {"$set": {"in_boss_raid": True}})
                database_handler.users.update_one({"_id": player_two.id},  {"$set": {"in_boss_raid": True}})
                database_handler.users.update_one({"_id": player_three.id},  {"$set": {"in_boss_raid": True}})

            # Holds the characters player will use in the raid and makes sure its actually given
            player_one_character = await get_character(player = ctx.author)

            if player_one_character is None:
                return
            
            player_one_character['current_hp'] = player_one_character['HP']

            player_two_character = await get_character(player = player_two)

            if player_two_character is None:
                return

            player_two_character['current_hp'] = player_two_character['HP']

            player_three_character = await get_character(player = player_three)

            if player_three_character is None:
                return
            
            player_three_character['current_hp'] = player_three_character['HP']


            # Checks to see what boss they will be raiding against
            await ctx.send(f"{ctx.author.mention}, please enter the full name of the boss you would like to fight. (Gun Park, Goo Kim, Kitae Kim)")

            def check(m):
                return m.channel == ctx.channel and m.author == ctx.author
                
            msg = await self.bot.wait_for('message', check=check, timeout=20.0)

            # Checks to make sure the name entered is an eligible boss
            boss_character = database_handler.all_characters_search(key = 'name', query = msg.content.title())[0]
            if boss_character == []:
                return await ctx.send("Not a valid boss")
            
            elif boss_character['name'] == "Gun Park" or boss_character['name'] == "Goo Kim" or boss_character['name'] == "Kitae Kim":
                #set_in_boss_raid_to_true()
                boss_raid = boss_raid_handler.BossRaidInstance(ctx = ctx, boss_character = boss_character, player_one = ctx.author, player_two = player_two, player_three = player_three, player_one_character = player_one_character, player_two_character = player_two_character, player_three_character = player_three_character)
                return await ctx.send(embed=boss_raid.create_embed())
            else:
                return await ctx.send("Not a valid boss.")


        except asyncio.TimeoutError as e:
            return await ctx.send("You took too long to respond.")
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was starting a boss raid on line {line_num}")
       
    # Adds a character to a team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='addteammember', 
                      aliases=['addtm'],
                      help="This command allows you to add a team member to your team. A team consists of three fighter characters and one support character. The format for this command is `?addteammember <character name>`")
    async def add_to_team(self, ctx, *, character_name):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return

            # Gets the current team and the character that is to be added to the team as well as creating some checker variables
            user_team = database_handler.users.find_one({'_id': ctx.author.id}).get('team')
            character = database_handler.user_character_finder(
                user_id=ctx.author.id, character_name=character_name.title()
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
                    if member['name'] == character['name']:

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
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was trying to add a character to their team on line {line_num}")
    
    # Removes a character from the team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='removeteammember', 
                      aliases=['removetm'],
                      help="This command allows you to remove a character from your team. The format for this command is `?removeteammember <character name>`")
    async def remove_from_team(self, ctx, *, character_name):
        try:
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
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was trying to remove a character from their team on line {line_num}")
    
    # Displays the user's current team
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.command(name='viewteam', 
                      aliases=['team'],
                      help="This command allows you to view all of the current members on your team. Your team can be used to challenge other players or to fight in raids.")
    async def view_team(self, ctx, *, member: discord.Member = None):
        try:
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
       
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while a user was trying to view their team on line {line_num}")

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
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno
            file_name = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]

            await create_error_embed(ctx=ctx, error=error, msg=f"This occured on line {line_num} in {file_name}")
        
async def setup(bot):
    await bot.add_cog(Fighting(bot))

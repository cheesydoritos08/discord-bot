from discord.ext import commands
import discord
import asyncio
import handlers.database_handler as database_handler
import sys
from utils.utility_functions import create_error_embed, cooldown_calculator

class Crew_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    # BUFF RAID REWARDS
    @commands.command(name="crewcreate",
                      help="This command allows you to create a crew with up to four members including yourself. The syntax for this command is ?crewcreate <crew name>.")
    async def create_crew(self, ctx, *, name : str):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't be in two crews. Traitor.")
            
            # Checks to see if the crew name is already in use
            crews = database_handler.crews.find({})

            for crew in crews:
                if name == crew.get('crew_name'):
                    return await ctx.send("Be original for once and use a name that no one else has used.")

            # Checks to see if the user has enough money to form a crew
            cost = 10 * 1000 # ten thousand

            user_balance = user_profile.get('economy').get('won')

            if user_balance < cost:
                return await ctx.send("You don't even have enough money to form a crew. Pathetic.")
            
            # Deducts the won from the users balance
            database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=-cost)

            # Creates a crew dictionary with crew head name, crew member slots, crew balance, crew passive income for each member,
            # character slots for sending out on expeditions
            crew_dictionary = {
                "crew_head": ctx.author.id,
                "crew_name": name,
                "crew_balance": 0,
                "crew_member_one": {
                    "crew_member_id": ctx.author.id,
                    "last_income_claimtime": 0,
                    "current_scouting_member": ""       
                },
                "crew_member_two": {
                    "crew_member_id": 0,
                    "last_income_claimtime": 0,
                    "current_scouting_member": ""           
                },
                "crew_member_three": {
                    "crew_member_id": 0,
                    "last_income_claimtime": 0,
                    "current_scouting_member": ""          
                },
                "crew_member_four": {
                    "crew_member_id": 0,
                    "last_income_claimtime": 0,
                    "current_scouting_member": ""          
                }
            }
            
            # Sends the dictionary to the database
            database_handler.crews.insert_one(crew_dictionary)
            database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'crew.in_crew': True}})
            database_handler.users.update_one({'_id': ctx.author.id}, {'$set': {'crew.crew_name': name}})

            
            # Sends a message to the user saying their crew "crew name" has been created 
            return await ctx.send(f"You have created the crew called {name}.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while creating a crew on line {line_num}")

    @commands.command(name="crewinvite",
                      help="This command allows you to invite other users to a crew if you are the head of that crew. The syntax for this command is ?crewinvite @user.")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def invite_crew_member(self, ctx, invitee : discord.Member):
        try:
            # Checks to see if the users have a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=invitee.id, another_user=True):
                return
            
            if invitee == ctx.author:
                return await ctx.send("You can't invite yourself stupid.")
            
            inviter_user_profile = database_handler.users.find_one({"_id": ctx.author.id})
            invitee_user_profile = database_handler.users.find_one({"_id": invitee.id})

            # Check to see if inviter is in crew
            if not inviter_user_profile.get('crew').get('in_crew'):
                return await ctx.send("You have to be in a crew first to invite other people.")
            
            # Check if inviter is head of the crew they are in
            crews = database_handler.crews.find({})

            for crew in crews:            
                if (crew.get('crew_member_one').get('crew_member_id') == ctx.author.id 
                    or crew.get('crew_member_two').get('crew_member_id') == ctx.author.id 
                    or crew.get('crew_member_three').get('crew_member_id') == ctx.author.id 
                    or crew.get('crew_member_four').get('crew_member_id') == ctx.author.id):
                    crew_being_joined = crew
                    break
               
            if crew_being_joined.get('crew_head') != ctx.author.id:
                return await ctx.send("You have to be the head of a crew to invite other people.")

            # Check to see if invitee is already in crew
            if invitee_user_profile.get('crew').get('in_crew'):
                return await ctx.send("This user is already in a crew.")
            
            # Send message asking for invitee if they want to join crew
            await ctx.send(f"{invitee.mention}, would you like to join this crew? Please reply with `yes` or `no`.")

            def check(m):
                return m.channel == ctx.channel and m.author == invitee
            
            msg : discord.Message = await self.bot.wait_for('message', check=check, timeout = 10.0)

            if msg.content.lower() == "yes":
                # If yes, invitee is added to crew and crew stats are updated
                if crew_being_joined.get('crew_member_one').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_one']['crew_member_id'] = invitee.id
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_two').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_two']['crew_member_id'] = invitee.id
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_three').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_three']['crew_member_id'] = invitee.id
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_four').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_four']['crew_member_id'] = invitee.id
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                else:
                    return await ctx.send("This crew is currently full.")
                
                database_handler.crews.find_one_and_replace({"crew_head": ctx.author.id}, crew_being_joined)
                database_handler.users.find_one_and_replace({"_id": invitee.id}, invitee_user_profile)

                return await ctx.send(f"{invitee} has successfully been added to the crew.")


            elif msg.content.lower() == "no":
                return await ctx.send("The invite has been declined.")
            else:
                return await ctx.send("Wrong response.")

        except asyncio.TimeoutError as e:
            return await ctx.send("Too slow. Answer faster next time.")
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while creating a crew on line {line_num}")
      
    @create_crew.error
    @invite_crew_member.error
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



async def setup(bot):
    await bot.add_cog(Crew_Commands(bot))
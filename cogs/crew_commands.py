from discord.ext import commands
import discord
import re
import time
import asyncio
import math
import random
import validators
import handlers.database_handler as database_handler
import sys
from utils.utility_functions import create_error_embed, cooldown_calculator, num_to_words_dict
from utils.timer import Timer
from utils.buttons import CrewUpgradesButton

class Crew_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()



    @commands.command(name="crewcreate",
                      help="This command allows you to create a crew with up to four members including yourself. Creating a crew costs 10,000 won. The syntax for this command is ?crewcreate <crew name>.")
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
                "crew_level": 0,
                "crew_income_rate": 0,
                "crew_scout_time_reduction": 0,
                "crew_image_url": "",
                "crew_embed_color": "",
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
                if crew.get('crew_name') == inviter_user_profile.get('crew').get('crew_name'):
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

                    if crew_being_joined.get("crew_level") > 0:
                        crew_being_joined['crew_member_one']['last_income_claimtime'] = round(time.time())

                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_two').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_two']['crew_member_id'] = invitee.id
                    
                    if crew_being_joined.get("crew_level") > 0:
                        crew_being_joined['crew_member_two']['last_income_claimtime'] = round(time.time())
                        
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_three').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_three']['crew_member_id'] = invitee.id

                    if crew_being_joined.get("crew_level") > 0:
                        crew_being_joined['crew_member_three']['last_income_claimtime'] = round(time.time())
                        
                    invitee_user_profile['crew']['in_crew'] = True
                    invitee_user_profile['crew']['crew_name'] = crew_being_joined['crew_name']

                elif crew_being_joined.get('crew_member_four').get('crew_member_id') == 0:
                    crew_being_joined['crew_member_four']['crew_member_id'] = invitee.id

                    if crew_being_joined.get("crew_level") > 0:
                        crew_being_joined['crew_member_four']['last_income_claimtime'] = round(time.time())
                        
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

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to invite someone to a crew on line {line_num}")

    @commands.command(name="crewleave",
                      help="This command allows you to leave a crew. If you are the current head of the crew, leaving the crew will result in the deletion of the crew. Leaving a crew costs 20,000 won. The syntax for this command is ?crewleave")
    async def leave_crew(self, ctx):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't leave a crew if you aren't even in one.")

            # Checks to see if the user has enough money to leave the crew
            cost = 20 * 1000 # twenty thousand

            user_balance = user_profile.get('economy').get('won')

            if user_balance < cost:
                return await ctx.send("You don't even have enough money to leave the crew. Pathetic.")
            
            # Deducts the won from the users balance
            database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=-cost)

            # Removes user from the crew
            crews = database_handler.crews.find({})

            def remove_from_crew(crew, crew_member_number):
                crew_member_id = crew[crew_member_number]['crew_member_id']
                
                # Makes sure there's an actual member in the slot
                if crew_member_id == 0:
                    return

                crew_member_profile = database_handler.users.find_one({"_id": crew_member_id})
                crew[crew_member_number]['crew_member_id'] = 0
                crew[crew_member_number]['last_income_claimtime'] = 0
                crew[crew_member_number]['current_scouting_member'] = ""
                crew_member_profile['crew']['in_crew'] = False
                crew_member_profile['crew']['crew_name'] = ""
                database_handler.users.find_one_and_replace({"_id": crew_member_id}, crew_member_profile)
            
            for crew in crews:
                if crew.get('crew_member_one').get('crew_member_id') == ctx.author.id:
                    former_crew = crew
                    remove_from_crew(crew, 'crew_member_one')
                    database_handler.crews.find_one_and_replace({"crew_name": crew['crew_name']}, crew) 
                    break

                elif crew.get('crew_member_two').get('crew_member_id') == ctx.author.id:
                    former_crew = crew
                    remove_from_crew(crew, 'crew_member_two')
                    database_handler.crews.find_one_and_replace({"crew_name": crew['crew_name']}, crew)
                    break

                elif crew.get('crew_member_three').get('crew_member_id') == ctx.author.id:
                    former_crew = crew
                    remove_from_crew(crew, 'crew_member_three')
                    database_handler.crews.find_one_and_replace({"crew_name": crew['crew_name']}, crew)
                    break

                elif crew.get('crew_member_four').get('crew_member_id') == ctx.author.id:
                    former_crew = crew
                    remove_from_crew(crew, 'crew_member_four')
                    database_handler.crews.find_one_and_replace({"crew_name": crew['crew_name']}, crew)
                    break
            
            # Checks to see if user was the head of the former crew and deletes the crew
            if former_crew.get('crew_head') == ctx.author.id:
                for x in range(1, 5):
                    remove_from_crew(former_crew, f"crew_member_{num_to_words_dict[x]}")
                
                database_handler.crews.find_one_and_delete({"crew_name": former_crew['crew_name']})
                return await ctx.send(f"{former_crew['crew_name']} has been disbanded.")
            
            return await ctx.send(f"You have left {former_crew['crew_name']}")
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to leave a crew on line {line_num}")

    @commands.command(name="crewview",
                      help="This command allows you to view your current crew. The syntax for this command is ?crewview")
    async def view_crew(self, ctx):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't view your crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            if user_crew["crew_embed_color"] != "": 
                embed = discord.Embed(title=f"{user_crew['crew_name']} Crew",
                                      color=int(f"0x{str(user_crew["crew_embed_color"])[1:]}", 16))
            else:
                embed = discord.Embed(title=f"{user_crew['crew_name']} Crew")

            embed.add_field(name="",
                            value=f"**Crew Head**\n{self.bot.get_user(user_crew['crew_head'])}",
                            inline=True)
            embed.add_field(name="",
                            value=f"",
                            inline=True)
            embed.add_field(name="",
                            value=f"**Crew Stats**\n**Level:** {user_crew['crew_level']}\n**Balance:** ₩{user_crew['crew_balance']}",
                            inline=True)
            embed.add_field(name="",
                            value=f"",
                            inline=False)
            embed.add_field(name="",
                            value=f"**Members**\n1. {self.bot.get_user(user_crew.get("crew_member_two").get('crew_member_id')) if user_crew.get("crew_member_two").get('crew_member_id') != 0 else "None"}\n2. {self.bot.get_user(user_crew.get("crew_member_three").get('crew_member_id')) if user_crew.get("crew_member_three").get('crew_member_id') != 0 else "None"}\n3. {self.bot.get_user(user_crew.get("crew_member_four").get('crew_member_id')) if user_crew.get("crew_member_four").get('crew_member_id') != 0 else "None"}",
                            inline=True)
            embed.add_field(name="",
                            value=f"",
                            inline=True)
            embed.add_field(name="Crew Upgrade",
                            value=f"**Passive Income Rate Per Minute:** {user_crew['crew_income_rate']}\n**Scout Time Reduction:** {user_crew['crew_scout_time_reduction']} minutes",
                            inline=True)

            if user_crew["crew_image_url"] != "":
                embed.set_image(url=user_crew['crew_image_url'])

            await ctx.send(embed=embed)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to view a crew on line {line_num}")

    @commands.command(name="crewsetimage",
                      help="This command allows you to set the picture for your crew if you are the crew head. If you want to remove a picture, simply type None instead of a url. The syntax for this command is ?crewsetimage <url>")
    async def set_crew_image(self, ctx, url : str):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't set the image for a crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            # Checks to see if the user is the head of their crew
            if user_crew['crew_head'] != ctx.author.id:
                return await ctx.send("Only the crew head can set the image for their crew, not a low life like you.")

            if url.lower() == "none":
                url = ""
            else:
                valid_image_url=validators.url(url)
                if valid_image_url != True:
                    return await ctx.send("Invalid url.")
            
            database_handler.crews.find_one_and_update({"crew_name": crew['crew_name']}, {"$set": {"crew_image_url": url}})

            return await ctx.send("You have successfully updated the image url. Run the ?crewview command to make sure the url works.")


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to set the image for a crew on line {line_num}")

    @commands.command(name="crewsetcolor",
                      help="This command allows you to set the embed color for your crew if you are the crew head by typing a hexcode. If you want to remove a color, simply type None instead of a hexcode. The syntax for this command is ?crewsetcolor <hexcode>")
    async def set_crew_color(self, ctx, hexcode):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't set the image for a crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            # Checks to see if the user is the head of their crew
            if user_crew['crew_head'] != ctx.author.id:
                return await ctx.send("Only the crew head can set the color for their crew, not a low life like you.")

            # Makes sure that the hexcode entered is actually a hexcode
            def is_valid_hexa_code(string):
                hexa_code = re.compile(r'^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$')
                return bool(re.match(hexa_code, string))

            if is_valid_hexa_code(hexcode):
                database_handler.crews.find_one_and_update({"crew_name": crew['crew_name']}, {"$set": {"crew_embed_color": hexcode}})
                return await ctx.send("You have successfully updated the embed color. Run the ?crewview command to make sure the color works.")
            
            elif hexcode.lower() == "none":
                database_handler.crews.find_one_and_update({"crew_name": crew['crew_name']}, {"$set": {"crew_embed_color": ""}})
                return await ctx.send("You have successfully updated the embed color. Run the ?crewview command to make sure the color works.")
            
            else:
                return await ctx.send("This isn't a valid hexcode. Put in a hexcode with the hashtag.")
            

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to set the embed color for a crew on line {line_num}")

    @commands.command(name="crewdeposit",
                      help="This command allows you to deposit your money into the crew bank. Any money deposited **can not** be withdrawn. The money in the crew bank can be used for upgrades to the crew. The syntax for this command is ?crewdeposit <amount>")
    async def deposit_money_in_crew_bank(self, ctx, amount : float):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't give money to a crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            # Checks to see if the user has the money to deposit to the crew
            if amount > user_profile.get('economy').get('won'):
                return await ctx.send("You can't give what you don't have. Get out of here and go make some money.")
            
            database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=-amount)
            database_handler.crews.find_one_and_update({"crew_name": crew['crew_name']}, {"$inc": {"crew_balance": amount}})

            return await ctx.send(f"You have successfully deposited ₩{amount} to the crew bank.")


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to set the image for a crew on line {line_num}")

    @commands.command(name="crewupgrade",
                      help="This command allows you to upgrade your crew to the next level. Only the head of the crew is allowed to do this. If you want to see all the upgrades and their requirements, just type ?crewupgrade. The syntax for this command is ?crewupgrade <level>")
    async def upgrade_crew(self, ctx, level : int = None):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't upgrade your crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            if level is not None:
                # Checks to see if the user is the head of their crew
                if user_crew['crew_head'] != ctx.author.id:
                    return await ctx.send("Only the crew head can upgrade the crew, not a low life like you.")
                
                next_level = user_crew['crew_level'] + 1

                if level > 10:
                    return await ctx.send("The maximum upgrade level is 10.")
                elif level != next_level:
                    return await ctx.send(f"The next level you can upgrade to is {next_level}. Not more or less stupid.")

                # Checks to see if the crew has enough money to upgrade
                crew_balance = user_crew['crew_balance']
                upgrade_price = level * 100000

                if crew_balance < upgrade_price:
                    return await ctx.send("Your crew is too weak to even buy this upgrade. Pathetic.")
                
                database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$inc": {"crew_balance": -upgrade_price}})

                if level % 2 == 1:
                    next_income_upgrade = 7
                    database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$inc": {"crew_income_rate": next_income_upgrade}})

                    for x in range(1, 5):
                        if level == 1 and user_crew[f'crew_member_{num_to_words_dict[x]}']['crew_member_id'] != 0:
                            database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$set": {f'crew_member_{num_to_words_dict[x]}.last_income_claimtime': round(time.time())}})

                elif level % 2 == 0:
                    next_time_upgrade = 30
                    database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$inc": {"crew_scout_time_reduction": next_time_upgrade}})

                user_crew['crew_level'] += 1
                database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$inc": {"crew_level": 1}})
                return await ctx.send(f"Your current crew level is {user_crew['crew_level']}.")      
            
            else:
                crew_upgrades_dictionary = {}
                
                for x in range(0, 10, 2):
                    crew_upgrades_dictionary[x + 1] = {
                        "name": f"Upgrade {x + 1} {"✅" if user_crew['crew_level'] >= (x + 1) else "❌"}",
                        "value": f"Description: Upgrades the amount of money earned per minute from your crew to {round((3.5 * x) + 7)} won\nCost: ₩{x + 1}00,000",
                    }

                    crew_upgrades_dictionary[x + 2] = {
                        "name": f"Upgrade {x + 2} {"✅" if user_crew['crew_level'] >= (x + 2) else "❌"}",
                        "value": f"Description: Shortens the time it takes for a character to return from a scouting mission by 30 minutes\nCost: ₩{x + 2}00,000",
                    }

                    if x + 2 == 10:
                        crew_upgrades_dictionary[x + 2] = {
                            "name": f"Upgrade {x + 2} {"✅" if user_crew['crew_level'] >= (x + 2 )else "❌"}",
                            "value": f"Description: Shortens the time it takes for a character to return from a scouting mission by 30 minutes\nCost: ₩1,000,000",
                        }
                    
                buttons = CrewUpgradesButton(crew_upgrades_dictionary = crew_upgrades_dictionary, ctx = ctx) 
                embed = await buttons.create_embed()

                return await ctx.send(embed=embed, view=buttons)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to upgrade a crew on line {line_num}")

    @commands.command(name="crewclaim",
                      help="This command allows you to claim money from your crew. This is unlocked after the first upgrade and can be claimed anytime. The syntax for this command is ?crewclaim")
    async def claim_crew_money(self, ctx, level : int = None):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't upgrade claim money from a crew if you aren't in one.")
            
            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            # Checks to see if the crew can earn income
            if user_crew['crew_income_rate'] <= 0:
                return await ctx.send("You need the first upgrade for your crew to start earning passive income.")
           
            # Finds what crew member the user is
            for x in range(1, 5):
                if user_crew[f'crew_member_{num_to_words_dict[x]}']['crew_member_id'] == ctx.author.id:
                    crew_member_position = f'crew_member_{num_to_words_dict[x]}'
            
            last_claimtime = user_crew[crew_member_position]['last_income_claimtime']

            current_claimtime = time.time()
            difference_between_time = current_claimtime - last_claimtime

            # Gives the money to the user and resets timestamp
            money_awarded = math.floor((difference_between_time / 60)) * user_crew['crew_income_rate']

            database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=money_awarded)
            database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$set": {f"{crew_member_position}.last_income_claimtime": current_claimtime}})
            
            return await ctx.send(f"You have claimed ₩{money_awarded}. Please come back later to earn more.")


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to upgrade a crew on line {line_num}")

    @commands.command(name="crewscout",
                      aliases=['scout'],
                      help="This command allows you to send a character on a scouting mission. Scouting missions can bring back shards, items, and tickets. Sending higher rarity characters on missions will result in more rewards and having a higher crew level results in more valuable rewards. To claim your rewards once scouting is over, just type ?crewscout. The syntax for this command is ?crewscout <character name>")
    async def send_character_on_scouting_mission(self, ctx, *, character_name : str = None):
        try:
            # Checks to see if the user has a profile or not
            if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
                return
            
            user_profile = database_handler.users.find_one({"_id": ctx.author.id})

            # Checks to see if the user is in a crew already
            if not user_profile.get('crew').get('in_crew'):
                return await ctx.send("You can't send a member on a scouting mission if you aren't in a crew.")

            crews = database_handler.crews.find({})

            for crew in crews:            
                if crew.get('crew_name') == user_profile.get('crew').get('crew_name'):
                    user_crew = crew
                    break
            
            # Finds what crew member the user is
            for x in range(1, 5):
                if user_crew[f'crew_member_{num_to_words_dict[x]}']['crew_member_id'] == ctx.author.id:
                    crew_member_position = f'crew_member_{num_to_words_dict[x]}'
            
            # Runs if the character is trying to claim the rewards from a scouting mission
            if character_name is None:
                if user_crew[crew_member_position]["current_scouting_member"] == "":
                    return await ctx.send("You don't currently have any characters out scouting. Type ?crewscout <character name> to send a character out.")
                
                if user_profile['timers']["scouting_member_return"] != 0:
                    return await ctx.send(f"{user_crew[crew_member_position]["current_scouting_member"]} is still out scouting. Wait for them to return before claiming their rewards.")
                
                user_character = database_handler.user_character_finder(user_id=ctx.author.id, character_name=user_crew[crew_member_position]["current_scouting_member"])
                
                rewards_dictionary = {
                    10: {
                        "common_shard": 100,
                        "rare_shard": 100,
                        "epic_shard": 60,
                        "legendary_shard": 5,
                        "standard_ticket": 100,
                        "limited_ticket": 15,
                        "white_shirt": 40,
                        "broken_sunglasses": 70,
                        "boxing_gloves": 50,
                        "biker_helmet": 80,
                        "leather_jacket": 60
                        },
                    7: {
                        "common_shard": 100,
                        "rare_shard": 80,
                        "epic_shard": 40,
                        "legendary_shard": 4,
                        "standard_ticket": 70,
                        "limited_ticket": 10,
                        "white_shirt": 30,
                        "broken_sunglasses": 60,
                        "boxing_gloves": 40,
                        "biker_helmet": 70,
                        "leather_jacket": 50
                        },
                    4: {
                        "common_shard": 100,
                        "rare_shard": 50,
                        "epic_shard": 20,
                        "legendary_shard": 3,
                        "standard_ticket": 50,
                        "limited_ticket": 5,
                        "white_shirt": 20,
                        "broken_sunglasses": 50,
                        "boxing_gloves": 30,
                        "biker_helmet": 60,
                        "leather_jacket": 40
                        },
                    1: {
                        "common_shard": 100,
                        "rare_shard": 30,
                        "epic_shard": 5,
                        "legendary_shard": 1,
                        "standard_ticket": 30,
                        "limited_ticket": 1,
                        },

                }

                threshold = 0

                for item in rewards_dictionary:
                    if item <= user_crew['crew_level']:
                        threshold = item
                        break
                
                user_rewards = {}
            
                # Rolls a random number for each item in the rewards dictionary to see if
                # the user gets the item
                for item, percentage in rewards_dictionary[threshold].items():
                    random_num = random.randint(1, 100)
                    
                    if percentage >= random_num:
                        if user_character['rarity'] == "Common":
                            num_of_rewards = random.randint(1, 2)

                        elif user_character['rarity'] == "Rare":
                            num_of_rewards = random.randint(1, 3)

                        elif user_character['rarity'] == "Epic":
                            num_of_rewards = random.randint(1, 4)

                        elif user_character['rarity'] == "Legendary":
                            num_of_rewards = random.randint(1, 5)

                        user_rewards[item] = num_of_rewards

                user_inventory = user_profile.get('inventory')

                for reward, amount in user_rewards.items():
                    reward_given = False
                    
                    for item in user_inventory:
                        try:
                            if reward == item:
                                database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{reward}.amount", value=amount)
                                reward_given = True
                        except Exception as e:
                            create_error_embed(error=e, ctx=self.ctx, msg="This occurred while trying to add items won from a scout to a user's inventory.")
                    
                    if not reward_given:
                        database_handler.add_item(user_id=ctx.author.id, item=reward)
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{reward}.amount", value=amount)

                embed = discord.Embed(title="Scouting Missions Rewards",
                                      color=discord.Color.from_rgb(17, 242, 227))

                embed.add_field(name="",
                    value=f"{user_crew[crew_member_position]["current_scouting_member"]} has brought back the following rewards: \n\n{"\n".join([f"`{reward.replace("_", " ").title()}`: {amount}" for reward, amount in user_rewards.items()])}",
                    inline=False)
                
                database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$set": {f"{crew_member_position}.current_scouting_member": ""}})

                return await ctx.send(embed=embed)
            
            # Runs if the user is sending out a character on a scouting mission
            # Checks to see if they already have a member out on a scouting mission.
            if user_crew[crew_member_position]["current_scouting_member"] != "":
                return await ctx.send(f"You already have {user_crew[crew_member_position]["current_scouting_member"]} out scouting. Wait for them to return before sending out another character.")
            
            # Gets the character passed into the command
            user_character = database_handler.user_character_finder(user_id=ctx.author.id, character_name=character_name.title())

            if user_character is None:
                return await ctx.send(f"You do not have {character_name.title()}.")
            
            database_handler.crews.update_one({"crew_name": user_crew['crew_name']}, {"$set": {f"{crew_member_position}.current_scouting_member": character_name.title()}})

            # Gets the scout time for the crew
            scout_time = 60 * 60 * 8 # --> 8 hours
            
            if user_crew['crew_scout_time_reduction'] != 0:
                scout_time -= user_crew['crew_scout_time_reduction'] * 60 # Scout time reduction in minutes times the number of seconds per minute
            
            Timer(user_id=ctx.author.id, name="scouting_member_return", starttime=round(time.time()), timer_length=scout_time).create_timer()
            
            return await ctx.send(f"{character_name.title()} has been sent on a scouting mission. Come back in {cooldown_calculator(scout_time)} to claim what they found.")

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while trying to send a character on a scouting mission/claim their rewards on line {line_num}")

    @create_crew.error
    @invite_crew_member.error
    @leave_crew.error
    @view_crew.error
    @set_crew_image.error
    @set_crew_color.error
    @deposit_money_in_crew_bank.error
    @upgrade_crew.error
    @claim_crew_money.error
    @send_character_on_scouting_mission.error
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

            elif isinstance(error, commands.MissingRequiredArgument):
                return await ctx.send("You typed the command incorrectly. Double check how to run the command by typing `?help <command name>`")



async def setup(bot):
    await bot.add_cog(Crew_Commands(bot))
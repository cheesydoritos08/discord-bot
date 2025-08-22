from discord.ext import commands
import discord
import handlers.database_handler as database_handler
import sys
from utils.utility_functions import create_error_embed

class Crew_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # BUFF RAID REWARDS
    @commands.command(name="crewcreate",
                      help="This command allows you to create a crew with up to four members including yourself. The syntax for this command is ?crewcreate <crew name>.")
    async def create_crew(self, ctx, *, name : str):
        try:
            # Checks to see if the user has enough money to form a crew
            cost = 10 * 1000 # ten thousand

            user_balance = database_handler.users.find_one({"_id": ctx.author.id}).get('economy').get('won')

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
                    "crew_member_id": 0,
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
            }
            
            # Sends the dictionary to the database
            database_handler.crews.insert_one(crew_dictionary)
            
            # Sends a message to the user saying their crew "crew name" has been created 
            return await ctx.send(f"You have created the crew called {name}.")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while creating a crew on line {line_num}")

    @commands.command(name="crewinvite",
                      help="This command allows you to create a crew with up to four members including yourself. The syntax for this command is ?crewcreate <crew name>.")
    async def create_crew(self, ctx, member : discord.Member):
        try:
            pass
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            await create_error_embed(ctx=ctx, error=e, msg=f"This occured while creating a crew on line {line_num}")
      

async def setup(bot):
    await bot.add_cog(Crew_Commands(bot))
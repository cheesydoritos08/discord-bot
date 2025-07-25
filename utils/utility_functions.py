from discord.ext import tasks
import handlers.database_handler as database_handler 
import discord 
import datetime


def check_boosts(user_id, type):
    # Sets the variables for all the boosters
    multiplier = 1
    user_profile = database_handler.users.find_one({"_id": user_id})
    buffs_list = user_profile.get("buffs")
    rank_boost = user_profile.get("elo").get("won_booster")

    if buffs_list[type]["active"]:
        multiplier = buffs_list[type]["multiplier"]

    if type == "won_booster":
        multiplier *= rank_boost
        
    # Returns how much to multiply money by
    return multiplier

def cooldown_calculator(time_to_calculate):
    # Calculates the time left to cool down in minutes, hours and days
    remaining_time = round(time_to_calculate)
    hours, remainder = divmod(remaining_time, 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f'{hours}h {minutes}m and {seconds}s'
    elif minutes:
        return f'{minutes}m and {seconds}s'
    else:
        return f'{seconds}s'

def update_quests(user_id, quest_id, amount):
    # Sets variables
    user_profile = database_handler.users.find_one({"_id": user_id})
    user_quests = user_profile.get("quests")
    user_inventory = user_profile.get('inventory')

    if not user_quests:
        return
    
    quests_completed = 0

    for i, quest in enumerate(user_quests):
        # Checks to see if the quest is already completed or not
        if quest["_id"] == quest_id and quest["total_completed"] >= quest["total_needed"]:
            continue
        
        # Updates the total completed if the quest ids match
        if quest["_id"] == quest_id:
            quest["total_completed"] += amount
            database_handler.users.update_one({"_id": user_id}, {"$set": {f"quests.{i}.total_completed": quest["total_completed"]}})
        
        # Checks to see if the user completes the quest in that moment
        if quest["_id"] == quest_id and quest["total_completed"] >= quest["total_needed"]: 
            database_handler.inc_value_to_users(user_id=user_id, key="economy.won", value=1000)
            standard_ticket_in_inventory = False

            for item in user_inventory:
                if item == "standard_ticket":
                    database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.standard_ticket.amount", value=2)
                    standard_ticket_in_inventory = True
            
            if not standard_ticket_in_inventory:
                database_handler.add_item(user_id=user_id, item="standard_ticket")
                database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.standard_ticket.amount", value=1)
        
        # Counts all other quests that were already completed before hand
        if quest["total_completed"] >= quest["total_needed"]:
            quests_completed += 1        

    # Checks to see if all the quests are completed and they haven't been completed before
    if quests_completed >= len(user_quests) and not user_profile['all_quests_complete']:
        limited_ticket_in_inventory = False
        database_handler.users.update_one({"_id": user_id}, {"$set": {"all_quests_complete": True}})  

        for item in user_inventory:
            if item == "limited_ticket":
                database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.limited_ticket.amount", value=5)
                limited_ticket_in_inventory = True
            
        if not limited_ticket_in_inventory:
            database_handler.add_item(user_id=user_id, item="limited_ticket")
            database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.limited_ticket.amount", value=5)


@tasks.loop(seconds=5.0, reconnect=True)
async def log_error_embed(bot):
    try:
        # Grabs the first error from the list
        error_list = []
        for error in database_handler.errors.find({}).limit(1):
            error_list.append(error)

        if not error_list:
            return
        
        # Gets the server to report to and the channel to report to
        server = discord.utils.get(bot.guilds, id=1382922154957344838)
        report = discord.utils.get(server.text_channels, id=1382924705941553152)

        error = error_list[0]

        # Creates an embed based on the contents of the error message
        if error["initial_embed"]["timestamp"] != "":
            embed = discord.Embed(title=error["initial_embed"]["title"],
                                description=error["initial_embed"]["description"],
                                timestamp=error["initial_embed"]["timestamp"],
                                color=discord.Color.red())
            
            embed.add_field(name="Additional Info:",
                            value=error["additional_info"]["value"])
        else:
            embed = discord.Embed(title=error["initial_embed"]["title"],
                                description=error["initial_embed"]["description"],
                                color=discord.Color.red()
                            )
            embed.add_field(name="Additional Info:",
                            value="This most likely occured on startup/resume or from a background process that doesn't have access to context like voting or searching through the database.")


        embed.add_field(name="Developer Message",
                        value=error['developer_message']['value'])
        
        await report.send(embed=embed)    

        # Deletes the error message from the database
        database_handler.errors.delete_one({"_id": error["_id"]})
    
    except Exception as e:
        print(f"Error in logging error embed: {e}")


def create_error_embed(error, ctx=None, msg="None given."):
    # Template for error message
    error_message = {
        "initial_embed": {
            "title": "An error occured",
            "description": f"**Error:** \n{type(error).__name__}: {error}",
            "timestamp": ""
        },
        "additional_info": {
            "value": ""
        },
        "developer_message": {
            "value": msg
        }
    }
    try:
        # Adds additional info to the error message if context exists
        if ctx is not None:
            error_message["additional_info"]["value"] = f"User: {ctx.author}\nChannel Sent in: {ctx.channel}\nMessage Sent: {ctx.message.content}\n Guild: {ctx.guild}\n Command Name: {ctx.invoked_with}"
            error_message["initial_embed"]["timestamp"] = datetime.datetime.fromtimestamp(ctx.message.created_at.timestamp())
    except Exception as e:
        print(f"Error in creating error embed: {e}")
    
    database_handler.errors.insert_one(error_message)




            

            
import handlers.database_handler as database_handler 
import discord 

def check_boosts(user_id, type):
    multiplier = 1
    user_profile = database_handler.users.find_one({"_id": user_id})
    buffs_list = user_profile.get("buffs")
    rank_boost = user_profile.get("elo").get("yen_booster")

    if buffs_list[type]["active"]:
        multiplier = buffs_list[type]["multiplier"]

    if type == "yen_booster":
        multiplier *= rank_boost
        
    return multiplier

def cooldown_calculator(time_to_calculate):
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
    user_profile = database_handler.users.find_one({"_id": user_id})
    user_quests = user_profile.get("quests")
    user_inventory = user_profile.get('inventory')

    if not user_quests:
        return
    
    quests_completed = 0

    for i, quest in enumerate(user_quests):
        if quest["_id"] == quest_id and quest["total_completed"] >= quest["total_needed"]:
            continue
        
        if quest["_id"] == quest_id:
            quest["total_completed"] += amount
            database_handler.users.update_one({"_id": user_id}, {"$set": {f"quests.{i}.total_completed": quest["total_completed"]}})
        
        if quest["_id"] == quest_id and quest["total_completed"] >= quest["total_needed"]: 
            database_handler.inc_value_to_users(user_id=user_id, key="economy.yen", value=1000)
            standard_ticket_in_inventory = False

            for item in user_inventory:
                if item == "standard_ticket":
                    database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.standard_ticket.amount", value=2)
                    standard_ticket_in_inventory = True
            
            if not standard_ticket_in_inventory:
                database_handler.add_item(user_id=user_id, item="standard_ticket")
                database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.standard_ticket.amount", value=1)
        
        if quest["total_completed"] >= quest["total_needed"]:
            quests_completed += 1        

    if quests_completed >= len(user_quests) and not user_profile['all_quests_complete']:
        limited_ticket_in_inventory = False
        database_handler.users.update_one({"_id": user_id}, {"$set": {"all_quests_complete": True}})  

        for item in user_inventory:
            if item == "limited_ticket":
                database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.limited_ticket.amount", value=5)
                limited_ticket_in_inventory = True
            
        if not limited_ticket_in_inventory:
            database_handler.add_item(user_id=user_id, item="limited_ticket")
            database_handler.inc_value_to_users(user_id=user_id, key=f"inventory.limited_ticket.amount", value=4)

async def send_error_embed(bot, error, ctx=None):
    server = discord.utils.get(bot.guilds, id=1366943308659822743)
    report = discord.utils.get(server.text_channels, id=1375623174447956029)
    
    if ctx is not None:
        embed = discord.Embed(title="An error occured",
                                    description=f"**Error:** \n{error}",
                                    timestamp=ctx.message.created_at,
                                    color=discord.Color.red())
    else:
         embed = discord.Embed(title="An error occured at startup",
                                    description=f"**Error:** \n{error}",
                                    color=discord.Color.red())   
            
    await report.send(embed=embed)
            

            





# Give users 1000 yen and 2 standard tickets for completing a quest, if the user completes all three quests, give user
# 5 limited banner tickets also create embed for daily quests

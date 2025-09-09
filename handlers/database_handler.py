import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from utils.utility_functions import create_error_embed
from utils.converters import InventoryConverter

# Secures the string as a variable
load_dotenv('.env')
DATABASE_CONNECTION_STRING: str = os.getenv('DATABASE_CONNECTION_STRING')

cluster = MongoClient(DATABASE_CONNECTION_STRING)
db = cluster['discord-bot']
users = db['users']
all_characters = db['all_characters']
items = db['items']
quests = db['quests']
errors = db['errors']
guild_prefixes = db['prefixes']
crews = db['crews']


# Creates a new profile for the specified user_id
def create_new_profile(user_id):
    try:
        # Checks to see if an existing profile already exists for the user
        existing_user = users.find_one({'_id': user_id})

        if existing_user is not None:
            return

        new_profile = {
            '_id': user_id,
            'characters': [],
            'inventory': {},
            'economy': {'won': 5000, 'daily_streak': 0, 'last_claim_time': 0},
            'wins': 0,
            'losses': 0,
            'elo': {
                "score": 1000,
                "ranking": "None",
                "won_booster": 1},
            'common_characters': 0,
            'rare_characters': 0,
            'epic_characters': 0,
            'legendary_characters': 0,
            'threshold_one_characters': 0,
            'threshold_two_characters': 0,
            'threshold_three_characters': 0,
            'threshold_four_characters': 0,
            'pity': 0,
            'team': [],
            'vote': {
                'vote_streak': 0,
                'last_vote_time': 0
            },
            'in_challenge': False,
            'in_trade': False,
            'in_raid': False,
            'in_boss_raid': False,

            'all_quests_complete': False,
            'raid_level': 1,
            'buffs': {
                'xp_booster': {'active': False,
                            'multiplier': 0},
                'won_booster':  {'active': False,
                            'multiplier': 0}
            },
            'timers': {
                'won_booster': 0,
                'xp_booster': 0,
                'daily_claim': 0,
                'daily_quests': 0,
                'bot_vote': 0,
                'eloclaim': 0,
                "scouting_member_return": 0
            },
            'quests': [],
            'crew':{
                'in_crew': False,
                'crew_name': ""
            }
        }

        users.insert_one(new_profile)
    except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, msg=f"This occured when creating a new profile for a user in line {line_num}")
    

# Update value of specified key
def inc_value_to_users(user_id, key, value):
    try:
        users.update_one({'_id': user_id}, {'$inc': {key: value}})
    except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, msg=f"This occured when increasing a value for a user in line {line_num}")
    

# Adds an array to specified key
def add_array_to_users(user_id, key, array):
    try:
        users.update_one({'_id': user_id}, {'$addToSet': {key: array}})
    except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, msg=f"This occured when adding an array to a user in line {line_num}")
    
# Checks to see if a user has a certain character
def user_character_finder(user_id, character_name):
    try:
        user = users.find_one({'_id': user_id})

        # Checks to see if the user has the character passed in the parameters
        for character in user['characters']:
            if character['name'].lower() == character_name.lower():
                return character
        return None
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
        line_num = exc_traceback.tb_lineno

        create_error_embed(error=e, msg=f"This occured when searching for a character within a user in line {line_num}")
        return None

def all_characters_search(key, query):
    try:
        results = all_characters.find({key: query})
        matches = []
        for result in results:
            matches.append(result)
        return matches
    except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, msg=f"This occured when searching for a particular character in line {line_num}")
    
# Sets the stats of the character when they level up based on their rarity
def update_stats(character, index, user_id):
    try:
        threshold_level_reqs = {
                1: 50,
                2: 100,
                3: 150,
                4: 200
            } 
        
        leveling_cap = threshold_level_reqs[character['threshold']]

        # Checks to see if the character is already over the leveling cap and stops if true
        if character["LVL"] >= leveling_cap:
            character["XP"] = 0
            users.update_one({'_id': user_id}, {'$set': {f'characters.{index}.XP': character["XP"]}}) 
            return

        # Sets variables for the levels and remaining XP
        levels, remaning_xp = divmod(character["XP"], 2000)
        team = users.find_one({"_id": user_id}).get("team")
        new_character_level = character['LVL'] + levels
        character['XP'] = remaning_xp

        # Makes sures the character doesn't exceed the leveling cap
        if new_character_level > leveling_cap:
            levels = leveling_cap - character["LVL"]
            new_character_level = leveling_cap
            character["XP"] = 0

        stat_increase = {
            1: {
                'Common': {"type": "flat",
                        "hp": 10,
                        "atk": 1,
                        "spd": 2},
                'Rare':  {"type": "flat",
                        "hp": 13,
                        "atk": 2,
                        "spd": 2},
                'Epic': {"type": "percent",
                        "hp": 3,
                        "atk": 3,
                        "spd": 3},
                'Legendary': {"type": "percent",
                        "hp": 4,
                        "atk": 4,
                        "spd": 4},
                },
            2: {
                'Common': {"type": "flat",
                        "hp": 15,
                        "atk": 2,
                        "spd": 3},
                'Rare':  {"type": "flat",
                        "hp": 18,
                        "atk": 3,
                        "spd": 3},
                'Epic': {"type": "percent",
                        "hp": 1,
                        "atk": 1,
                        "spd": 1},
                'Legendary': {"type": "percent",
                        "hp": 2,
                        "atk": 2,
                        "spd": 2},
                },
            3: {
                'Common': {"type": "flat",
                        "hp": 20,
                        "atk": 3,
                        "spd": 4},
                'Rare':  {"type": "flat",
                        "hp": 23,
                        "atk": 4,
                        "spd": 4},
                'Epic': {"type": "percent",
                        "hp": 1.5,
                        "atk": 1.5,
                        "spd": 1.5},
                'Legendary': {"type": "percent",
                        "hp": 2.5,
                        "atk": 2.5,
                        "spd": 2.5},
                },
            4: {
                'Common': {"type": "flat",
                        "hp": 25,
                        "atk": 4,
                        "spd": 5},
                'Rare':  {"type": "flat",
                        "hp": 27,
                        "atk": 5,
                        "spd": 4},
                'Epic': {"type": "percent",
                        "hp": 2,
                        "atk": 2,
                        "spd": 2},
                'Legendary': {"type": "percent",
                        "hp": 3,
                        "atk": 3,
                        "spd": 3},
                }    
        }
    
        # Increases the stats for each level
        for x in range(levels):
            if stat_increase[character['threshold']][character["rarity"]]["type"] == "flat":
                character["HP"] += stat_increase[character['threshold']][character["rarity"]]["hp"]
                character["ATK"] += stat_increase[character['threshold']][character["rarity"]]["atk"]
                character["SPD"] += stat_increase[character['threshold']][character["rarity"]]["spd"]
            
            elif stat_increase[character['threshold']][character["rarity"]]["type"] == "percent":
                character["HP"] = round(character["HP"] * (1 + (stat_increase[character['threshold']][character["rarity"]]["hp"] / 100)))
                character["ATK"] = round(character["ATK"] * (1 + (stat_increase[character['threshold']][character["rarity"]]["atk"] / 100)))
                character["SPD"] = round(character["SPD"] * (1 + (stat_increase[character['threshold']][character["rarity"]]["spd"] / 100)))
            
        character['LVL'] = new_character_level
    
        # Updates the character with the new stats in both the character collection and the team
        users.update_one({"_id": user_id}, {"$set": {f"characters.{index}": character}})
        
        for i, char in enumerate(team):
            if char["name"] == character["name"]:
                character['current_hp'] = character['HP']
                users.update_one({"_id": user_id}, {"$set": {f"team.{i}": character}})
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
        line_num = exc_traceback.tb_lineno

        create_error_embed(error=e, msg=f"This occured when updating the stats for a character when they level up in line {line_num}")

def increment_character_xp(user_id, character, xp, return_xp=False):
        try:
            user = users.find_one({'_id': user_id})

            # Checks to see if the user has the character and updates the XP accordingly
            for i, user_character in enumerate(user['characters']):
                if user_character['name'].lower() == character.lower():
                    user_character['XP'] += xp

                    users.update_one({'_id': user_id, f'characters.{i}.name': user_character['name']},{'$set': {f'characters.{i}.XP': user_character['XP']}},)

                    if user_character['XP'] >= 2000:
                        update_stats(character=user_character, index=i, user_id=user_id)


                    if return_xp:
                        return user_character['XP']
            return
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, msg=f"This occured when incrementing a character's xp in line {line_num}")

def add_item(user_id, item : InventoryConverter):
    try:
        # Formats the item to be added to the inventory
        item = items.find_one({"name": item})
        item_name = item["name"].lower()
        item.pop("_id")
        item.pop("name")

        users.update_one({"_id": user_id}, {"$set": {f"inventory.{item_name}": item}})
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
        line_num = exc_traceback.tb_lineno

        create_error_embed(error=e, msg=f"This occured when adding an item to a user in line {line_num}")

async def check_existing_profile(ctx, user_id, another_user=False):
    try:
        # Checks to see if the profile exists
        if users.find_one({'_id': user_id}) is None and not another_user:
            await ctx.send('You can\'t use a command without a profile, genius. Use the `?tut` command to get started with me!')
            return False
        elif users.find_one({'_id': user_id}) is None:
            await ctx.send(
                'You can\'t run a command on someone if they don\'t have a profile. Tell them to use the `?tut` command to get started with me!'
            )
            return False
        else:
            return True
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
        line_num = exc_traceback.tb_lineno

        create_error_embed(error=e, msg=f"This occured when checking to see if a user had an existing profile in line {line_num}")



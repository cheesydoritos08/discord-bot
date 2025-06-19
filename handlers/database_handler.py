import os
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


# Creates a new profile for the specified user_id
def create_new_profile(user_id):
    # Checks to see if an existing profile already exists for the user
    existing_user = users.find_one({'_id': user_id})

    if existing_user is not None:
        return

    new_profile = {
        '_id': user_id,
        'characters': [],
        'inventory': {'shards': {}},
        'economy': {'yen': 5000, 'daily_streak': 0, 'last_claim_time': 0},
        'wins': 0,
        'losses': 0,
        'elo': {
            "score": 1000,
            "ranking": "None",
            "yen_booster": 1},
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
        'all_quests_complete': False,
        'raid_level': 1,
        'buffs': {
            'xp_booster': {'active': False,
                           'multiplier': 0},
            'yen_booster':  {'active': False,
                           'multiplier': 0}
        },
        'timers': {
            'yen_booster': 0,
            'xp_booster': 0,
            'daily_claim': 0,
            'daily_quests': 0,
            'bot_vote': 0
        },
        'quests': []
    }

    users.insert_one(new_profile)


# Update value of specified key
def inc_value_to_users(user_id, key, value):
    try:
        users.update_one({'_id': user_id}, {'$inc': {key: value}})
    except Exception as e:
        create_error_embed(error=e)


# Adds an array to specified key
def add_array_to_users(user_id, key, array):
    try:
        users.update_one({'_id': user_id}, {'$addToSet': {key: array}})
    except Exception as e:
        create_error_embed(error=e)


# Checks to see if a user has a certain character
def user_character_finder(user_id, character_name):
    try:
        user = users.find_one(
            {
                '_id': user_id,
            }
        )
        for character in user['characters']:
            if character['name'].lower() == character_name.lower():
                return character
        return None
    except Exception as e:
        create_error_embed(error=e)
        return None


def all_characters_search(key, query):
    try:
        results = all_characters.find({key: query})
        matches = []
        for result in results:
            matches.append(result)
        return matches
    except Exception as e:
        create_error_embed(error=e)

# Sets the stats of the character when they level up based on their rarity
def update_stats(character, index, user_id):
    leveling_cap = 30

    if character["LVL"] >= leveling_cap:
        character["XP"] = 0
        users.update_one({'_id': user_id}, {'$set': {f'characters.{index}.XP': character["XP"]}}) 
        return

    
    team_character = False
    levels, remaning_xp = divmod(character["XP"], 2000)
    team = users.find_one({"_id": user_id}).get("team")
    for char in team:
        if char["name"] == character["name"]:
            team_character = True

    new_character_level = character['LVL'] + levels
    character['XP'] = remaning_xp

    if new_character_level > leveling_cap:
        levels = leveling_cap - character["LVL"]
        new_character_level = leveling_cap
        character["XP"] = 0

    stat_increase = {
        'Common': {"type": "flat",
                   "hp": 10,
                   "atk": 2,
                   "spd": 2},
        'Rare':  {"type": "flat",
                   "hp": 15,
                   "atk": 3,
                   "spd": 2},
        'Epic': {"type": "percent",
                   "hp": 3,
                   "atk": 3,
                   "spd": 3},
        'Legendary': {"type": "percent",
                   "hp": 3,
                   "atk": 3,
                   "spd": 3},
                    }  
    
    for x in range(levels):
        if stat_increase[character["rarity"]]["type"] == "flat":
            character["HP"] += stat_increase[character["rarity"]]["hp"]
            character["ATK"] += stat_increase[character["rarity"]]["atk"]
            character["SPD"] += stat_increase[character["rarity"]]["spd"]
        
        elif stat_increase[character["rarity"]]["type"] == "percent":
            character["HP"] *= (1 + (stat_increase[character["rarity"]]["hp"] / 100))
            character["ATK"] *= (1 + (stat_increase[character["rarity"]]["atk"] / 100))
            character["SPD"] *= (1 + (stat_increase[character["rarity"]]["spd"] / 100))
        

    users.update_one({"_id": user_id}, {"$set": {f"characters.{index}.HP": round(character["HP"])}})
    users.update_one({"_id": user_id}, {"$set": {f"characters.{index}.ATK": round(character["ATK"])}})
    users.update_one({"_id": user_id}, {"$set": {f"characters.{index}.SPD": round(character["SPD"])}})
    users.update_one({'_id': user_id}, {'$set': {f'characters.{index}.LVL': new_character_level}}) 
    users.update_one({'_id': user_id}, {'$set': {f'characters.{index}.XP': character['XP']}}) 



    if not team_character:
        return
    
    for i, char in enumerate(team):
        if char["name"] == character["name"]:
            users.update_one({"_id": user_id}, {"$set": {f"team.{i}.HP": round(character["HP"])}})
            users.update_one({"_id": user_id}, {"$set": {f"team.{i}.current_hp": round(character["HP"])}})
            users.update_one({"_id": user_id}, {"$set": {f"team.{i}.ATK": round(character["ATK"])}})
            users.update_one({"_id": user_id}, {"$set": {f"team.{i}.SPD": round(character["SPD"])}})


def increment_character_xp(user_id, character, xp, return_xp=False):
    user = users.find_one({'_id': user_id})

    for i, user_character in enumerate(user['characters']):
        if user_character['name'].lower() == character.lower():
            user_character['XP'] += xp

            users.update_one(
                {'_id': user_id, f'characters.{i}.name': user_character['name']},
                {'$set': {f'characters.{i}.XP': user_character['XP']}},
            )

            if user_character['XP'] >= 2000:
                update_stats(character=user_character, index=i, user_id=user_id)


            if return_xp:
                return user_character['XP']
    return

def add_item(user_id, item : InventoryConverter):
    item = items.find_one({"name": item})
    item_name = item["name"].lower()
    item.pop("_id")
    item.pop("name")

    users.update_one({"_id": user_id}, {"$set": {f"inventory.{item_name}": item}})

async def check_existing_profile(ctx, user_id, another_user=False):
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



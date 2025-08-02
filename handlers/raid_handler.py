import math
import copy
import random
import discord
import sys
import handlers.database_handler as database_handler
from utils.utility_functions import update_quests, check_boosts, create_error_embed
from utils.buttons import RaidFighterButton, RaidItemButton



# TO DO: TEST THE DODGING AND OTHER EFFECTS

# Instantiates a new raid for the user
class RaidInstance():
    def __init__(self, level, ctx, team, bot):
        self.level = level
        self.bot = bot
        self.starting_level = level
        self.team = team
        self.ctx = ctx
        self.view = RaidView(ctx = ctx, raid = self)
        self.enemies = self.get_enemies()
        self.round = 1
        self.combat_log = []
        self.send_timeout_message = True
        self.turn = "user"
        self.player_rewards = {}
        self.user_character = None
        self.enemy_character = None
        self.items_in_use = []
        self.num_of_items_used = 0

        self.apply_stat_boosts()

        # Different states of the characters
        self.state = {
            "user": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
                "can_dodge": False,
            },
            "enemy": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
            },
        }

    # Applys stat boost for entire team if applicable
    def apply_stat_boosts(self):
        try:
            user_support = next((c for c in self.team if c["class"] == "Support"), None)

            if user_support:
                user_fighter_characters = [c for c in self.team if c["class"] != "Support"]
        
                for effect in user_support["effects"]:
                    if effect["stat"] == "SPD" or effect["stat"] == "ATK":
                        for char in user_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                    elif effect["stat"] == "HP":
                        for char in user_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                            char["current_hp"] = char[effect["stat"]]
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured while applying stat boosts during a raid on line {line_num}.")

    # Applys item stat boosts
    def apply_item_boosts(self, item):
        try:
            # Gets the info inside of the item
            item = item[f"{list(item.keys())[0]}"]
            for effect in item.get('effects'):
                # Checks what stat the item will be boosting and boosts the stats accordingly
                if effect['buff'].lower() == "hp":
                    for char in self.team:
                        char['current_hp'] = math.ceil(char['current_hp'] * (1 + (effect['buff_amount'] / 100)))
                        
                        if char['current_hp'] > char['HP']:
                            char['current_hp'] = char['HP']

                elif effect['buff'].lower() == "dodge":
                    self.state['user']['can_dodge'] = True

                else:
                    for char in self.team:
                        char[effect['buff']] = math.floor(char[effect['buff']] * (1 + (effect['buff_amount'] / 100)))

            self.num_of_items_used += 1

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured while trying to apply an item boost to the team on line {line_num}.")

    # Checks the duration of the current items:
    def check_item_boost_duration(self):
        try:
            for item in self.items_in_use:
                # Gets the info inside of the item
                item_name = f"{list(item.keys())[0]}"
                item_data = item[item_name]
                #print(item['effects'].pop(item['effects'].index(effect)))

                if item_data.get('effects') is None:
                    self.items_in_use.remove(item)
                    continue

                for effect in item_data.get('effects'):
                    # buffs the stat as long as it isn't dodge or hp
                    if effect['turn_duration'] <= 0 and (effect['buff'].lower() != "hp" and effect['buff'].lower() != "dodge"):
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        for char in self.team:
                            char[effect['buff']] = math.ceil(char[effect['buff']] * (((100 - effect['buff_amount']) / 100)))

                    # changes the state if it's dodge
                    elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "dodge":
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        self.state['user']['can_dodge'] = False

                    # removes the hp buff because its a one time use
                    elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "hp":
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                    
                    effect['turn_duration'] -= 1

                                    
                

       
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the duration of the item effect on line {line_num}")

    # Creates the buttons for the users to press
    def create_character_buttons(self, team):
        try:
            self.view.clear_items()

            # Creates the fighter buttons for the user to choose from
            for char in team:
                if char["class"] != "Support" and char["current_hp"] > 0:
                    button = RaidFighterButton(label=char["name"], character=char, raid=self)
                    button.callback = button.on_button_click
                    self.view.add_item(button)
                    button.raid = self

            # Checks to see if it's the user's turn and gives them the option to use an item
            if self.turn == 'user':
                button = RaidItemButton(label="Items", raid=self)
                button.callback = button.on_button_click
                self.view.add_item(button)
                button.raid = self

            return self.view
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating character buttons for a raid on {line_num}")
    
    # Returns a list of the enemies that will be generated
    def get_enemies(self):
        try:
            possible_enemies_list = []
            enemies_list = []

            # Determines the stats and amount of enemies based on the current raid level
            enemy_setup_dictionary = {
                5: {"rarity": "Common",
                    "number_of_enemies": 5,
                    "stat_multiplier": {
                        "HP": 1,
                        "ATK": 2,
                        "SPD": 2,
                    }},

                10: {"rarity": "Rare",
                    "number_of_enemies": 4,
                    "stat_multiplier": {
                        "HP": 5,
                        "ATK": 3,
                        "SPD": 3
                    }},

                15: {"rarity": "Epic",
                    "number_of_enemies": 3,
                    "stat_multiplier": {
                        "HP": 10,
                        "ATK": 4,
                        "SPD": 4
                    }},

                20:  {"rarity": "Legendary",
                    "number_of_enemies": 2,
                    "stat_multiplier": {
                        "HP": 15,
                        "ATK": 5,
                        "SPD": 5
                    }},
            }

            threshold = math.ceil(float(self.level) / 5) * 5

            if threshold > 20:
                threshold = 20
            
            # Gets a list of all the characters who correspond to the rarity
            possible_enemies = database_handler.all_characters.find({"rarity": enemy_setup_dictionary[threshold]["rarity"], "class": { "$ne": "Support" }})

            for character in possible_enemies:
                possible_enemies_list.append(character)
            
            # Slightly randomizes the stats of the enemies
            for i in range(enemy_setup_dictionary[threshold]["number_of_enemies"]):
                random_num = random.randint(0, (len(possible_enemies_list) - 1))
                enemy = copy.deepcopy(possible_enemies_list[random_num])
                
                if enemy.get("crit_chance", None) is not None:
                    enemy["crit_chance"] = random.randint(round(enemy["crit_chance"]*2*0.8), round(enemy["crit_chance"]*2*1.2))
                elif enemy.get("reflect_chance", None) is not None:
                    enemy["reflect_chance"] = random.randint(round(enemy["reflect_chance"]*2*0.8), round(enemy["reflect_chance"]*2*1.2))
                elif enemy.get("stun_chance", None) is not None:
                    enemy["stun_chance"] = random.randint(round(enemy["stun_chance"]*2*0.8), round(enemy["stun_chance"]*2*1.2))

                enemy["HP"] = random.randint(round(enemy["HP"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["HP"]*0.8), round(enemy["HP"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["HP"]*1.2))
                enemy["ATK"] = random.randint(round(enemy["ATK"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["ATK"]*0.8), round(enemy["ATK"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["ATK"]*1.2))
                enemy["SPD"] = random.randint(round(enemy["SPD"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["SPD"]*0.8), round(enemy["SPD"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["SPD"]*1.2))
                enemy["current_hp"] = enemy["HP"]

                enemies_list.append(enemy)
            
            return enemies_list
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating enemies at the start of the round for a raid on line {line_num}.")

    # Creates an embed displaying the current fight information
    def create_embed(self):
        try:
            combat_log = self.combat_log
            embed = discord.Embed(description=f"Current Level: **{self.level}**\nCurrent Round: **{self.round}**")

            embed.set_author(name=f"----------- {self.ctx.author} is currently in a raid -----------")

            embed.add_field(name=f"{self.ctx.author}'s Team",
                    value=self.format_team(team=self.team),
                    inline=True)
            embed.add_field(name="Defenders",
                    value=self.format_team(team=self.enemies),
                    inline=True)
            
            embed.add_field(
                name="Combat Log",
                value="\n".join(f"- {line}" for line in combat_log),
                inline=False,
            )

            embed.set_thumbnail(url=self.ctx.author.display_avatar)

            return embed
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating an embed for the raid display on line {line_num}")
        
    # Displays the health bar of the character
    def display_health_bar(self, current_hp, max_hp):
        try:
            health_bars = [
                "[HP ▸ ▐──────────▌]",
                "[HP ▸ ▐█─────────▌]",
                "[HP ▸ ▐██────────▌]",
                "[HP ▸ ▐███───────▌]",
                "[HP ▸ ▐████──────▌]",
                "[HP ▸ ▐█████─────▌]",
                "[HP ▸ ▐██████────▌]",
                "[HP ▸ ▐███████───▌]",
                "[HP ▸ ▐████████──▌]",
                "[HP ▸ ▐█████████─▌]",
                "[HP ▸ ▐██████████▌]",
            ]
            index = math.floor((current_hp / max_hp) * 10)
            return(health_bars[index])
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when getting the health bars during the raid on line {line_num}.")

    # Formats the team in into a string
    def format_team(self, team):
        try:
            return "\n".join(
                [
                    f"**{char['emoji']} {char['name']}**\n`{self.display_health_bar(char['current_hp'], char['HP'])}\n▸ {char['current_hp']} / {char["HP"]}`\n`ATK ▸ {char['ATK']}`\n`SPD ▸ {char['SPD']}`\n"
                    for char in team
                    if char["class"] != "Support"
                ]
            )
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when formatting the team string for a raid on line {line_num}.")
 
    # Determines whether the effect is cast and on to who if necessary
    def process_effect(self, character, effect, target_key):
        try:
            if effect is not None and character.get(effect["stat"]) is not None:
                # Runs if the character has a support character that supports its stats
            
                chance = character[effect["stat"]] + effect["amount"]
                if random.randint(1, 100) < chance:

                    if effect["stat"] == "stun_chance":
                        self.combat_log.append(
                            f"{character['name']} has unleashed an attack, powerful enough to stun the whole team for two turns!"
                        )
                        self.state[target_key]["stunned"] = True
                        self.state[target_key]["stun_timer"] = 2
                        update_quests(user_id=self.ctx.author.id, quest_id="stun_one_character", amount=1)

                    elif effect["stat"] == "crit_chance":
                        self.state["user" if target_key == "enemy" else "enemy"]["crits"] = True
                    elif effect["stat"] == "reflect_chance":
                        self.state["user" if target_key == "enemy" else "enemy"]["reflects"] = True
            elif effect is None:
                # Runs if the character doesn't have a support character
                chance = (
                    character.get("crit_chance", None)
                    or character.get("stun_chance", None)
                    or character.get("reflect_chance", None)
                )

                if random.randint(1, 100) < chance:
                    if character.get("stun_chance", None) is not None:
                        self.combat_log.append(
                            f"{character['name']} has unleashed an attack, powerful enough to stun the whole team for two turns!"
                        )
                        self.state[target_key]["stunned"] = True
                        self.state[target_key]["stun_timer"] = 2
                        update_quests(user_id=self.ctx.author.id, quest_id="stun_one_character", amount=1)

                    elif character.get("crit_chance", None) is not None:
                        self.state["user" if target_key == "enemy" else "enemy"]["crits"] = True
                    elif character.get("reflect_chance", None) is not None:
                        self.state["user" if target_key == "enemy" else "enemy"]["reflects"] = True
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating processing the effect: {effect["stat"]} for {character['name']} in a raid in line {line_num}.")

    # Calculates the rewards you get from that level
    def calculate_level_rewards(self):
        try:
            rewards_dictionary = {
                5: {
                    "raid_token": 30,
                    "standard_ticket": 30,
                    "limited_ticket": 10,
                    "ev_stone": 10,
                    "white_shirt": 5,
                    "broken_sunglasses": 20,
                    "boxing_gloves": 10,
                    "biker_helmet": 25,
                    "leather_jacket": 100
                    },

                10: {                
                    "raid_token": 40,
                    "standard_ticket": 30,
                    "limited_ticket": 20,
                    "ev_stone": 10,
                    "white_shirt": 10,
                    "broken_sunglasses": 25,
                    "boxing_gloves": 15,
                    "biker_helmet": 30,
                    "leather_jacket": 20
                    },

                15: {
                    "raid_token": 50,
                    "standard_ticket": 40,
                    "limited_ticket": 25,
                    "xp_booster": 5,
                    "won_booster": 5,
                    "ev_stone": 10,
                    "white_shirt": 15,
                    "broken_sunglasses": 30,
                    "boxing_gloves": 20,
                    "biker_helmet": 35,
                    "leather_jacket": 25
                },

                20:  {
                    "raid_token": 60,
                    "standard_ticket": 50,
                    "limited_ticket": 30,
                    "xp_booster": 10,
                    "won_booster": 10,
                    "ev_stone": 15,
                    "white_shirt": 20,
                    "broken_sunglasses": 35,
                    "boxing_gloves": 25,
                    "biker_helmet": 40,
                    "leather_jacket": 30
                },
            }

            threshold = math.ceil(float(self.level) / 5) * 5

            if threshold > 20:
                threshold = 20

            # Rolls a random number for each item in the rewards dictionary to see if
            # the user gets the item
            for item, percentage in rewards_dictionary[threshold].items():
                random_num = random.randint(1, 100)
                if percentage >= random_num:
                    excess_round_attempts = math.fabs(self.round - len(self.enemies))
                    range_of_rewards = 4

                    # Determines the number of rewards based on how fast the round is completed
                    if excess_round_attempts > 5:
                        range_of_rewards = 1
                    elif excess_round_attempts <= 5:
                        range_of_rewards = 2
                    elif excess_round_attempts <= 2:
                        range_of_rewards = 3
                    
                    if self.player_rewards.get(item) is None:
                        self.player_rewards[item] = 0
                    
                    self.player_rewards[item] += random.randint(1, range_of_rewards) 
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when calculating the level rewards for a raid on line {line_num}")
       
    # Checks whether either play has won
    async def check_raid_end(self, interaction):
        try:
            dead_characters = 0
            fighter_characters = [char for char in self.team if char["class"] != "Support"]

            # Counts the number of dead characters
            for char in fighter_characters:
                if char["current_hp"] <= 0:
                    char["current_hp"] = 0
                    dead_characters += 1


            if dead_characters == len(fighter_characters):
                # Creates the final embed for the fight
                embed = self.create_embed()

                await interaction.response.edit_message(embed = embed, view = None)

                # Updates the raid level and removes the user from being in the raid state
                if self.level > database_handler.users.find_one({"_id": interaction.user.id}).get("raid_level"):
                    database_handler.users.update_one({"_id": self.ctx.author.id}, {"$set": {"raid_level": self.level}})
                
                database_handler.users.update_one({"_id": self.ctx.author.id}, {"$set": {"in_raid": False}})


                # Creates an embed displaying end of raid stats
                embed = discord.Embed(title="------------------- The raid is over! ------------------")

                embed.add_field(name="Stats",
                    value=f"Final Level: **{self.level}**\nNumber of Rounds: **{self.round}**",
                    inline=False)
                embed.add_field(name="-------------------------------------------------------------------",
                    value="",
                    inline=False)

                # Sets the starting payout based on level
                if self.level > 20:
                    xp_starting_payout = 2500
                elif self.level > 15:
                    xp_starting_payout = 2000
                elif self.level > 10:
                    xp_starting_payout = 1500
                elif self.level > 5:
                    xp_starting_payout = 1000
                else:
                    xp_starting_payout = 500

                # Gives each character XP based on whether they completed a level or not
                for char in fighter_characters:
                    if (self.level - self.starting_level) > 0:
                        xp_payout = random.randint(xp_starting_payout, xp_starting_payout + 1000) * check_boosts(user_id=self.ctx.author.id, type="xp_booster")
                    else:
                        xp_payout = 0

                    embed.add_field(name="",
                        value=f"{char["name"]} has received {xp_payout} XP! Their current XP amount is now `{database_handler.increment_character_xp(user_id=self.ctx.author.id, xp=xp_payout, character=char["name"], return_xp=True)}/2000`",
                        inline=False)
        
                embed.add_field(name="-------------------------------------------------------------------",
                    value="",
                    inline=False)
                
                # Display the rewards accumulated from the raid here
                embed.add_field(name="Rewards",
                    value=f"You have received the following rewards: \n{"\n".join([f"`{reward.replace("_", " ").title().replace("Xp", "XP")}`: {amount}" for reward, amount in self.player_rewards.items()])}",
                    inline=False)
                
                user_profile = database_handler.users.find_one({"_id": self.ctx.author.id})
                user_inventory = user_profile.get("inventory")
                
                for reward, amount in self.player_rewards.items():
                    reward_given = False
                    for item in user_inventory:
                        try:
                            if reward == item:
                                database_handler.inc_value_to_users(user_id=interaction.user.id, key=f"inventory.{reward}.amount", value=amount)
                                reward_given = True
                        except Exception as e:
                            create_error_embed(error=e, ctx=self.ctx)
                    
                    if not reward_given:
                        database_handler.add_item(user_id=self.ctx.author.id, item=reward)
                        database_handler.inc_value_to_users(user_id=self.ctx.author.id, key=f"inventory.{reward}.amount", value=amount)

                embed.set_thumbnail(url=self.ctx.author.display_avatar)

                embed.set_footer(text="The fewer rounds it takes to complete a level, the more rewards you get!")

                await self.ctx.send(embed=embed)
                update_quests(user_id=self.ctx.author.id, quest_id="complete_one_raid", amount=1)

                return True 

            return False
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the end of a raid on line {line_num}")

    # Checks whether the player has defeated all the characters on the level
    def check_level_end(self):
        try:
            dead_characters = 0
            
            # Checks to see if all the enemies are dead
            for char in self.enemies:
                if char["current_hp"] <= 0:
                    dead_characters += 1

            if dead_characters == len(self.enemies):
                # Adds rewards to the rewards dictionary for completing the level
                self.calculate_level_rewards()

                if self.round < 10:
                    update_quests(user_id=self.ctx.author.id, quest_id="complete_in_ten_rounds", amount=1)

                # Resets the level
                self.level += 1
                self.round = 1
                self.enemies = self.get_enemies()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the end of the level for a raid on line {line_num}")

    # Applys the effects determined by the process_effect function
    def apply_effects(self):
        try:
            # Gets player support characters
            user_support = next(
                (c for c in self.team if c["class"] == "Support"), None
            )

            # Checks to see if character has a support character and is not stunned
            if user_support and not self.state["user"]["stunned"]:
                effect_processed = False
                for i, effect in enumerate(user_support["effects"]):
                    if effect['stat'] != "crit_chance" and effect['stat'] != "stun_chance" and effect['stat'] != "reflect_chance":
                        continue
                    
                    self.process_effect(
                        character=self.user_character, effect=user_support["effects"][i], target_key="enemy"
                        )
                    effect_processed = True
                    
                if not effect_processed:
                    self.process_effect(character=self.user_character, effect=None, target_key="enemy")


                        
            elif not self.state["user"]["stunned"]:
                # Checks to see if the character isn't stunned
                self.process_effect(character=self.user_character, effect=None, target_key="enemy")

            # Checks to see if character has a support character and is not stunned
            if not self.state["enemy"]["stunned"]:
                # Checks to see if the character isn't stunned
                self.process_effect(character=self.enemy_character, effect=None, target_key="user")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying effects to characters during a raid on line {line_num}")

    # Handles the attack for each of the characters
    def handle_attack(self, attacker, defender, attacker_key):
        try:
            # Checks to see if the attacker is stunned
            if self.state[attacker_key]["stunned"]:
                self.combat_log.append(
                    f"{attacker['name']} is stunned for {self.state[attacker_key]['stun_timer']} turn(s) and can't attack."
                )
                return 0
            

            if attacker["current_hp"] <= 0:
                return

            # Returns a random number between a small range from the flat ATK
            damage = random.randrange(
                round(0.8 * attacker["ATK"]), round(1.2 * attacker["ATK"])
            )

            # Checks to see if the character should crit or not
            if self.state[attacker_key]["crits"]:
                damage *= attacker["crit_damage"]
                self.combat_log.append(
                    f"{attacker['name']} lands a **CRITICAL HIT** for {round(damage)}!"
                )
                if attacker_key == "user":
                    update_quests(user_id=self.ctx.author.id, quest_id="crit_one_character", amount=1)

            else:
                self.combat_log.append(
                    f"{attacker['name']} lands a hit for {damage} damage."
                )
            
            # Checks to see if the defender can dodge the attack
            if attacker_key == "enemy" and self.state['user']['can_dodge']:
                self.combat_log.append(
                    f"{defender['name']} dodged the attacked!"
                )
                return 0

            defender["current_hp"] -= int(round(damage))

            if defender["current_hp"] <= 0:
                defender["current_hp"] = 0
                self.combat_log.append(f"{defender['name']} has died!")
            
            return damage
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when handling the attack for a raid in line {line_num}")

    # Checks to see whether damage should be reflected by the character
    def handle_reflect(self, attacker, defender, attacker_key, defender_key, damage):
        try: 
            # Checks to see if the defender can dodge the attack
            if attacker_key == "enemy" and self.state['user']['can_dodge']:
                return 

            if (
                self.state[attacker_key]["reflects"]
                and not self.state[attacker_key]["stunned"]
                and not self.state[defender_key]["stunned"]
                and attacker["current_hp"] > 0
                and defender["current_hp"] > 0
            ):
                reflect_percent = attacker["reflect_percent"] / 100
                reflect_damage = round(reflect_percent * damage)
                self.combat_log.append(
                    f"{attacker['name']} reflects {reflect_damage} damage back to {defender['name']}!"
                )
                if attacker_key == "user":
                    update_quests(user_id=self.ctx.author.id, quest_id="reflect_one_character", amount=1)

                defender["current_hp"] -= reflect_damage
                if defender["current_hp"] <= 0:
                    self.combat_log.append(f"{defender['name']} has died!")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when handling the reflection for such characters in a raid on line {line_num}")

    # Determines the amount of damage to be taken then resets the turn
    def determine_final_damage(self):
        try:
            # Applies the support effects on to user characters
            self.apply_effects()

            user_speed = self.user_character.get("SPD")
            enemy_speed = self.enemy_character.get("SPD")

            # Checks to see who attacked first
            if user_speed >= enemy_speed:
                if not self.state["user"]["stunned"]:
                    self.combat_log.append(f"**{self.user_character['name']} attacked before {self.enemy_character['name']} could even blink!**"   )
                else:
                    self.combat_log.append(f"**{self.enemy_character['name']} takes advantage of {self.user_character['name']}'s stunned state and attacks!**"   )  
                
                user_damage = self.handle_attack(self.user_character, self.enemy_character, "user")
                enemy_damage = self.handle_attack(self.enemy_character, self.user_character, "enemy")

                self.handle_reflect(self.user_character,self.enemy_character,"user","enemy", enemy_damage,)
                self.handle_reflect(self.enemy_character,self.user_character,"enemy","user",user_damage,)


            elif user_speed < enemy_speed:
                if not self.state["enemy"]["stunned"]:
                    self.combat_log.append(f"**{self.enemy_character['name']} attacked before {self.user_character['name']} could even blink!**"   )
                else:
                    self.combat_log.append(f"**{self.user_character['name']} takes advantage of {self.enemy_character['name']}'s stunned state and attacks!**"   )  
               
                enemy_damage = self.handle_attack(self.enemy_character, self.user_character, "enemy")
                user_damage = self.handle_attack(self.user_character, self.enemy_character, "user")
                
                self.handle_reflect(self.enemy_character,self.user_character,"enemy","user", user_damage,)
                self.handle_reflect(self.user_character,self.enemy_character,"user","enemy", enemy_damage,)

            self.check_item_boost_duration()
            self.reset_round()


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when determining the final damage in a raid on line {line_num}")

    # Resets the round to prepare for the next turn
    def reset_round(self):
        try:
            self.round += 1
            for key in ["user", "enemy"]:
                self.state[key]["crits"] = False
                self.state[key]["reflects"] = False
                
                if self.state[key]["stun_timer"] == 1:
                    self.state[key]["stunned"] = False
                else:
                    self.state[key]["stun_timer"] -= 1
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when resetting the round for each round in line {line_num}")
    
# Creates the view where the buttons are held
class RaidView(discord.ui.View):
    def __init__(self, ctx, raid):
        super().__init__()
        self.timeout = 30.0
        self.ctx = ctx
        self.raid = raid

    # Checks to make sure only the specified user can press the button
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            if interaction.user != self.raid.ctx.author:
                await interaction.response.send_message(
                    "Only the author of the command can use this.", ephemeral=True
                )
                return False
            
            return True
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking who is interacting with the raid view in line {line_num}")
    
    # Stops the game when timed out
    async def on_timeout(self):
        try:
            if self.raid.send_timeout_message:
                await self.ctx.send("Quitting mid fight? Come back again when you're serious.")
            database_handler.users.update_one({"_id": self.raid.ctx.author.id}, {"$set": {"in_raid": False}})
            return await super().on_timeout()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when running the on timeout function for the raid view in line {line_num}")
        


import discord
import math
import copy
import random
import sys
from utils.utility_functions import check_boosts, update_quests, create_error_embed
from utils.buttons import GameFighterButton, GameItemButton
import handlers.database_handler as database_handler

# MAKE RAIDS AND GAME MORE CONSISTENT

class GameInstance:
    # Initializes all the information needed throughout the game
    def __init__(self, ctx, bot, game_type):
        self.ctx = ctx
        self.bot = bot
        self.turn = "team_1"
        self.send_timeout_message = True
        self.view = FighterView(ctx=ctx, game=self)
        self.combat_log = []
        self.game_type = game_type

        self.player_one_team = None
        self.player_two_team = None

        self.player_one_character = None
        self.player_two_character = None

        self.p1_items_in_use = []
        self.p1_num_of_items_used = 0

        # Different states of the characters
        self.team_states = {
            "team_1": {
            },
            "team_2": {
            },
        }

    def initalize_character_states(self, is_start_of_game = False):
        player_one_team = [char for char in self.player_one_team if char['class'] != "Support"]
        player_two_team = [char for char in self.player_two_team if char['class'] != "Support"]

        if is_start_of_game:
            for char in player_one_team:
                self.team_states['team_1'][char['name']] = {
                        "can_dodge": False,
                        "dodge_timer": 0,
                        "stunned": False,
                        "stun_timer": 0,
                        "can_crit": False
                    }
        
        for char in player_two_team:
            self.team_states['team_2'][char['name']] = {
                    "can_dodge": False,
                    "dodge_timer": 0,
                    "stunned": False,
                    "stun_timer": 0,
                    "can_crit": False
                }
            
    # YES Applys stat boost for entire team if applicable 
    def apply_stat_boosts(self):
        try:
            player_one_support = next((c for c in self.player_one_team if c["class"] == "Support"), None)
            player_two_support = next((c for c in self.player_two_team if c["class"] == "Support"), None)

            if player_one_support:
                player_one_fighter_characters = [c for c in self.player_one_team if c["class"] != "Support"]
        
                for effect in player_one_support["effects"]:
                    if effect["stat"] == "SPD" or effect["stat"] == "ATK":
                        for char in player_one_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                    elif effect["stat"] == "HP":
                        for char in player_one_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                            char["current_hp"] = char[effect["stat"]]

            if player_two_support:
                player_two_fighter_characters = [c for c in self.player_two_team if c["class"] != "Support"]

                for effect in player_two_support["effects"]:
                    if effect["stat"] == "SPD" or effect["stat"] == "ATK":
                        for char in player_two_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                    elif effect["stat"] == "HP":
                        for char in player_two_fighter_characters:
                            char[effect["stat"]] = round(char[effect["stat"]] * (1 + (effect["amount"] / 100)))
                            char["current_hp"] = char[effect["stat"]]

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() 
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying stat boosts in a challenge on line {line_num}")

    # YES Applys item stat boosts
    def apply_item_boosts(self, item):
        try:
            team = self.player_one_team if self.turn == "team_1" else self.player_two_team

            # Gets the info inside of the item
            item = item[f"{list(item.keys())[0]}"]
            for effect in item.get('effects'):
                # Checks what stat the item will be boosting and boosts the stats accordingly
                if effect['buff'].lower() == "hp":
                    for char in team:
                        if char['class'] != "Support":
                            char['current_hp'] = math.ceil(char['current_hp'] * (1 + (effect['buff_amount'] / 100)))
                            
                            if char['current_hp'] > char['HP']:
                                char['current_hp'] = char['HP']

                else:
                    for char in self.player_one_team:
                        if char['class'] != "Support":
                            char[effect['buff']] = math.ceil(char[effect['buff']] * (1 + (effect['buff_amount'] / 100)))


            if self.turn == "team_1":
                self.p1_num_of_items_used += 1
            elif self.turn == "team_2":
                self.p2_num_of_items_used += 1


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured while trying to apply an item boost to the team in a challenge on line {line_num}.")

    # YES Checks the duration of the current items:
    def check_item_boost_duration(self, team, items_in_use_list : list):
        try:
            team = self.player_one_team if team == "team_1" else self.player_two_team

            for item in items_in_use_list:
                # Gets the info inside of the item
                item_name = f"{list(item.keys())[0]}"
                item_data = item[item_name]

                if item_data.get('effects') is None:
                   items_in_use_list.remove(item)
                   continue

                for effect in item_data.get('effects').copy():
                    # buffs the stat as long as it isn't dodge or hp
                    if effect['turn_duration'] <= 0 and (effect['buff'].lower() != "hp" and effect['buff'].lower() != "dodge"):
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        for char in team:
                            if char['class'] != "Support":
                                char[effect['buff']] = math.floor(char[effect['buff']] / (1 + (effect['buff_amount'] / 100)))

                    # changes the state if it's dodge
                    elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "dodge":
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))

                        # removes the hp buff because its a one time use
                    elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "hp":
                        item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        
                    effect['turn_duration'] -= 1
                    
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the duration of the item effect for {player_key} on line {line_num}")

    # YES Displays the health bar of the character
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

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the health bars for a challenge on line {line_num}")

    # YES Formats the team in into a string
    def format_team(self, team):
        return "\n".join(
            [
                f"**{char['emoji']} {char['name']}**\n`{self.display_health_bar(char['current_hp'], char['HP'])}\n▸ {char['current_hp']} / {char["HP"]}`\n`ATK ▸ {char['ATK']}`\n`SPD ▸ {char['SPD']}`\n"
                for char in team
                if char["class"] != "Support"
            ]
        )

    # YES Creates the buttons for the users to press
    def create_character_buttons(self, team):
        try:
            self.view.clear_items()
            for char in team:
                if char["class"] != "Support" and char["current_hp"] > 0:
                    button = GameFighterButton(label=char["name"], character=char, game=self)
                    button.callback = button.on_button_click
                    self.view.add_item(button)
                    button.game = self
            
            if (self.game_type == "challenge") or (self.game_type == "raid" and self.turn == "team_1") :
                button = GameItemButton(label="Items", game=self)
                button.callback = button.on_button_click
                self.view.add_item(button)
                button.game = self
            
            return self.view
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating character buttons for a challenge on {line_num}")
    
    # YES Determines whether the effect is cast and on to who if necessary
    def process_support_effect(self, team, support_effect = None):
        try:
            attacking_character = self.player_one_character if team == "team_1" else self.player_two_character

            if self.team_states[team][attacking_character['name']]['stunned']:
                return
            
            chance_of_triggering_effect = int(attacking_character.get("crit_chance") or attacking_character.get("dodge_chance") or attacking_character.get("stun_chance"))

            # Makes sure the support effect actually matches the character effect
            if support_effect is not None and attacking_character.get(support_effect['stat'], None) is not None:
                chance_of_triggering_effect += int(support_effect['amount'])

            random_num = random.randint(0, 100)
            
            if random_num <= chance_of_triggering_effect:
                if attacking_character.get('crit_chance', None) is not None:
                    self.team_states[team][attacking_character['name']]['can_crit'] = True

                elif attacking_character.get('dodge_chance', None) is not None:
                    self.team_states[team][attacking_character['name']]['can_dodge'] = True
                    self.team_states[team][attacking_character['name']]['dodge_timer'] = attacking_character.get('dodge_duration')
                        
                elif attacking_character.get('stun_chance', None) is not None:
                    defending_character = self.player_one_character if attacking_character == self.player_two_character else self.player_two_character
                    
                    self.combat_log.append(f"{attacking_character['name']} is charging up an attack strong enough to stun {defending_character['name']} for {attacking_character['stun_duration']} turn(s)")
                    
                    defending_team = "team_1" if team == "team_2" else "team_2"

                    if self.team_states[defending_team][defending_character['name']]['can_dodge']:
                        return

                    self.team_states[defending_team][defending_character['name']]['stunned'] = True
                    self.team_states[defending_team][defending_character['name']]['stun_timer'] = attacking_character.get('stun_duration')
                
                

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

    # YES Applys the effects determined by the process_effect function
    def apply_support_effects(self, attacking_team):
        try:
            # Gets player support characters
            attacking_team_support = next((c for c in self.player_one_team if c["class"] == "Support"), None) if attacking_team == "team_1" else next((c for c in self.player_two_team if c["class"] == "Support"), None)
            attacking_character = self.player_one_character if attacking_team == "team_1" else self.player_two_character
            effect_processed = False

            if attacking_team_support is None:
                self.process_support_effect(team=attacking_team)
                return
            
            for effect in attacking_team_support.get('effects'):
                if effect['stat'] == "SPD" or effect['stat'] == "ATK" or effect['stat'] == "HP":
                    continue
                
                if attacking_character.get("crit_chance") is not None:
                    character_effect = "crit_chance"
                elif attacking_character.get("dodge_chance") is not None:
                    character_effect = "dodge_chance"
                elif attacking_character.get("stun_chance") is not None:
                    character_effect = "stun_chance"

                if character_effect == effect['stat']:
                    self.process_support_effect(team=attacking_team, support_effect=effect)
                    effect_processed = True
            
            if not effect_processed:
                self.process_support_effect(team=attacking_team)


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying the effects in a challenge on line {line_num}")

    # YES Handles the attack for each of the characters
    def handle_attack(self, attacker, attacking_team):
        try:
            defender = self.player_one_character if attacker == self.player_two_character else self.player_two_character
            
            defending_team = "team_1" if attacking_team == "team_2" else "team_2"

            # Checks to see if the character is stunned
            if self.team_states[attacking_team][attacker['name']]["stunned"] and attacker['current_hp'] > 0:
                self.combat_log.append(f"{attacker['name']} is stunned for {self.team_states[attacking_team][attacker['name']]['stun_timer']} turn(s) and can't attack.")
                return 0

            if attacker["current_hp"] <= 0:
                return

            # Returns a random number between a small range from the flat ATK
            damage = random.randrange(round(0.8 * attacker["ATK"]), round(1.2 * attacker["ATK"]) )

            # Checks to see if the character should crit or not
            if self.team_states[attacking_team][attacker['name']]["can_crit"]:
                damage *= attacker["crit_damage"]

                if attacking_team == "team_1" and self.game_type == "challenge":
                    update_quests(user_id=self.player_one.id, quest_id="crit_one_character", amount=1)
                elif attacking_team == "team_2" and self.game_type == "challenge":
                    update_quests(user_id=self.player_two.id, quest_id="crit_one_character", amount=1)

                self.combat_log.append(f"{attacker['name']} lands a **CRITICAL HIT** for {round(damage)}!")
            else:
                self.combat_log.append(f"{attacker['name']} lands a hit for {damage} damage.")
            
            # Checks to see if the defender can dodge the attack
            if self.team_states[defending_team][defender['name']]['can_dodge'] and not self.team_states[defending_team][defender['name']]['stunned']:
                self.combat_log.append(f"{defender['name']} dodged the attacked!")
                return 0


            defender["current_hp"] -= int(math.ceil(damage))
            
            if defender["current_hp"] <= 0:
                defender["current_hp"] = 0
                self.combat_log.append(f"{defender['name']} has died!")
            return damage
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when handling the attack for {attacking_team} on line {line_num}")

    # YES Determines the amount of damage to be taken then resets the turn
    def determine_final_damage(self):
        try:
            self.check_item_boost_duration(team="team_1", items_in_use_list=self.p1_items_in_use)

            if self.game_type == "challenge":
                self.check_item_boost_duration(team="team_2", items_in_use_list=self.p2_items_in_use)
            
            player_one_speed = self.player_one_character.get("SPD")
            player_two_speed = self.player_two_character.get("SPD")

            if player_one_speed >= player_two_speed:
                self.apply_support_effects(attacking_team = "team_1")
                self.apply_support_effects(attacking_team = "team_2")

                if not self.team_states["team_1"][self.player_one_character['name']]["stunned"]:
                    self.combat_log.append(f"**{self.player_one_character['name']} attacked before {self.player_two_character['name']} could even blink!**")
                else:
                    self.combat_log.append(f"**{self.player_two_character['name']} takes advantage of {self.player_one_character['name']}'s stunned state and attacks!**")  
                
                self.handle_attack(attacker=self.player_one_character, attacking_team="team_1")
                self.handle_attack(attacker=self.player_two_character, attacking_team="team_2")


            elif player_one_speed < player_two_speed:
                self.apply_support_effects(attacking_team = "team_2")
                self.apply_support_effects(attacking_team = "team_1")

                if not self.team_states["team_2"][self.player_two_character['name']]["stunned"]:
                    self.combat_log.append(f"**{self.player_two_character['name']} attacked before {self.player_one_character['name']} could even blink!**")
                else:
                    self.combat_log.append(f"**{self.player_one_character['name']} takes advantage of {self.player_two_character['name']}'s stunned state and attacks!**" )  
                
                self.handle_attack(attacker=self.player_two_character, attacking_team="team_2")
                self.handle_attack(attacker=self.player_one_character, attacking_team="team_1")

            self.reset_round()

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when determining the final damage for a challenge round on line {line_num}")

    # YES Resets the round to prepare for the next turn
    def reset_round(self):
        try:
            self.player_one_character = None
            self.player_two_character = None

            for char in self.player_one_team:
                if char['class'] != "Support":
                    self.team_states["team_1"][char['name']]["can_crit"] = False
                        
                    if self.team_states["team_1"][char['name']]["stun_timer"] <= 1:
                        self.team_states["team_1"][char['name']]["stunned"] = False
                    else:
                        self.team_states["team_1"][char['name']]["stun_timer"] -= 1

                    if self.team_states["team_1"][char['name']]["dodge_timer"] <= 1:
                        self.team_states["team_1"][char['name']]["can_dodge"] = False
                    else:
                        self.team_states["team_1"][char['name']]["dodge_timer"] -= 1
    

            for char in self.player_two_team:
                if char['class'] != "Support":
                    self.team_states["team_2"][char['name']]["can_crit"] = False
                        
                    if self.team_states["team_2"][char['name']]["stun_timer"] <= 1:
                        self.team_states["team_2"][char['name']]["stunned"] = False
                    else:
                        self.team_states["team_2"][char['name']]["stun_timer"] -= 1

                    if self.team_states["team_2"][char['name']]["dodge_timer"] <= 1:
                        self.team_states["team_2"][char['name']]["can_dodge"] = False
                    else:
                         self.team_states["team_2"][char['name']]["dodge_timer"] -= 1

            if self.game_type == "raid":
                self.round += 1
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when resetting the round in a challenge on line {line_num}")


class ChallengeInstance(GameInstance):
    def __init__(self, ctx, bot, player_one, player_two, player_one_team, player_two_team):
        super().__init__(ctx=ctx, bot=bot, game_type="challenge")
                
        self.player_one = player_one
        self.player_two = player_two
        
        self.player_one_team = player_one_team
        self.player_two_team = player_two_team
        
        self.p2_num_of_items_used = 0
        self.p2_items_in_use = []

        self.apply_stat_boosts()
        self.initalize_character_states(is_start_of_game=True)

    # Function to get calculate the probability of player winning
    def elo_probability(self, rating1, rating2):
        # Calculates and returns the expected score
        return 1.0 / (1 + math.pow(10, (rating1 - rating2) / 400.0))
    
    # Gets the correct k constant for the player based on their elo rating
    def k_factor_generator(self, elo):
        if elo < 2100:
            return 32
        elif elo <= 2400:
            return 24
        else:
            return 16

    # Updates the elo of the user and their rank based on their current elo  
    def update_elo_profile(self, elo, user):
        try:
            elo_dictionary = [
                {"min": 2400, "rank": "Amethyst", "boost": 1.25},
                {"min": 2100, "rank": "Diamond", "boost": 1.2},
                {"min": 1800, "rank": "Gold", "boost": 1.15},
                {"min": 1500, "rank": "Silver", "boost": 1.1},
                {"min": 1200, "rank": "Bronze", "boost": 1.05}
            ]

            for item in elo_dictionary:
                if elo > item["min"]:
                    database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.ranking": item["rank"]}})
                    database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.won_booster": item["boost"]}})
                    database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.score": elo}})
                    return

            database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.ranking": "None"}})
            database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.won_booster": 1}})
            database_handler.users.update_one({"_id": user.id}, {"$set": {"elo.score": elo}})
            return
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when updating the elo profile in a challenge on line {line_num}")
 
    # Calculates the elo rating for both players
    def calculate_elo_rating(self, winner, loser):
        try:
            # Gets the current elo rating for both players
            winner_elo = database_handler.users.find_one({"_id": winner.id}).get("elo").get("score")
            loser_elo = database_handler.users.find_one({"_id": loser.id}).get("elo").get("score")

            winner_prob = self.elo_probability(loser_elo, winner_elo)
            loser_prob = self.elo_probability(winner_elo, loser_elo)

            winner_new_elo = round(winner_elo + self.k_factor_generator(winner_elo) * (1 - winner_prob))
            loser_new_elo = round(loser_elo + self.k_factor_generator(loser_elo) * (-loser_prob))

            self.update_elo_profile(elo=winner_new_elo, user=winner)
            self.update_elo_profile(elo=loser_new_elo, user=loser)

            return winner_new_elo, loser_new_elo
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when calculating the elo rating for a challenge on line {line_num}")

    # Creates an embed displaying the current fight information
    def create_embed(self):
        try:
            combat_log = self.combat_log
            embed = discord.Embed(
                title=f"{self.player_one} vs {self.player_two}",
                description="----------------------------------------------------------------",
                colour=discord.Color.dark_magenta(),
            )
            embed.set_author(
                name=f"{self.player_one} and {self.player_two} are fighting!",
                icon_url="https://i.pinimg.com/736x/14/fd/50/14fd509b0c7183202556710d436b9954.jpg",
            )
            embed.add_field(
                name=f"{self.player_one}'s team",
                value=self.format_team(self.player_one_team),
                inline=True,
            )
            embed.add_field(
                name=f"{self.player_two}'s team",
                value=self.format_team(self.player_two_team),
                inline=True,
            )
            embed.add_field(
                name="Combat Log",
                value="\n".join(f"- {line}" for line in combat_log),
                inline=False,
            )
            embed.set_thumbnail(
                url="https://i.pinimg.com/736x/40/4f/29/404f296cd298fb8610e1cd8b85da1db6.jpg"
            )
            return embed
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for a challenge on line {line_num}")

    # Checks whether either player has won
    async def check_player_win(self, team):
        try:
            dead_characters = 0
            fighter_characters = [char for char in team if char["class"] != "Support"]

            # Counts the number of dead characters
            for char in fighter_characters:
                if char["current_hp"] <= 0:
                    char["current_hp"] = 0
                    dead_characters += 1

            # If all characters die on a team, winner and loser is calculated and an embed detailing fight info is sent
            if dead_characters == len(fighter_characters):
                embed = self.create_embed()
                await self.ctx.send(embed = embed)

                database_handler.users.update_one(
                    {"_id": self.player_one.id}, {"$set": {"in_challenge": False}}
                )
                database_handler.users.update_one(
                    {"_id": self.player_two.id}, {"$set": {"in_challenge": False}}
                )

                winning_player = (
                    self.player_one if self.player_one_team != team else self.player_two
                )
                losing_player = (
                    self.player_one if self.player_one_team == team else self.player_two
                )

                winner_elo, loser_elo  = self.calculate_elo_rating(winner=winning_player, loser=losing_player)

                winning_team = (self.player_one_team if self.player_one_team != team else self.player_two_team)

                payout = round(random.randint(500, 1000) * check_boosts(user_id = winning_player.id, type="won_booster"))
                update_quests(user_id=winning_player.id, quest_id="earn_five_thousand_won", amount=payout)

                embed = discord.Embed(
                    title=f"{winning_player} won the fight!",
                    description=f"{winning_player} has received {payout} won for winning this fight.",
                    color= discord.Color.brand_green(),
                )

                embed.set_author(name="The fight has ended!")


                embed.add_field(name="Elo Ratings",
                                value=f"{winning_player}'s ELO Rating: {winner_elo}\n{losing_player}'s ELO Rating: {loser_elo}")

                for char in winning_team:
                    if char["class"] != "Support":
                            xp_win = round(random.randint(300, 700) * check_boosts(user_id = winning_player.id, type="xp_booster"))
                            embed.add_field(
                                name="",
                                value=f"**{char['emoji']} {char['name']}**  has received `{xp_win}` XP for winning. Their current XP level is `{database_handler.increment_character_xp(user_id=winning_player.id, xp=xp_win, character=char["name"], return_xp=True)}/2000`",
                                inline=False,
                            )

                embed.set_thumbnail(url=winning_player.display_avatar)
                embed.set_footer(
                    text="Keep fighting other players to get more XP for your characters!"
                )

                await self.ctx.send(embed=embed)

                database_handler.inc_value_to_users(user_id=winning_player.id, key="economy.won", value=payout)
                database_handler.inc_value_to_users(user_id=winning_player.id, key="wins", value=1)
                database_handler.inc_value_to_users(user_id=losing_player.id, key="losses", value=1)

                update_quests(user_id=winning_player.id, quest_id="win_a_fight", amount=1)

                return True

            return False
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking for a player win in a challenge on line {line_num}")


class RaidInstance(GameInstance):
    def __init__(self, ctx, bot, level, team):
        super().__init__(ctx=ctx, bot=bot, game_type="raid") 

        self.player_rewards = {}
        self.level = level
        self.starting_level = level
        self.round = 1
        
        self.player_one_team = team # User is player one
        self.player_two_team = self.get_enemies() # Enemies are player two

        self.xp_payout = 0
        self.won_payout = 0

        self.apply_stat_boosts()
        self.initalize_character_states(is_start_of_game=True)



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
            
            10: {"rarity": "Common",
                 "number_of_enemies": 5,
                 "stat_multiplier": {
                     "HP": 1.5,
                     "ATK": 2.5,
                     "SPD": 2.5,
                 }},

            15: {"rarity": "Rare",
                 "number_of_enemies": 4,
                 "stat_multiplier": {
                     "HP": 2,
                     "ATK": 2.5,
                     "SPD": 2.5
                 }},

            20: {"rarity": "Rare",
                 "number_of_enemies": 4,
                 "stat_multiplier": {
                     "HP": 2.5,
                     "ATK": 3,
                     "SPD": 3
                 }},

            25: {"rarity": "Epic",
                 "number_of_enemies": 3,
                 "stat_multiplier": {
                     "HP": 2.5,
                     "ATK": 3,
                     "SPD": 3
                 }},
            
            30: {"rarity": "Epic",
                 "number_of_enemies": 3,
                 "stat_multiplier": {
                     "HP": 3,
                     "ATK": 3.5,
                     "SPD": 3.5
                 }},

            35:  {"rarity": "Legendary",
                 "number_of_enemies": 2,
                 "stat_multiplier": {
                     "HP": 3,
                     "ATK": 3.5,
                     "SPD": 3.5
                 }},

            40:  {"rarity": "Legendary",
                 "number_of_enemies": 2,
                 "stat_multiplier": {
                     "HP": 3.5,
                     "ATK": 4,
                     "SPD": 4
                 }},
        }

            threshold = math.ceil(float(self.level) / 5) * 5

            if threshold > 40:
                threshold = 40
            
            # Gets a list of all the characters who correspond to the rarity
            possible_enemies = database_handler.all_characters.find({"rarity": enemy_setup_dictionary[threshold]["rarity"], "class": { "$ne": "Support" }})

            for character in possible_enemies:
                possible_enemies_list.append(character)
            
            # Slightly randomizes the stats of the enemies
            for i in range(enemy_setup_dictionary[threshold]["number_of_enemies"]):
                random_num = random.randint(0, (len(possible_enemies_list) - 1))
                enemy = copy.deepcopy(possible_enemies_list[random_num])
                possible_enemies_list.remove(enemy)
                
                if enemy.get("crit_chance", None) is not None:
                    enemy["crit_chance"] = random.randint(round(enemy["crit_chance"]*2*0.8), round(enemy["crit_chance"]*2*1.2))
                elif enemy.get("dodge_chance", None) is not None:
                    enemy["dodge_chance"] = random.randint(round(enemy["dodge_chance"]*2*0.8), round(enemy["dodge_chance"]*2*1.2))
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
                    value=self.format_team(team=self.player_one_team),
                    inline=True)
            embed.add_field(name="Defenders",
                    value=self.format_team(team=self.player_two_team),
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
   
    # Calculates the rewards you get from that level
    def calculate_level_rewards(self):
        try:
            rewards_dictionary = {
                5: {
                    "raid_token": 30,
                    "standard_ticket": 30,
                    "limited_ticket": 25,
                    "white_shirt": 5,
                    "broken_sunglasses": 35,
                    "boxing_gloves": 15,
                    "biker_helmet": 45,
                    "leather_jacket": 25
                    },

                10: {                
                    "raid_token": 40,
                    "standard_ticket": 30,
                    "limited_ticket": 30,
                    "ev_stone": 20,
                    "white_shirt": 10,
                    "broken_sunglasses": 40,
                    "boxing_gloves": 20,
                    "biker_helmet": 50,
                    "leather_jacket": 30
                    },

                15: {
                    "raid_token": 50,
                    "standard_ticket": 40,
                    "limited_ticket": 35,
                    "xp_booster": 5,
                    "won_booster": 5,
                    "ev_stone": 10,
                    "white_shirt": 15,
                    "broken_sunglasses": 45,
                    "boxing_gloves": 25,
                    "biker_helmet": 55,
                    "leather_jacket": 35
                    },

                20:  {
                    "raid_token": 60,
                    "standard_ticket": 50,
                    "limited_ticket": 40,
                    "xp_booster": 10,
                    "won_booster": 10,
                    "ev_stone": 15,
                    "white_shirt": 20,
                    "broken_sunglasses": 60,
                    "boxing_gloves": 30,
                    "biker_helmet": 60,
                    "leather_jacket": 40
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
                    excess_round_attempts = math.fabs(self.round - len(self.player_two_team))

                    # Determines the number of rewards based on how fast the round is completed
                    if excess_round_attempts > 15:
                        range_of_rewards = 1
                    elif excess_round_attempts > 10:
                        range_of_rewards = 2
                    elif excess_round_attempts > 5:
                        range_of_rewards = 3
                    else:
                        range_of_rewards = 4
                    
                    if self.player_rewards.get(item) is None:
                        self.player_rewards[item] = 0
                    
                    self.player_rewards[item] += range_of_rewards

            if self.level > 20:
                xp_starting_payout = 600
                won_starting_payout = 500
            elif self.level > 15:
                xp_starting_payout = 500
                won_starting_payout = 400
            elif self.level > 10:
                xp_starting_payout = 400
                won_starting_payout = 300
            elif self.level > 5:
                xp_starting_payout = 300
                won_starting_payout = 200
            else:
                xp_starting_payout = 200
                won_starting_payout = 100

            self.xp_payout += random.randint(xp_starting_payout, xp_starting_payout + 100)
            self.won_payout += random.randint(won_starting_payout, won_starting_payout + 100)


        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when calculating the level rewards for a raid on line {line_num}")
    
    # Checks whether either play has won
    async def check_raid_end(self, interaction):
        try:
            dead_characters = 0
            fighter_characters = [char for char in self.player_one_team if char["class"] != "Support"]

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

                # States the won payout
                embed.add_field(name="",
                    value=f"You have received ₩{self.won_payout}!",
                    inline=False)

                # Gives each character XP based on whether they completed a level or not
                for char in fighter_characters:
                    xp_payout = random.randint(self.xp_payout, self.xp_payout + 1000) * check_boosts(user_id=self.ctx.author.id, type="xp_booster")

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
            for char in self.player_two_team:
                if char["current_hp"] <= 0:
                    dead_characters += 1

            if dead_characters == len(self.player_two_team):
                # Adds rewards to the rewards dictionary for completing the level
                self.calculate_level_rewards()

                if self.round < 10:
                    update_quests(user_id=self.ctx.author.id, quest_id="complete_in_ten_rounds", amount=1)

                # Resets the level
                self.level += 1
                self.round = 1

                self.player_two_team = self.get_enemies()
                self.initalize_character_states()
        

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the end of the level for a raid on line {line_num}")


# Creates the view where the buttons are held
class FighterView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__()
        self.timeout = 120.0
        self.ctx = ctx
        self.game = game

    # Checks to make sure only the specified user can press the button
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.game.game_type == "challenge":
            turn = self.game.player_one if self.game.turn == "team_1" else self.game.player_two

            if interaction.user != turn:
                await interaction.response.send_message(
                    "Only the author of the command can use this.", ephemeral=True
                )
                return False
        
            return True
        
        elif self.game.game_type == "raid":
            if interaction.user != self.ctx.author:
                await interaction.response.send_message(
                    "Only the author of the command can use this.", ephemeral=True
                )
                return False
        
            return True

    async def on_timeout(self):
        # Removes the players from the fighting state
        if self.game.send_timeout_message:
            await self.ctx.send("You're taking too long. Try again when you're actually ready to fight.")

        if self.game.game_type == "challenge":
            database_handler.users.update_one({"_id": self.game.player_one.id}, {"$set": {"in_challenge": False}})
            database_handler.users.update_one({"_id": self.game.player_two.id}, {"$set": {"in_challenge": False}})
        elif self.game.game_type == "raid":
            database_handler.users.update_one({"_id": self.game.ctx.author.id}, {"$set": {"in_raid": False}})
            database_handler.inc_value_to_users(user_id=self.game.ctx.author.id, key="inventory.raid_token.amount", value=1)

        for child in self.children:
            child.disabled = True

        return await super().on_timeout()
    

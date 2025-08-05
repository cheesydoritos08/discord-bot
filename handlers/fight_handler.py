import discord
import math
import random
import sys
from utils.utility_functions import check_boosts, update_quests, create_error_embed
from utils.buttons import FighterButton, ChallengeItemButton
import handlers.database_handler as database_handler


class GameInstance:
    # Initializes all the information needed throughout the game
    def __init__(self, ctx, player_one, player_two, player_one_team, player_two_team, bot):
        self.ctx = ctx
        self.bot = bot
        self.player_one, self.player_two = player_one, player_two
        self.player_one_team, self.player_two_team = player_one_team, player_two_team
        self.turn = player_one
        self.send_timeout_message = True
        self.view = FighterView(ctx=self.ctx, game=self)
        self.combat_log = []
        self.p1_num_of_items_used = 0
        self.p2_num_of_items_used = 0
        self.p1_items_in_use = []
        self.p2_items_in_use = []


        self.player_one_character = None
        self.player_two_character = None

        # Different states of the characters
        self.state = {
            "p1": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
                "can_dodge": False
            },
            "p2": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
                "can_dodge": False
            },
        }

        self.apply_stat_boosts()

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

    # Applys stat boost for entire team if applicable
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
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying stat boosts in a challenge on line {line_num}")

    # Applys item stat boosts
    def apply_item_boosts(self, item, player_key):
        try:
            if player_key == "p1":
                # Gets the info inside of the item
                item = item[f"{list(item.keys())[0]}"]
                for effect in item.get('effects'):
                    # Checks what stat the item will be boosting and boosts the stats accordingly
                    if effect['buff'].lower() == "hp":
                        for char in self.player_one_team:
                            if char['class'] != "Support":
                                char['current_hp'] = math.ceil(char['current_hp'] * (1 + (effect['buff_amount'] / 100)))
                            
                                if char['current_hp'] > char['HP']:
                                    char['current_hp'] = char['HP']

                    elif effect['buff'].lower() == "dodge":
                        self.state[player_key]['can_dodge'] = True

                    else:
                        for char in self.player_one_team:
                            if char['class'] != "Support":
                                char[effect['buff']] = math.floor(char[effect['buff']] * (1 + (effect['buff_amount'] / 100)))

                self.p1_num_of_items_used += 1



            elif player_key == "p2":
                # Gets the info inside of the item
                item = item[f"{list(item.keys())[0]}"]
                for effect in item.get('effects'):
                    # Checks what stat the item will be boosting and boosts the stats accordingly
                    if effect['buff'].lower() == "hp":
                        for char in self.player_two_team:
                            if char['class'] != "Support":
                                char['current_hp'] = math.ceil(char['current_hp'] * (1 + (effect['buff_amount'] / 100)))
                                
                                if char['current_hp'] > char['HP']:
                                    char['current_hp'] = char['HP']

                    elif effect['buff'].lower() == "dodge":
                        self.state[player_key]['can_dodge'] = True

                    else:
                        for char in self.player_two_team:
                            if char['class'] != "Support":
                                char[effect['buff']] = math.floor(char[effect['buff']] * (1 + (effect['buff_amount'] / 100)))

                self.p2_num_of_items_used += 1      



        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured while trying to apply an item boost to the team in a challenge on line {line_num}.")

    # Checks the duration of the current items:
    def check_item_boost_duration(self, player_key):
        try:
            if player_key == "p1":
                for item in self.p1_items_in_use:
                    # Gets the info inside of the item
                    item_name = f"{list(item.keys())[0]}"
                    item_data = item[item_name]

                    if item_data.get('effects') is None:
                        self.p1_items_in_use.remove(item)
                        continue

                    for effect in item_data.get('effects').copy():
                        # buffs the stat as long as it isn't dodge or hp
                        if effect['turn_duration'] <= 0 and (effect['buff'].lower() != "hp" and effect['buff'].lower() != "dodge"):
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                            for char in self.player_one_team:
                                if char['class'] != "Support":
                                    char[effect['buff']] = math.ceil(char[effect['buff']] * (((100 - effect['buff_amount']) / 100)))

                        # changes the state if it's dodge
                        elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "dodge":
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                            self.state[player_key]['can_dodge'] = False

                        # removes the hp buff because its a one time use
                        elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "hp":
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        
                        effect['turn_duration'] -= 1
                    
            
            elif player_key == "p2":
                for item in self.p2_items_in_use:
                    # Gets the info inside of the item
                    item_name = f"{list(item.keys())[0]}"
                    item_data = item[item_name]

                    if item_data.get('effects') is None:
                        self.p2_items_in_use.remove(item)
                        continue

                    for effect in item_data.get('effects').copy():

                        # buffs the stat as long as it isn't dodge or hp
                        if effect['turn_duration'] <= 0 and (effect['buff'].lower() != "hp" and effect['buff'].lower() != "dodge"):
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                            for char in self.player_two_team:
                                char[effect['buff']] = math.ceil(char[effect['buff']] * (((100 - effect['buff_amount']) / 100)))

                        # changes the state if it's dodge
                        elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "dodge":
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                            self.state[player_key]['can_dodge'] = False

                        # removes the hp buff because its a one time use
                        elif effect['turn_duration'] <= 0 and effect['buff'].lower() == "hp":
                            item[item_name]['effects'].pop(item[item_name]['effects'].index(effect))
                        
                        effect['turn_duration'] -= 1

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when checking the duration of the item effect for {player_key} on line {line_num}")

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

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the health bars for a challenge on line {line_num}")

    # Formats the team in into a string
    def format_team(self, team):
        return "\n".join(
            [
                f"**{char['emoji']} {char['name']}**\n`{self.display_health_bar(char['current_hp'], char['HP'])}\n▸ {char['current_hp']} / {char["HP"]}`\n`ATK ▸ {char['ATK']}`\n`SPD ▸ {char['SPD']}`\n"
                for char in team
                if char["class"] != "Support"
            ]
        )

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
            embed.set_footer(text=f"Current turn: {self.turn}")
            return embed
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the embed for a challenge on line {line_num}")

    # Creates the buttons for the users to press
    def create_character_buttons(self, team):
        try:
            self.view.clear_items()

            for char in team:
                if char["class"] != "Support" and char["current_hp"] > 0:
                    button = FighterButton(label=char["name"], character=char, game=self)
                    button.callback = button.on_button_click
                    self.view.add_item(button)
                    button.game = self
            
            button = ChallengeItemButton(label="Items", game=self)
            button.callback = button.on_button_click
            self.view.add_item(button)
            button.game = self
            
            return self.view
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating character buttons for a challenge on {line_num}")
    
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

                        if self.state[target_key]["can_dodge"] == True:
                            other_character = self.player_one_character if character != self.player_one_character else self.player_two_character 
                            self.combat_log.append(f"{other_character['name']} has avoided being stunned")
                            self.state[target_key]["stunned"] = False
                            self.state[target_key]["stun_timer"] = 2
                        
                        if target_key == "p1":
                            update_quests(user_id=self.player_two.id, quest_id="stun_one_character", amount=1)
                        else:
                            update_quests(user_id=self.player_one.id, quest_id="stun_one_character", amount=1)

                    elif effect["stat"] == "crit_chance":
                        self.state["p1" if target_key == "p2" else "p2"]["crits"] = True
                    elif effect["stat"] == "reflect_chance":
                        self.state["p1" if target_key == "p2" else "p2"]["reflects"] = True
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

                        if self.state[target_key]["can_dodge"] == True:
                            other_character = self.player_one_character if character != self.player_one_character else self.player_two_character 
                            self.combat_log.append(f"{other_character['name']} has avoided being stunned")
                            self.state[target_key]["stunned"] = False
                            self.state[target_key]["stun_timer"] = 2


                        if target_key == "p1":
                            update_quests(user_id=self.player_two.id, quest_id="stun_one_character", amount=1)
                        else:
                            update_quests(user_id=self.player_one.id, quest_id="stun_one_character", amount=1)
                            
                    elif character.get("crit_chance", None) is not None:
                        self.state["p1" if target_key == "p2" else "p2"]["crits"] = True
                    else:
                        self.state["p1" if target_key == "p2" else "p2"]["reflects"] = True
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when processing the effect for a character in a challenge on line {line_num}")

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

    # Applys the effects determined by the process_effect function
    def apply_effects(self):
        try:
            # Gets player support characters
            p1_support = next((c for c in self.player_one_team if c["class"] == "Support"), None)
            p2_support = next((c for c in self.player_two_team if c["class"] == "Support"), None)

            # Checks to see if character has a support character and is not stunned
            if p1_support and not self.state["p1"]["stunned"]:
                effect_processed = False
                for i, effect in enumerate(p1_support["effects"]):
                    if effect['stat'] != "crit_chance" and effect['stat'] != "stun_chance" and effect['stat'] != "reflect_chance":
                        continue
                    
                    self.process_effect(character=self.player_one_character, effect=p1_support["effects"][i], target_key="p2")
                    effect_processed = True
                    
                if not effect_processed:
                    self.process_effect(character=self.player_one_character, effect=None, target_key="p2")

            elif not self.state["p1"]["stunned"]:
                # Checks to see if the character isn't stunned
                self.process_effect(self.player_one_character, None, "p2")

            # Checks to see if character has a support character and is not stunned
            if p2_support and not self.state["p2"]["stunned"]:
                effect_processed = False
                for i, effect in enumerate(p2_support["effects"]):
                    if effect['stat'] != "crit_chance" and effect['stat'] != "stun_chance" and effect['stat'] != "reflect_chance":
                        continue
                    
                    self.process_effect(character=self.player_two_character, effect=p2_support["effects"][i], target_key="p1")
                    effect_processed = True
                    
                if not effect_processed:
                    self.process_effect(character=self.player_two_character, effect=None, target_key="p1")

            elif not self.state["p2"]["stunned"]:
                # Checks to see if the character isn't stunned
                self.process_effect(self.player_two_character, None, "p1")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying the effects in a challenge on line {line_num}")

    # Handles the attack for each of the characters
    def handle_attack(self, attacker, defender, attacker_key):
        try:
            # Checks to see if the character is stunned
            if self.state[attacker_key]["stunned"]:
                self.combat_log.append(f"{attacker['name']} is stunned for {self.state[attacker_key]['stun_timer']} turn(s) and can't attack.")
                return 0

            if attacker["current_hp"] <= 0:
                return

            # Returns a random number between a small range from the flat ATK
            damage = random.randrange(round(0.8 * attacker["ATK"]), round(1.2 * attacker["ATK"]) )

            # Checks to see if the character should crit or not
            if self.state[attacker_key]["crits"]:
                damage *= attacker["crit_damage"]
                if attacker_key == "p1":
                    update_quests(user_id=self.player_one.id, quest_id="crit_one_character", amount=1)
                else:
                    update_quests(user_id=self.player_two.id, quest_id="crit_one_character", amount=1)

                self.combat_log.append(
                    f"{attacker['name']} lands a **CRITICAL HIT** for {round(damage)}!"
                )
            else:
                self.combat_log.append(
                    f"{attacker['name']} lands a hit for {damage} damage."
                )
            
            # Checks to see if the defender can dodge the attack
            if attacker_key == "p1" and self.state['p2']['can_dodge'] and not self.state['p2']['stunned']:
                self.combat_log.append(f"{defender['name']} dodged the attacked!")
                return 0
            
            if attacker_key == "p2" and self.state['p1']['can_dodge'] and not self.state['p1']['stunned']:
                self.combat_log.append(f"{defender['name']} dodged the attacked!")
                return 0

            defender["current_hp"] -= int(round(damage))
            
            if defender["current_hp"] <= 0:
                defender["current_hp"] = 0
                self.combat_log.append(f"{defender['name']} has died!")
            return damage
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when handling the attack for {attacker_key} on line {line_num}")

    # Checks to see whether damage should be reflected by the character
    def handle_reflect(self, attacker, defender, attacker_key, defender_key, damage):
        try:
            # Checks to see if the defender can dodge the attack
            if self.state[attacker_key]['can_dodge']:
                return 
            
            if (
                self.state[attacker_key]["reflects"]
                and not self.state[attacker_key]["stunned"]
                and not self.state[defender_key]["stunned"]
                and attacker["current_hp"] > 0
                and defender["current_hp"] > 0
            ):
                # Figure out ehat Xiaalong reflected no damage back to Olly
                reflect_percent = attacker["reflect_percent"] / 100
                reflect_damage = round(reflect_percent * damage)

                self.combat_log.append(
                    f"{attacker['name']} reflects {reflect_damage} damage back to {defender['name']}!"
                )
                if attacker_key == "p1":
                    update_quests(user_id=self.player_one.id, quest_id="reflect_one_character", amount=1)
                else:
                    update_quests(user_id=self.player_two.id, quest_id="reflect_one_character", amount=1)

                defender["current_hp"] -= reflect_damage
                if defender["current_hp"] <= 0:
                    self.combat_log.append(f"{defender['name']} has died!")
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when handling the reflect for {attacker_key} on line {line_num}")

    # Determines the amount of damage to be taken then resets the turn
    def determine_final_damage(self):
        try:
            self.check_item_boost_duration(player_key="p1")
            self.check_item_boost_duration(player_key="p2")
            self.apply_effects()

            player_one_speed = self.player_one_character.get("SPD")
            player_two_speed = self.player_two_character.get("SPD")

            if player_one_speed >= player_two_speed:
                if not self.state["p1"]["stunned"]:
                    self.combat_log.append(f"**{self.player_one_character['name']} attacked before {self.player_two_character['name']} could even blink!**")
                else:
                    self.combat_log.append(f"**{self.player_two_character['name']} takes advantage of {self.player_one_character['name']}'s stunned state and attacks!**")  
                
                damage1 = self.handle_attack(self.player_one_character, self.player_two_character, "p1")
                damage2 = self.handle_attack(self.player_two_character, self.player_one_character, "p2")
                self.handle_reflect(self.player_one_character,self.player_two_character, "p1", "p2", damage2)
                self.handle_reflect(self.player_two_character, self.player_one_character, "p2", "p1", damage1)

            elif player_one_speed < player_two_speed:
                if not self.state["p2"]["stunned"]:
                    self.combat_log.append(f"**{self.player_two_character['name']} attacked before {self.player_one_character['name']} could even blink!**")
                else:
                    self.combat_log.append(f"**{self.player_one_character['name']} takes advantage of {self.player_two_character['name']}'s stunned state and attacks!**" )  
                
                damage1 = self.handle_attack(self.player_two_character, self.player_one_character, "p2" )
                damage2 = self.handle_attack(self.player_one_character, self.player_two_character, "p1")
                self.handle_reflect(self.player_two_character, self.player_one_character, "p2", "p1", damage2)
                self.handle_reflect(self.player_one_character, self.player_two_character, "p1", "p2", damage1)

            self.reset_round()

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when determining the final damage for a challenge round on line {line_num}")

    # Resets the round to prepare for the next turn
    def reset_round(self):
        try:
            self.player_one_character = None
            self.player_two_character = None
            for key in ["p1", "p2"]:
                self.state[key]["crits"] = False
                self.state[key]["reflects"] = False
                if self.state[key]["stun_timer"] == 1:
                    self.state[key]["stunned"] = False
                else:
                    self.state[key]["stun_timer"] -= 1
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when resetting the round in a challenge on line {line_num}")


# Creates the view where the buttons are held
class FighterView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__()
        self.timeout = 30.0
        self.ctx = ctx
        self.game = game

    # Checks to make sure only the specified user can press the button
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.game.turn:
            await interaction.response.send_message(
                "Only the author of the command can use this.", ephemeral=True
            )
            return False
        
        return True
    
    async def on_timeout(self):
        # Removes the players from the fighting state
        if self.game.send_timeout_message:
            await self.ctx.send("You're taking too long. Try again when you're actually ready to fight.")
        database_handler.users.update_one({"_id": self.game.player_one.id}, {"$set": {"in_challenge": False}})
        database_handler.users.update_one({"_id": self.game.player_two.id}, {"$set": {"in_challenge": False}})
        return await super().on_timeout()
    

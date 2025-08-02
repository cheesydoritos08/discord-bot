import discord
import math
import random
from utils.utility_functions import check_boosts, update_quests
from utils.buttons import FighterButton
import handlers.database_handler as database_handler


class GameInstance:
    # Initializes all the information needed throughout the game
    def __init__(self, ctx, player_one, player_two, player_one_team, player_two_team):
        self.ctx = ctx
        self.player_one, self.player_two = player_one, player_two
        self.player_one_team, self.player_two_team = player_one_team, player_two_team
        self.turn = player_one
        self.send_timeout_message = True
        self.view = FighterView(ctx=self.ctx, game=self)
        self.combat_log = []

        self.player_one_character = None
        self.player_two_character = None

        # Different states of the characters
        self.state = {
            "p1": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
            },
            "p2": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
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
    
    # Calculates the elo rating for both players
    def calculate_elo_rating(self, winner, loser):
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

    # Applys stat boost for entire team if applicable
    def apply_stat_boosts(self):
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
    
    # Displays the health bar of the character
    def display_health_bar(self, current_hp, max_hp):
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

    # Creates the buttons for the users to press
    def create_character_buttons(self, team):
        self.view.clear_items()

        for char in team:
            if char["class"] != "Support" and char["current_hp"] > 0:
                button = FighterButton(label=char["name"], character=char, game=self)
                button.callback = button.on_button_click
                self.view.add_item(button)
        
        return self.view

    # Determines whether the effect is cast and on to who if necessary
    def process_effect(self, character, effect, target_key):
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

                    if target_key == "p1":
                        update_quests(user_id=self.player_two.id, quest_id="stun_one_character", amount=1)
                    else:
                        update_quests(user_id=self.player_one.id, quest_id="stun_one_character", amount=1)
                        
                elif character.get("crit_chance", None) is not None:
                    self.state["p1" if target_key == "p2" else "p2"]["crits"] = True
                else:
                    self.state["p1" if target_key == "p2" else "p2"]["reflects"] = True

    # Checks whether either player has won
    async def check_player_win(self, team):
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

            winning_team = (
                self.player_one_team
                if self.player_one_team != team
                else self.player_two_team
            )

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

    # Applys the effects determined by the process_effect function
    def apply_effects(self):
        # Gets player support characters
        p1_support = next(
            (c for c in self.player_one_team if c["class"] == "Support"), None
        )
        p2_support = next(
            (c for c in self.player_two_team if c["class"] == "Support"), None
        )

        # Checks to see if character has a support character and is not stunned
        if p1_support and not self.state["p1"]["stunned"]:
            effect_processed = False
            for i, effect in enumerate(p1_support["effects"]):
                if effect['stat'] != "crit_chance" and effect['stat'] != "stun_chance" and effect['stat'] != "reflect_chance":
                    continue
                
                self.process_effect(
                    character=self.player_one_character, effect=p1_support["effects"][i], target_key="p2"
                    )
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
                
                self.process_effect(
                    character=self.player_two_character, effect=p2_support["effects"][i], target_key="p1"
                    )
                effect_processed = True
                
            if not effect_processed:
                self.process_effect(character=self.player_two_character, effect=None, target_key="p1")

        elif not self.state["p2"]["stunned"]:
            # Checks to see if the character isn't stunned
            self.process_effect(self.player_two_character, None, "p1")

    # Handles the attack for each of the characters
    def handle_attack(self, attacker, defender, attacker_key):
        # Checks to see if the character is stunned
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

        defender["current_hp"] -= int(round(damage))
        if defender["current_hp"] <= 0:
            defender["current_hp"] = 0
            self.combat_log.append(f"{defender['name']} has died!")
        return damage

    # Checks to see whether damage should be reflected by the character
    def handle_reflect(self, attacker, defender, attacker_key, defender_key, damage):
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
            if attacker_key == "p1":
                update_quests(user_id=self.player_one.id, quest_id="reflect_one_character", amount=1)
            else:
                update_quests(user_id=self.player_two.id, quest_id="reflect_one_character", amount=1)

            defender["current_hp"] -= reflect_damage
            if defender["current_hp"] <= 0:
                self.combat_log.append(f"{defender['name']} has died!")

    # Determines the amount of damage to be taken then resets the turn
    def determine_final_damage(self):
        self.combat_log = []
        self.apply_effects()

        player_one_speed = self.player_one_character.get("SPD")
        player_two_speed = self.player_two_character.get("SPD")

        if player_one_speed >= player_two_speed:
            if not self.state["p1"]["stunned"]:
                self.combat_log.append(
                        f"**{self.player_one_character['name']} attacked before {self.player_two_character['name']} could even blink!**"   
                )
            else:
                self.combat_log.append(
                        f"**{self.player_two_character['name']} takes advantage of {self.player_one_character['name']}'s stunned state and attacks!**"   
                )  
            damage1 = self.handle_attack(
                self.player_one_character, self.player_two_character, "p1"
            )
            damage2 = self.handle_attack(
                self.player_two_character, self.player_one_character, "p2"
            )
            self.handle_reflect(
                self.player_one_character,
                self.player_two_character,
                "p1",
                "p2",
                damage2,
            )
            self.handle_reflect(
                self.player_two_character,
                self.player_one_character,
                "p2",
                "p1",
                damage1,
            )

        elif player_one_speed < player_two_speed:
            if not self.state["p2"]["stunned"]:
                self.combat_log.append(
                        f"**{self.player_two_character['name']} attacked before {self.player_one_character['name']} could even blink!**"   
                )
            else:
                self.combat_log.append(
                        f"**{self.player_one_character['name']} takes advantage of {self.player_two_character['name']}'s stunned state and attacks!**"   
                )  
            damage1 = self.handle_attack(
                self.player_two_character, self.player_one_character, "p2"
            )
            damage2 = self.handle_attack(
                self.player_one_character, self.player_two_character, "p1"
            )
            self.handle_reflect(
                self.player_two_character,
                self.player_one_character,
                "p2",
                "p1",
                damage2,
            )
            self.handle_reflect(
                self.player_one_character,
                self.player_two_character,
                "p1",
                "p2",
                damage1,
            )

        self.reset_round()

    # Resets the round to prepare for the next turn
    def reset_round(self):
        self.player_one_character = None
        self.player_two_character = None
        for key in ["p1", "p2"]:
            self.state[key]["crits"] = False
            self.state[key]["reflects"] = False
            if self.state[key]["stun_timer"] == 1:
                self.state[key]["stunned"] = False
            else:
                self.state[key]["stun_timer"] -= 1


# Creates the view where the buttons are held
class FighterView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__()
        self.timeout = 120.0
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
    

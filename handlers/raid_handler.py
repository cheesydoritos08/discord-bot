import math
import copy
import random
import discord
import handlers.database_handler as database_handler
from utils.utility_functions import update_quests, check_boosts, create_error_embed
from utils.buttons import RaidFighterButton, RaidItemButton

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

        self.apply_stat_boosts()

        # Different states of the characters
        self.state = {
            "user": {
                "stunned": False,
                "stun_timer": 0,
                "crits": False,
                "reflects": False,
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

    # Creates the buttons for the users to press
    def create_character_buttons(self, team):
        try:
            self.view.clear_items()
            # view is changed after the button is created, using the unupdated version of the view
            for char in team:
                if char["class"] != "Support" and char["current_hp"] > 0:
                    button = RaidFighterButton(label=char["name"], character=char, raid=self)
                    button.callback = button.on_button_click
                    self.view.add_item(button)
                    button.raid = self


            if self.turn == 'user':
                button = RaidItemButton(label="Items", raid=self)
                button.callback = button.on_button_click
                self.view.add_item(button)
                button.raid = self
                print("create_character_button", self.team)



            return self.view
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when creating character buttons for a raid")
    
    # Returns a list of the enemies that will be generated
    def get_enemies(self):
        try:
            possible_enemies_list = []
            enemies_list = []

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
            
            possible_enemies = database_handler.all_characters.find({"rarity": enemy_setup_dictionary[threshold]["rarity"], "class": { "$ne": "Support" }})

            for character in possible_enemies:
                possible_enemies_list.append(character)
            
            for i in range(enemy_setup_dictionary[threshold]["number_of_enemies"]):
                random_num = random.randint(0, (len(possible_enemies_list) - 1))
                enemy = copy.deepcopy(possible_enemies_list[random_num])
                
                if enemy.get("crit_chance", None) is not None:
                    enemy["crit_chance"] = random.randint(round(enemy["crit_chance"]*2*0.8), round(enemy["crit_chance"]*2*1.2))
                elif enemy.get("reflect_chance", None) is not None:
                    enemy["reflect_chance"] = random.randint(round(enemy["reflect_chance"]*2*0.8), round(enemy["reflect_chance"]*2*1.2))
                elif enemy.get("stun_chance", None) is not None:
                    enemy["stun_chance"] = random.randint(round(enemy["stun_chance"]*0.1*0.8), round(enemy["stun_chance"]*0.1*1.2))

                enemy["HP"] = random.randint(round(enemy["HP"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["HP"]*0.8), round(enemy["HP"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["HP"]*1.2))
                enemy["ATK"] = random.randint(round(enemy["ATK"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["ATK"]*0.8), round(enemy["ATK"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["ATK"]*1.2))
                enemy["SPD"] = random.randint(round(enemy["SPD"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["SPD"]*0.8), round(enemy["SPD"]*enemy_setup_dictionary[threshold]["stat_multiplier"]["SPD"]*1.2))
                enemy["current_hp"] = enemy["HP"]

                enemies_list.append(enemy)
            
            return enemies_list
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when creating enemies at the start of the round for a raid")

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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when creating an embed for the raid display")
        
    # Returns the team formatted in a way to be displayed on the embed
    def format_team(self, team):
        try:
            return "\n".join(
                [
                    f"**⚔️ {char['name']}**\nHP: `{char['current_hp']} / {char['HP']}`\nATK: `{char['ATK']}`\nSPD: `{char['SPD']}`\n"
                    for char in team
                    if char["class"] != "Support"
                ]
            )
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when formatting the team string for a raid")
 
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
            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating processing the effect: {effect["stat"]} for {character['name']} in a raid.")

    # Calculates the rewards you get from that level
    def calculate_level_rewards(self):
        try:
            rewards_dictionary = {
                5: {
                    "raid_token": 30,
                    "standard_ticket": 30,
                    "limited_ticket": 10,
                    "ev_stone": 10
                    },

                10: {                
                    "raid_token": 40,
                    "standard_ticket": 30,
                    "limited_ticket": 20,
                    "ev_stone": 10
                    },

                15: {
                    "raid_token": 50,
                    "standard_ticket": 40,
                    "limited_ticket": 25,
                    "xp_booster": 5,
                    "won_booster": 5,
                    "ev_stone": 10
                },

                20:  {
                    "raid_token": 60,
                    "standard_ticket": 50,
                    "limited_ticket": 30,
                    "xp_booster": 10,
                    "won_booster": 10,
                    "ev_stone": 15
                },
            }

            threshold = math.ceil(float(self.level) / 5) * 5

            if threshold > 20:
                threshold = 20

            for item, percentage in rewards_dictionary[threshold].items():
                random_num = random.randint(1, 100)
                if percentage >= random_num:
                    excess_round_attempts = math.fabs(self.round - len(self.enemies))
                    range_of_rewards = 4

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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when calculating the level rewards for a raid")
            
    # Checks whether either play has won
    async def check_raid_end(self, interaction):
        try:
            dead_characters = 0
            fighter_characters = [char for char in self.team if char["class"] != "Support"]

            for char in fighter_characters:
                if char["current_hp"] <= 0:
                    char["current_hp"] = 0
                    dead_characters += 1

            if dead_characters == len(fighter_characters):
                embed = self.create_embed()

                await interaction.response.edit_message(embed = embed, view = None)

                if self.level > database_handler.users.find_one({"_id": interaction.user.id}).get("raid_level"):
                    database_handler.users.update_one({"_id": self.ctx.author.id}, {"$set": {"raid_level": self.level}})
                
                database_handler.users.update_one({"_id": self.ctx.author.id}, {"$set": {"in_raid": False}})


                embed = discord.Embed(title="------------------- The raid is over! ------------------")

                embed.add_field(name="Stats",
                    value=f"Final Level: **{self.level}**\nNumber of Rounds: **{self.round}**",
                    inline=False)
                embed.add_field(name="-------------------------------------------------------------------",
                    value="",
                    inline=False)
                            
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
                
                # Display the rewards accumulated from the raid here. Below is a placeholder

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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when checking the end of a raid")

    # Checks whether the player has defeated all the characters on the level
    def check_level_end(self):
        try:
            dead_characters = 0

            for char in self.enemies:
                if char["current_hp"] <= 0:
                    dead_characters += 1

            if dead_characters == len(self.enemies):
                self.calculate_level_rewards()

                if self.round < 10:
                    update_quests(user_id=self.ctx.author.id, quest_id="complete_in_ten_rounds", amount=1)

                self.level += 1
                self.round = 1
                self.enemies = self.get_enemies()
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when checking the end of the level for a raid")
        
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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when applying effects to characters during a raid")

    # Handles the attack for each of the characters
    def handle_attack(self, attacker, defender, attacker_key):
        try:
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
                self.combat_log.append(
                    f"{attacker['name']} lands a **CRITICAL HIT** for {round(damage)}!"
                )
                if attacker_key == "user":
                    update_quests(user_id=self.ctx.author.id, quest_id="crit_one_character", amount=1)

            else:
                self.combat_log.append(
                    f"{attacker['name']} lands a hit for {damage} damage."
                )

            print(self.user_character['name'], self.user_character['current_hp'], "Before")
            defender["current_hp"] -= int(round(damage))

            if defender["current_hp"] <= 0:
                defender["current_hp"] = 0
                self.combat_log.append(f"{defender['name']} has died!")
            
            print(self.user_character['name'], self.user_character['current_hp'], "Before")

            return damage
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when handling the attack for each character in the raid")

    # Checks to see whether damage should be reflected by the character
    def handle_reflect(self, attacker, defender, attacker_key, defender_key, damage):
        try:   
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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when handling the reflection for such characters in a raid")

    # Determines the amount of damage to be taken then resets the turn
    def determine_final_damage(self):
        try:
            self.combat_log = []
            self.apply_effects()

            user_speed = self.user_character.get("SPD")
            enemy_speed = self.enemy_character.get("SPD")

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

            self.reset_round()
        except Exception as e:
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when determining the final damage in a raid")

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
            create_error_embed(error=e, ctx=self.ctx, msg="This occured when resetting the round for each round")
    
 

# Creates the view where the buttons are held
class RaidView(discord.ui.View):
    def __init__(self, ctx, raid):
        super().__init__()
        self.timeout = 30.0
        self.ctx = ctx
        self.raid = raid

    # Checks to make sure only the specified user can press the button
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.raid.ctx.author:
            await interaction.response.send_message(
                "Only the author of the command can use this.", ephemeral=True
            )
            return False
        
        return True
    
    # Stops the game when timed out
    async def on_timeout(self):
        if self.raid.send_timeout_message:
            await self.ctx.send("Quitting mid fight? Come back again when you're serious.")
        database_handler.users.update_one({"_id": self.raid.ctx.author.id}, {"$set": {"in_raid": False}})
        return await super().on_timeout()
    


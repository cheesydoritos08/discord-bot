import discord
import math
import random
import handlers.database_handler as database_handler
import sys
from utils.utility_functions import create_error_embed

# Describes how the boss raid works
"""
1. User runs the boss raid command
2. User has to add a character to the boss raid
3. User invites a person to the boss raid
4. Person adds a character to the boss raid. 
6. User starts boss raid
7. The user can either attack, shield for another player, or use an item
8. Each user will choose their action and then turn order is determined by character speed
9. Start off with three bosses that you can end up fighting: Gun Park, Goo Kim, and Kitae Kim
10. Players keep fighting until either they all die or the boss dies


Gun Park Mechanic:
- Two phases: Normal and TUI
- In normal phase, he has regular boss stats 
- In TUI, he has a chance to dodge attacks, his crit chance and crit rate get buffed and he gets a buff to all stats

Goo Mechanic:
- Has three attacks: 
    - Normal one hit
    - Triple attack on one player
    - One hit and a chain attack to other players

Kitae Mechanic:
- Every attack has a chance of applying one of three debuffs:
    - Bleeding: Lose a percentage of HP every turn for a number of turns
    - Dazed: Character speed is decreased to 1 for a number of turns
    - Confused: Decreases the chance of a character landing their special effect for a number of turns
"""





# TODO: when boss raid is done, make sure to check that everyone has the 'in_boss_raid' attribute

class BossRaidInstance:
    def __init__(self, ctx, boss_character, player_one : discord.Member , player_two : discord.Member, player_three : discord.Member, player_one_character, player_two_character, player_three_character):
        # Players for the raid
        self.player_one = player_one
        self.player_two = player_two
        self.player_three = player_three

        # Characters for the raid
        self.player_one_character = player_one_character
        self.player_two_character = player_two_character
        self.player_three_character = player_three_character

        # Boss character stats
        self.boss_character = boss_character
        self.boss_skills = {}

        self.combat_log = []

        self.ctx = ctx

        self.initialize_boss()

    # Creates the boss
    def initialize_boss(self, is_gun_park_second_phase = False):
        try:
            if self.boss_character['name'] == "Goo Kim":
                hp_multiplier = 40
                atk_multiplier = 10
                spd_multiplier = 8

                self.boss_skills = {
                    "Normal Attack": 50,
                    "Multi-hit Attack": 25,
                    "Multi-character Attack": 25
                }
            
            elif self.boss_character['name'] == "Kitae Kim":
                hp_multiplier = 50
                atk_multiplier = 7
                spd_multiplier = 7

                self.boss_skills = {
                    "Normal Attack": 60,
                    "Debuff Attack": 40
                }

            elif self.boss_character['name'] == "Gun Park":
                hp_multiplier = 20
                atk_multiplier = 2
                spd_multiplier = 5

                self.boss_skills = {
                    "Normal Attack": 100,
                }



            if self.boss_character.get("crit_chance", None) is not None:
                self.boss_character["crit_chance"] = random.randint(math.ceil(self.boss_character["crit_chance"] * 2 * 0.8), math.ceil(self.boss_character["crit_chance"] * 2 * 1.2))
            
            elif self.boss_character.get("dodge_chance", None) is not None:
                self.boss_character["dodge_chance"] = random.randint(math.ceil(self.boss_character["dodge_chance"] * 2 * 0.8), math.ceil(self.boss_character["dodge_chance"] * 2 * 1.2))
            
            elif self.boss_character.get("stun_chance", None) is not None:
                self.boss_character["stun_chance"] = random.randint(math.ceil(self.boss_character["stun_chance"] * 2 * 0.8), math.ceil(self.boss_character["stun_chance"] * 2 * 1.2))
            
            # Check to see if it's Gun's second phase and adjust the stats accordingly
            if is_gun_park_second_phase:
                hp_multiplier = 30
                atk_multiplier = 5
                spd_multiplier = 10
                
                self.boss_character["crit_chance"] = random.randint(math.ceil(self.boss_character["crit_chance"] * 3 * 0.8), math.ceil(self.boss_character["crit_chance"] * 3 * 1.2))
                self.boss_character["crit_damage"] = random.randint(math.ceil(self.boss_character["crit_damage"] * 2 * 0.8), math.ceil(self.boss_character["crit_damage"] * 2 * 1.2))

            self.boss_character["HP"] = random.randint(math.ceil(self.boss_character["HP"] * hp_multiplier * 0.8), math.ceil(self.boss_character["HP"] * hp_multiplier * 1.2))
            self.boss_character["ATK"] = random.randint(math.ceil(self.boss_character["ATK"] * atk_multiplier * 0.8), math.ceil(self.boss_character["ATK"]* atk_multiplier * 1.2))
            self.boss_character["SPD"] = random.randint(math.ceil(self.boss_character["SPD"]* spd_multiplier * 0.8), math.ceil(self.boss_character["SPD"]* spd_multiplier * 1.2))
            
            self.boss_character["current_hp"] = self.boss_character["HP"]

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when initalizing the boss for the boss raid on line {line_num}")
   

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

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating the health bars for a boss raid on line {line_num}")

    # Formats the team in into a string
    def format_team(self, team):
        return "\n".join(
            [
                f"**{char['emoji']} {char['name']}**\n`{self.display_health_bar(char['current_hp'], char['HP'])}\n▸ {char['current_hp']} / {char["HP"]}`\n`ATK ▸ {char['ATK']}`\n`SPD ▸ {char['SPD']}`\n`Status ▸ Fine`\n"
                for char in team
            ]
        )

    # Creates an embed displaying the current fight information
    def create_embed(self):
        try:
            combat_log = self.combat_log
            embed = discord.Embed()

            embed.set_author(name=f"----------- A boss raid is in progress -----------")

            embed.add_field(name="Team Members",
                    value=f"{self.format_team(team=[self.player_one_character])} {self.format_team(team=[self.player_two_character])} {self.format_team(team=[self.player_three_character])}",
                    inline=True)
            embed.add_field(name="Boss",
                    value=f"{self.format_team(team=[self.boss_character])}",
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

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when creating an embed for the boss raid display on line {line_num}")
   
    # Calculates the total damage of the attack
    def calculate_damage(self, attacker_character):
        try:
            damage = math.ceil(random.randint(math.ceil(attacker_character['ATK'] * 0.7), math.ceil(attacker_character['ATK'] * 1.3)))

            if attacker_character.get('crit_chance'):
                random_num = random.randint(1, 100)

                if attacker_character['crit_chance'] >= random_num:
                    damage *= attacker_character['crit_damage']

            return damage
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when calculating damage for the boss raid on line {line_num}")
   
    
    # Applys a random debuff based on the debuff chance
    def apply_debuff(self, debuff_chance, target_character):
        try:
            random_num = random.randint(1, 100)

            if debuff_chance >= random_num:
                random_num = random.randint(1, 3)

                match random_num:
                    case 1:
                        self.apply_bleeding(target_character=target_character, bleed_amount = 30) # Change bleed amount to boss stat

                    case 2:
                        self.apply_dazed(target_character=target_character)
                    
                    case 3:
                        self.apply_confused(target_character=target_character)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying a debuff the boss raid on line {line_num}")
   
    # Decreases character current HP based off of the total percentage of HP
    def apply_bleeding(self, target_character, bleed_amount):
        try:
            target_character['current_hp'] = target_character['current_hp'] - math.ceil((bleed_amount / 100) * target_character['HP'])
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying bleeding for the boss raid on line {line_num}")
   
    # Decreases the character's speed to 1
    def apply_dazed(self, target_character):
        try:
            target_character['SPD'] = 1
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying dazed for the boss raid on line {line_num}")
   
    # Cuts the chance of a character landing their special attack in half
    def apply_confused(self, target_character):
        try:
            if target_character.get('crit_chance'):
                target_character['crit_chance'] = math.ceil(target_character['crit_chance'] / 2)
            
            elif target_character.get('dodge_chance'):
                target_character['dodge_chance'] = math.ceil(target_character['dodge_chance'] / 2)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when applying confused for the boss raid on line {line_num}")
           
    # Allows for damage to be done to multiple characters
    def multi_character_attack(self, attacker_character, target_character):
        try:
            main_damage = self.calculate_damage(attacker_character=attacker_character)
            
            if target_character != self.player_one_character:
                splash_damage = math.ceil(main_damage / 2)
                self.player_one_character['current_hp'] -= splash_damage

            if target_character != self.player_two_character:
                splash_damage = math.ceil(main_damage / 2)
                self.player_two_character['current_hp'] -= splash_damage

            if target_character != self.player_three_character:
                splash_damage = math.ceil(main_damage / 2)
                self.player_three_character['current_hp'] -= splash_damage

            target_character['current_hp'] -= main_damage

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when landing a multi-character attack for the boss raid on line {line_num}")
   
    # ALlows multiple hits of damage to be done to one character
    def multi_hit_attack(self, attacker_character, target_character):
        try:
            base_damage = self.calculate_damage(attacker_character=attacker_character)

            first_hit_damage = math.ceil(base_damage * 0.3)
            second_hit_damage = math.ceil(base_damage * 0.5)
            third_hit_damage = math.ceil(base_damage * 0.7)

            final_damage = first_hit_damage + second_hit_damage + third_hit_damage

            target_character['current_hp'] -= final_damage

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info() # most recent (if any) by default
            line_num = exc_traceback.tb_lineno

            create_error_embed(error=e, ctx=self.ctx, msg=f"This occured when landing a multi-hit attack for the boss raid on line {line_num}")
   
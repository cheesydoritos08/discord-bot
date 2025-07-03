import discord
import handlers.database_handler as database_handler
from utils.utility_functions import update_quests

# Creates the view where the buttons are held
class TradeView(discord.ui.View):
    def __init__(self, offerer_user, ctx, receiver_user, trade_offered, trade_received):
        super().__init__()
        self.timeout = 30.0
        self.ctx = ctx
        self.offerer_user = offerer_user
        self.receiver_user = receiver_user
        self.trade_offered = trade_offered
        self.trade_received = trade_received

    async def on_timeout(self):
        self.remove_user_from_trade_state()
        return await super().on_timeout()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        responding_user = None
        if interaction.data.get("custom_id") == "decline_button" or interaction.data.get("custom_id") == "accept_button":
             responding_user = self.receiver_user
        elif interaction.data.get("custom_id") == "cancel_button":
             responding_user = self.offerer_user
        
        if interaction.user != responding_user:
           await interaction.response.send_message("You can not use this button.", ephemeral=True)
           return False
        
        return True

    def disable_buttons(self):
         for button in self.children:
              button.disabled = True
    
    def remove_user_from_trade_state(self):
        database_handler.users.update_one({"_id": self.receiver_user.id}, {"$set": {"in_trade": False}})
        database_handler.users.update_one({"_id": self.offerer_user.id}, {"$set": {"in_trade": False}})

    def create_embed(self, title, color):
         embed = discord.Embed(title = title, color = color)  
         embed.set_author(name="Trade Offer")
         embed.set_thumbnail(url=self.offerer_user.display_avatar)

         embed.add_field(name=f"{self.offerer_user}'s Offer",
                        value="\n".join(f"`{k}: {v}`" for k, v in self.trade_offered.items()),
                        inline=False)
         embed.add_field(name=f"{self.receiver_user}'s Offer",
                        value="\n".join(f"`{k}: {v}`" for k, v in self.trade_received.items()))
        
         embed.set_footer(text="Be wary of unfair trades and scams!")
         
         return embed
    
    # Controls the accept button
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green, custom_id="accept_button")
    async def accept_offer(self, interaction: discord.Interaction, button: discord.ui.Button):
         self.disable_buttons()
         offerer_inventory = database_handler.users.find_one({"_id": self.offerer_user.id}).get('inventory')
         receiver_inventory = database_handler.users.find_one({"_id": self.receiver_user.id}).get('inventory')

         for offer, offer_number in self.trade_offered.items():
            if offer != "Won":
                offer = offer.lower().replace(" ", "_")

                item_found = False
                for item in receiver_inventory.keys():
                    if item == offer:
                        database_handler.inc_value_to_users(user_id=self.receiver_user.id, key=f"inventory.{offer}.amount", value=offer_number)
                        item_found = True
            
                if not item_found:
                    database_handler.add_item(user_id=self.receiver_user.id, item=offer)
                    database_handler.inc_value_to_users(user_id=self.receiver_user.id, key=f"inventory.{offer}.amount", value=offer_number)

                database_handler.inc_value_to_users(user_id=self.offerer_user.id, key=f"inventory.{offer}.amount", value=-offer_number)
            elif offer == "Won":
              database_handler.inc_value_to_users(user_id=self.offerer_user.id, key=f"economy.won", value=-offer_number)
              database_handler.inc_value_to_users(user_id=self.receiver_user.id, key=f"economy.won", value=offer_number)                

         for offer, offer_number in self.trade_received.items():
            if offer != "Won":
                offer = offer.lower().replace(" ", "_")

                item_found = False
                for item in offerer_inventory.keys():
                    if item == offer:
                        database_handler.inc_value_to_users(user_id=self.offerer_user.id, key=f"inventory.{offer}.amount", value=offer_number)
                        item_found = True
            
                if not item_found:
                    database_handler.add_item(user_id=self.offerer_user.id, item=offer)
                    database_handler.inc_value_to_users(user_id=self.offerer_user.id, key=f"inventory.{offer}.amount", value=offer_number)

                database_handler.inc_value_to_users(user_id=self.receiver_user.id, key=f"inventory.{offer}.amount", value=-offer_number)
            elif offer == "Won":
              database_handler.inc_value_to_users(user_id=self.offerer_user.id, key=f"economy.won", value=offer_number)
              database_handler.inc_value_to_users(user_id=self.receiver_user.id, key=f"economy.won", value=-offer_number)  
         
         embed = self.create_embed(title = f"{self.receiver_user} has accepted the trade!", color = discord.Color.dark_green())
         
         if self.ctx.guild.id == 1382922154957344838:
            update_quests(user_id=self.offerer_user.id, quest_id="trade_with_player", amount=1)

         self.remove_user_from_trade_state()
    
         return await interaction.response.edit_message(embed = embed, view = self )
    
        # Controls the decline button
    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red, custom_id="delete_button")
    async def decline_offer(self, interaction: discord.Interaction, button: discord.ui.Button):
         self.disable_buttons()

         embed = self.create_embed(title = f"{self.receiver_user} has declined the trade!", color = discord.Color.dark_red())
         
         self.remove_user_from_trade_state()

         return await interaction.response.edit_message(embed = embed, view = self )
    
        # Controls the cancel button
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey, custom_id="cancel_button")
    async def cancel_offer(self, interaction: discord.Interaction, button: discord.ui.Button):
         self.disable_buttons()
         
         embed = self.create_embed(title = f"{self.offerer_user} has cancelled the trade!", color = discord.Color.dark_gray())
         
         self.remove_user_from_trade_state()

         return await interaction.response.edit_message(embed = embed, view = self )
         

def is_int(arg):
        try:
            int(arg)
            return True
        except ValueError:
            return False


def handle_offer(offer, ctx, user_id):
        offer_dictionary = {}
        user_profile = database_handler.users.find_one({"_id": user_id})
        money_offered = True

        # Makes sure that money is in the first slot if presented
        try:
            offer_dictionary["Won"] = int(offer[0])
            offer.pop(0)
        except ValueError:
            money_offered = False
        
        # Checks to make sure user has enough won
        if money_offered and offer_dictionary["Won"] > user_profile.get("economy").get("won"):
            return "Error occurred", f"{ctx.bot.get_user(user_id)} does not have enough won."

        # Stores the args in a dictionary format
        for arg in offer:
            if is_int(arg):
                return "Error occurred", "Money should be placed once at the beginning of the offer."
                
            separated_args = arg.split("^")
            try:
                if is_int(separated_args[1]):
                        separated_args[0] = separated_args[0].title().replace("Ev", "EV").replace("Xp", "XP").replace("_", " ")
                        offer_dictionary[separated_args[0]] = int(separated_args[1])
                else:
                    return "Error occurred", "Each offer should be formatted as such: `[money_amount, shard_name^amount, shard_name2^amount]`"
            except IndexError:
                return "Error occured", "Each offer should be formatted as such: `[money_amount, shard_name^amount, shard_name2^amount]`"
            
        # Checks to see if the user owns the shards
        for key, value in offer_dictionary.copy().items():
            if key == "Won":
                continue
            
            key = key.replace(" ", "_").lower()

            item_found = False

            for item, item_info in user_profile.get('inventory').items():
                if item == key and item_info['amount'] < value:
                    return "Error occured", "Someone doesn't have enough items to trade lol"
                elif item == key and item_info['amount'] >= value:
                    item_found = True
            
            if not item_found:
                return "Error occured", "Someone doesn't have enough items to trade lol"

        return offer_dictionary, " "

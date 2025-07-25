from discord.ext import commands
from handlers.trade_handler import is_int
from utils.utility_functions import create_error_embed

class InventoryConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            # Turns each argument into "instant_ramyeon"
            argument = argument.split(" ")
            return "_".join(argument).lower()
        except Exception as e:
            await ctx.send("Search for a valid item.")
            create_error_embed(error=e, ctx=ctx, msg="This occured while the inventory converter was working.")
        
class UseChipConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            # Turns each argument into "<character name> <amount>"
            argument = argument.split(" ")
            character_name = " ".join(argument[0:2]).title()
            amount = int(argument[2])
            return character_name, amount
        except Exception as e:
            await ctx.send("Don't make me say it twice: `?chip character_name amount`" )
            create_error_embed(error=e, ctx=ctx, msg="This occured while the use chip command ran.")

class BuySellConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            # Splits the argument into two parts
            amount = None
            argument = argument.split(" ")

            # 
            for arg in argument:
                if is_int(arg):
                    # Stores the amount and converts the remaining argument into an item
                    amount = int(arg)
                    argument.remove(arg)
                    argument = " ".join(argument)

                    item = await InventoryConverter().convert(ctx=ctx, argument=argument)
                    return item, amount
        except Exception as e:
            await ctx.send("Don't make me say it twice: `?buy item_name amount`")
            create_error_embed(error=e, ctx=ctx)

class TradeArgumentConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            # Converts the member into a discord.Member
            member = await commands.MemberConverter().convert(ctx, (argument[:argument.find("[")].strip()))
        
            # Separates the argument into the offered items and the received items
            offers = argument[argument.index("["):argument.index("]") + 1].strip() 
            receives = argument[argument.index("[", argument.index("[")+1) : argument.index("]", argument.index("]")+1) + 1].strip() 

            return member, offers, receives
        except Exception as e:
            await ctx.send("Format the trade correctly: `?trade @user [your offer] [their offer].`")
            create_error_embed(error=e, ctx=ctx)
            
        


import discord
import random
import asyncio
import handlers.database_handler as database_handler
from utils.buttons import ShopButtons
from utils.converters import BuySellConverter, TradeArgumentConverter
from utils.utility_functions import cooldown_calculator, check_boosts, update_quests, create_error_embed
from utils.timer import Timer
import time
import handlers.trade_handler as trade_handler
import datetime
from datetime import datetime, timedelta
from discord.ext import commands


# Controls the economy of the system
class Economy(commands.Cog):
    # Initializes the class
    def __init__(self, bot):
        self.bot = bot
        self.warned_cooldown_users = set()

    # Balance command
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(aliases=['bal'],
                      help="This command display the amount of won you currently have!")
    async def balance(self, ctx):
        # Stores the user and user profile into a variable
        user = ctx.message.author


        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=user.id):
            return

        user_profile = database_handler.users.find_one({'_id': user.id})

        # Stores the balance in a variable
        balance = user_profile.get('economy').get('won')

        # Creates an embed with all the info
        embed = discord.Embed(
            title=f"{user}'s Balance",
            description=f'Balance: ₩{balance}',
            color=discord.Color.dark_green(),
        )
        
        await ctx.send(embed=embed)

    # Daily command with a one day cooldown
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(help="This command allows you to collect a reward every 24 hours! For every day you collect your reward, your streak increases. The longer your streak, the more rewards you get daily!")
    async def daily(self, ctx):
        shard_obtained = False
        # Stores daily amount as a variable
        daily_amount = 500
        # Stores user as a variable
        user = ctx.message.author

        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=user.id):
            return

        
        user_profile = database_handler.users.find_one({'_id': user.id})

        if user_profile.get('timers').get('daily_claim', 0) != 0:
            return await ctx.send("You already claimed your daily reward, stupid.")

        # Gets the streak and last claim time of the user
        streak = user_profile.get('economy').get('daily_streak')
        last_claim_time = user_profile.get('economy').get('last_claim_time')
        last_claim = datetime.fromtimestamp(float(last_claim_time))
        claim_time = datetime.now()
        time_difference = claim_time - last_claim

        # Calculates whether to reset the streak or not
        if time_difference > timedelta(hours=48):
            database_handler.users.update_one(
                {'_id': user.id}, {'$set': {'economy.daily_streak': 1}}
            )
            streak = 1
        else:
            database_handler.inc_value_to_users(
                user_id=user.id, key='economy.daily_streak', value=1
            )
            streak += 1

        # Updates the amount of money based off of streak multipler and character buffs
        daily_amount += sum(
            effect['amount']
            for character in user_profile['characters']
            if character['class'] == 'Support'
            for effect in character['effects']
            if effect.get('type') == 'daily'
        )

        streak_multipler = (streak - 1) / 100
        daily_amount *= 1.00 + streak_multipler

        database_handler.inc_value_to_users(user_id=user.id, key='economy.won', value=daily_amount)

        # Determines what shard to give to user ever 5 days of their streak
        if streak % 5 == 0:

            def choose_rarity():
                # Determines the rarity of each tier depending on current streak
                if streak > 30:
                    rarities = {
                        'Legendary': 15,
                        'Epic': 17,
                        'Rare': 28,
                        'Common': 40,
                    }
                elif streak > 20:
                    rarities = {
                        'Legendary': 10,
                        'Epic': 15,
                        'Rare': 25,
                        'Common': 50,
                    }
                elif streak > 10:
                    rarities = {
                        'Legendary': 5,
                        'Epic': 12,
                        'Rare': 23,
                        'Common': 60,
                    }
                else:
                    rarities = {
                        'Legendary': 1,
                        'Epic': 9,
                        'Rare': 20,
                        'Common': 70,
                    }

                # Generates a rarity for the shard
                randomNum = random.randint(1, sum(rarities.values()))
                counter = 0
                for rarity, weight in rarities.items():
                    counter += weight
                    if randomNum <= counter:
                        return rarity, True

            # Stores the rarity and whether a shard was obtained in two variables
            rarity, shard_obtained = choose_rarity()

            # Picks a character shard based off of the rarity
            character = random.choice(
                database_handler.all_characters_search(key='rarity', query=rarity)
            )
            database_handler.inc_value_to_users(
                user_id=user.id, key=f'inventory.shards.{character["name"]}', value=1
            )
            
        update_quests(user_id=ctx.author.id, quest_id="use_daily_command", amount=1)


        # Determines the embed message to display based on whether a shard was obtained or not
        if shard_obtained:
            embed = discord.Embed(
                title='* Daily Reward *',
                description=f"You've obtained ₩{daily_amount}! This has been added to your balance.\nYou also obtained a {character['name']} shard! This has been added to your inventory.",
                color=discord.Color.dark_magenta(),
            )
        else:
            embed = discord.Embed(
                title='* Daily Reward *',
                description=f"You've obtained ₩{daily_amount}! This has been added to your balance.",
                color=discord.Color.dark_magenta(),
            )

        update_quests(user_id=ctx.author.id, quest_id="earn_five_thousand_won", amount=daily_amount)
        embed.set_footer(text=f'Current Streak: {streak}')

        # Updates the claim time for the daily bonus
        database_handler.users.update_one(
            {'_id': user.id},
            {'$set': {'economy.last_claim_time': str(claim_time.timestamp())}}
        )
  
        Timer(user_id=ctx.author.id, name="daily_claim", starttime=round(time.time()), timer_length = 60 * 60 * 24).create_timer()
        await ctx.send(embed=embed)

    # Creates a game of high or low for the user to play
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(name='highlow', 
                      aliases=['hl'],
                      help="This commands allows you to play a guessing game. The bot draws a card and you have to guess whether the next card drawn will be higher, lower or the same. If you win, you get 100 won!")
    async def high_or_low(self, ctx):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        # Sets the win amount and creates the card list
        win_amount = 100 * check_boosts(user_id=ctx.author.id,type="won_booster")
        cards_list = [
            'Ace: 🂡',
            '2: 🂢',
            '3: 🂣',
            '4: 🂤',
            '5: 🂥',
            '6: 🂦',
            '7: 🂧',
            '8: 🂨',
            '9: 🂩',
            '10: 🂪',
            'Jack: 🂫',
            'Queen: 🂭',
            'King: 🂮',
        ]

        # Draws the first card and gets its value
        first_card = random.choice(cards_list)
        first_card_index = cards_list.index(first_card)
        await ctx.send(
            f'I drew a {first_card}. What\'s my next card going to be? Higher, lower or the same? Reply with either `higher`, `lower` or `same`.'
        )

        # Checks to see whether the message sent was from the same person in the same channel
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            # Gets the answer from the user
            answer = ''
            msg = await self.bot.wait_for('message', check=check, timeout=10.0)

            # Draws the second card and gets its value
            second_card = random.choice(cards_list)
            second_card_index = cards_list.index(second_card)

            # Check to see whether the new card is higher or lower than the old one
            # and sets the answer accordingly
            if second_card_index > first_card_index:
                answer = 'higher'
            elif second_card_index < first_card_index:
                answer = 'lower'
            elif second_card_index == first_card_index:
                answer = 'same'

            # Sends a response based on the message sent by the user
            if msg.content.lower() == answer:
                await ctx.send(
                    f'The next card was a {second_card}! Congrats. Here\'s ₩{win_amount} for winning.'
                )
                database_handler.inc_value_to_users(
                    user_id=msg.author.id, key='economy.won', value=win_amount
                )
                update_quests(user_id=ctx.author.id, quest_id="win_highlow", amount=1)
                update_quests(user_id=ctx.author.id, quest_id="earn_five_thousand_won", amount=win_amount)

            elif (
                msg.content.lower() == 'higher'
                or msg.content.lower() == 'lower'
                or msg.content.lower() == 'same'
            ):
                await ctx.send(
                    f'The next card was a {second_card}! Guess you lost. Maybe try getting luckier next time.'
                )
            else:
                await ctx.send('Wrong word.')
        except asyncio.TimeoutError:
            await ctx.send('I don\'t have all day and you\'re wasting my time. Talk me when you\'re serious.')
        except Exception as e:
            create_error_embed(error=e, ctx=ctx)
        
    # Allows a player to guess what side the coin will land on
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(aliases=['cf'],
                      help="This command lets you make a bet and flip a coin. If you guess the correct side, your bet will be doubled and given back to you. If you guess the wrong side, your bet will be deducted from your balance.")
    async def coinflip(self, ctx):
        # Checks to see if the user has a profile or not
        if not await database_handler.check_existing_profile(ctx=ctx, user_id=ctx.author.id):
            return

        result = random.choice(['heads', 'tails'])
        await ctx.send('Enter a bet amount.')

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=5, check=check)

            try:
                bet = int(msg.content)
                if bet > database_handler.users.find_one({'_id': ctx.author.id}).get('economy').get(
                    'won'
                ):
                    return await ctx.send('How about you try getting enough money first before you gamble.')
            except ValueError:
                await ctx.send('Not a number, genius.')

            if bet < 1:
                return await ctx.send("Doesn't work like that.")
            
            await ctx.send('`Heads` or `tails`?')

            msg = await self.bot.wait_for('message', timeout=7, check=check)
            if msg.content.lower() == result:
                await ctx.send(
                    f'It was {result}. You got lucky. Here\'s your bet back, doubled.'
                )
                if bet >= 1000:
                    update_quests(user_id=ctx.author.id, quest_id="win_bet_coinflip", amount=1)
                    
                
                database_handler.inc_value_to_users(
                    user_id=msg.author.id, key='economy.won', value=(bet * check_boosts(user_id=ctx.author.id, type="won_booster"))
                )

                update_quests(user_id=ctx.author.id, quest_id="earn_five_thousand_won", amount=(bet * check_boosts(user_id=ctx.author.id, type="won_booster")))

            elif msg.content.lower() == 'heads' or msg.content.lower() == 'tails':
                await ctx.send(
                    f'It was {result}. Unlucky. Thanks for the money though.'
                )
                database_handler.inc_value_to_users(
                    user_id=msg.author.id, key='economy.won', value=-bet
                )
            else:
                await ctx.send("Wrong word.")

        except asyncio.TimeoutError:
            await ctx.send('I don\'t have all day and you\'re wasting my time. Talk me when you\'re serious.')
        except Exception as e:
            create_error_embed(error=e, ctx=ctx)
        
    # Displays the shop to the user
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.command(name="shop",
                      help="This command displays all the items you can currently buy or sell in the shop!")
    async def display_shop(self, ctx):
        all_items = database_handler.items.find({})
        buyable_items = []
        for item in all_items:
            if item.get("buy_price") is not None:
                buyable_items.append(item)

        shop_buttons = ShopButtons(items = buyable_items, ctx = ctx)
        await ctx.send(embed=shop_buttons.create_embed(), view=shop_buttons)

    # Allows a user to buy an item from the shop
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)   
    @commands.command(name="buy",
                      help = "This command lets you buy any item in the shop. The format for this command is `?buy <item name> <amount>`")
    async def buy_item(self, ctx, *, arg : BuySellConverter):
        try:
            item_being_bought, amount = arg
        except Exception as e:
            return await ctx.send("Do I really have to remind you to use the correct format?: `?buy <item name> <amount>`")

        buyable_items = list(database_handler.items.find({"buy_price": {"$exists": True}}))

        if amount < 1:
            return await ctx.send("Doesn't work like that.")

        for item in buyable_items:
            if  item_being_bought == item["name"]:
                user_profile = database_handler.users.find_one({"_id": ctx.author.id})
                user_won = user_profile.get("economy").get("won")
                user_inventory = user_profile.get("inventory")
                price = item["buy_price"] * amount

                if user_won < price:
                    return await ctx.send("Don't try to buy something if you're broke.")
                
                for user_item in user_inventory:
                    if user_item == item["name"]:
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item['name']}.amount", value=amount)
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=-price)
                        update_quests(user_id=ctx.author.id, quest_id="buy_five_items", amount=amount)
                        return await ctx.send(f"You bought {amount} {item['emoji']} {item["name"].replace("_", " ").title().replace("Xp", "XP")}(s).")

                database_handler.add_item(user_id=ctx.author.id, item=item_being_bought)
                database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item['name']}.amount", value=amount)
                database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=-price)
                update_quests(user_id=ctx.author.id, quest_id="buy_five_items", amount=amount)
                return await ctx.send(f"You bought {amount} {item['emoji']} {item['name'].replace("_", " ").title().replace("Xp", "XP")}(s).")
            
        return await ctx.send("You really think this is an item?")

    # Allows users to sell an item    
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.command(name="sell",
                      help = "This command lets you sell any item to the shop, if sellable. The format for this command is `?sell <item name> <amount>`")
    async def sell_item(self, ctx, *, arg : BuySellConverter):
        try:
            item_being_sold, amount = arg
        except Exception as e:
            return await ctx.send("How many times do I have to tell you what the correct format is?: `?sell <item name> <amount>`")

        sellable_items = list(database_handler.items.find({"sell_price": {"$exists": True}}))

        if amount < 1:
            return await ctx.send("Doesn't work like that.")

        for item in sellable_items:
            if  item_being_sold == item["name"]:
                user_profile = database_handler.users.find_one({"_id": ctx.author.id})
                user_inventory = user_profile.get("inventory")
                sell_amount = item["sell_price"] * amount

                if user_inventory.get(item["name"]) is None:
                    return await ctx.send("You don't even own this item...")
                elif user_inventory.get(item["name"]).get("amount") < amount:
                    return await ctx.send("You don't even own this item...")
                
                for user_item in user_inventory:
                    if user_item == item["name"]:
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key=f"inventory.{item['name']}.amount", value=-amount)
                        database_handler.inc_value_to_users(user_id=ctx.author.id, key="economy.won", value=sell_amount)
                        update_quests(user_id=ctx.author.id, quest_id="sell_five_items", amount=amount)
                        update_quests(user_id=ctx.author.id, quest_id="earn_five_thousand_won", amount=sell_amount)
                        return await ctx.send(f"You sold {amount} {item["emoji"]} {item["name"].replace("_", " ").title().replace("Xp", "XP")}(s).")
        
        return await ctx.send("What gave you the bright idea to try and pass this off as a valid item?")
                    
    # Allows users to trade with one another
    @commands.command(help = "This command lets you trade items and money with another player. The format for this command is `?trade <user> [your offer] [their offer]`. The offer should be formatted like this: [<money amount>, <item name^amount>]' So if you wanted to trade 2 epic shards and a raid token for 1000 won and a standard ticket, the command would look like this: ?trade <user> [epic shard^2, raid token^1] [1000, standard ticket^1]")
    async def trade(self, ctx, *, arg: TradeArgumentConverter):
        target_user, offers, receives = arg

        if target_user is None:
            return await ctx.send("Not a valid user.")

        if target_user == ctx.author or target_user.bot:
            return await ctx.send("Enter a valid user.")
        
        if database_handler.users.find_one({"_id": target_user.id}).get("in_trade") or database_handler.users.find_one({"_id": ctx.author.id}).get("in_trade"):
            return await ctx.send("One of you is already in a trade. Pay attention.")

        trade_offered = offers[1:-1].split(", ")
        trade_received= receives[1:-1].split(", ")


        for i, offer in enumerate(trade_offered):
            if trade_offered[i] == "":
                trade_offered.pop(i)
        
        for i, offer in enumerate(trade_received):
            if trade_received[i] == "":
                trade_received.pop(i)

        trade_offered_dictionary, error_offer = trade_handler.handle_offer(trade_offered, ctx, ctx.author.id)
        trade_received_dictionary,  error_received = trade_handler.handle_offer(trade_received, ctx, target_user.id)

        if trade_offered_dictionary == "Error occurred":
            return await ctx.send(error_offer)
        elif trade_received_dictionary == "Error occurred":
            return await ctx.send(error_received)
        
        embed = discord.Embed(title=f"{ctx.author} has sent {target_user} a trade!", color= discord.Color.dark_purple())  
        embed.set_author(name="Trade Offer")
        embed.set_thumbnail(url=ctx.author.display_avatar)

        embed.add_field(name=f"{ctx.author}'s Offer",
                        value="\n".join(f"`{k}: {v}`" for k, v in trade_offered_dictionary.items()),
                        inline=False)
        embed.add_field(name=f"{target_user}'s Offer",
                        value="\n".join(f"`{k}: {v}`" for k, v in trade_received_dictionary.items()))
        
        embed.set_footer(text="Be wary of unfair trades and scams!")

        database_handler.users.update_one({"_id": target_user.id}, {"$set": {"in_trade": True}})
        database_handler.users.update_one({"_id": ctx.author.id}, {"$set": {"in_trade": True}})

        return await ctx.send(embed=embed, view=trade_handler.TradeView(offerer_user=ctx.author, ctx = ctx, receiver_user=target_user, trade_offered=trade_offered_dictionary, trade_received=trade_received_dictionary))

    @trade.error
    @sell_item.error
    @buy_item.error
    @coinflip.error
    @high_or_low.error
    @display_shop.error
    @daily.error
    @balance.error
    async def cooldown_error(self, ctx, error):
        # Sends a cooldown message if command is reused when on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            user_id = ctx.author.id
            cooldown_string = cooldown_calculator(round(error.retry_after))

            if user_id not in self.warned_cooldown_users:
                self.warned_cooldown_users.add(user_id)
                await ctx.send(f'Can\'t you be patient and wait for {cooldown_string}?')
            
            # cleanup after cooldown
            async def remove_after():
                await asyncio.sleep(error.retry_after)
                self.warned_cooldown_users.discard(user_id)

            asyncio.create_task(remove_after())
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            await create_error_embed(ctx=ctx, error=error)

async def setup(bot):
    await bot.add_cog(Economy(bot))

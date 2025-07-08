import discord
import handlers.database_handler as database_handler
from utils.buttons import TutorialButton
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="This command gives you a list of all the commands available for users!")
    async def help(self, ctx, command=None):
        help_embed = discord.Embed(title="Commands", color=0x14545d)
        cogs_list = [x for x in dict(self.bot.cogs).keys()]
        command_names_list = [x.name for x in self.bot.commands]

        # If there are no arguments, just list the commands:
        if not command:
            for cog in cogs_list:
                if cog == "Owner_Commands":
                    continue

                help_embed.add_field(
                    name=f"{cog.replace("_", " ")}",
                    value=" ".join([f'`{str(x)}`' for x in self.bot.commands if x.cog_name == cog]),
                    inline=False
            )

            help_embed.add_field(
                name="Details",
                value="Type `?help <command name>` for more details about each command.",
                inline=False
            )

        # If the argument is a command, get the help text from that command:
        elif command in command_names_list:
            all_aliases = " , ".join(self.bot.get_command(command).aliases) or "None"
            help_embed.add_field(
                name=command,
                value=f"**Aliases:** {all_aliases}\n **Description:** {self.bot.get_command(command).help}"
            )

        # If someone is just trolling:
        else:
            help_embed.add_field(
                name="Invalid command.",
                value="Can't help you if it doesn't exist now can I?"
            )

        await ctx.send(embed=help_embed)

    # Sends a tutorial to the user when user types $tutorial
    @commands.command(aliases=['tut'], 
                      help='This command gives you a tutorial of the bot! Very useful c:')
    async def tutorial(self, ctx):
        embed = discord.Embed(
            title='Welcome to the Lookism Bot!',
            description="Welcome to the Lookism Bot! This tutorial goes the core mechanics of the bot so feel free to revisit it as much as you want! If you ever want to find out more about a command, use the ?help command. (Pictures are unrelated to the tutorial, they just look cool. All credits go to the original creators.)",
            color=discord.Color.purple(),
        )
        embed.set_image(url='https://i.pinimg.com/736x/80/e0/ac/80e0ace80f573d27333a042e6e51d211.jpg')

        user_id = ctx.author.id
        await ctx.author.send(embed=embed, view=TutorialButton())
        await ctx.send('Check DMs.')
        database_handler.create_new_profile(user_id)


async def setup(bot):
    await bot.add_cog(Help(bot))



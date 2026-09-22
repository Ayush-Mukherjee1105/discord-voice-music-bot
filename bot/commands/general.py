from discord.ext import commands


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Check whether the bot is responding."""
        await ctx.send("Pong!")


def setup(bot):
    bot.add_cog(GeneralCommands(bot))
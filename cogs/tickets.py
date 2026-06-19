from discord.ext import commands
import discord

from views.ticket_modal import TicketModal


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="ticket-test",
        description="Open ticket modal"
    )
    async def ticket_test(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_modal(
            TicketModal(interaction.guild.id)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
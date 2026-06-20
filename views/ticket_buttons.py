import discord
from time import sleep
from services.logs import logger
from discord.ui import Button, View
from datetime import datetime, timezone
from services.translation_service import tr


from database.repository import (
    close_ticket_db,
    delete_ticket_by_channel_id,
    get_server_config,
    get_ticket_by_channel_id,
)

class TicketButtons(View):
    def __init__(self, guild_id: int, admin_role_name: str = None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.admin_role_name = admin_role_name

        close_button = Button(
            label=tr(guild_id, "button_close_ticket"),
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id=f"close_ticket_btn:{guild_id}",
        )
        close_button.callback = self.close_ticket

        notify_button = Button(
            label=tr(guild_id, "button_notify_member"),
            style=discord.ButtonStyle.secondary,
            emoji="🔔",
            custom_id=f"notify_member_btn:{guild_id}",
        )
        notify_button.callback = self.notify_member

        self.add_item(close_button)
        self.add_item(notify_button)


    async def _is_staff(self, guild: discord.Guild, member: discord.Member) -> bool:
        """Helper privado para validar se o utilizador pertence à Staff."""
        if member.guild_permissions.administrator:
            return True
            
        if not self.admin_role_name:
            config = get_server_config(guild.id) or {}
            self.admin_role_name = config.get("ADMIN_ROLE_NAME")

        if self.admin_role_name:
            role = discord.utils.get(guild.roles, name=self.admin_role_name)
            if role and role in member.roles:
                return True
                
        return False


    async def close_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        await interaction.response.defer(ephemeral=True)

        ticket = get_ticket_by_channel_id(channel.id)
        if not ticket:
            await interaction.followup.send(tr(guild.id, "ticket_not_found_db"), ephemeral=True)
            return

        author_id = ticket.get("user_id")

        is_staff_member = await self._is_staff(guild, user)
        if not is_staff_member and user.id != author_id:
            logger.warning(f"Security: Unauthorized user {user.id} attempted to close the ticket on channel {channel.id}")
            await interaction.followup.send("❌ You do not have permission to close this ticket.", ephemeral=True)
            return

        config = get_server_config(guild.id) or {}
        transcript_channel_id = config.get("transcript_channel_id")

        if not transcript_channel_id:
            await interaction.followup.send(tr(guild.id, "transcript_not_configured"), ephemeral=True)
            return

        transcript_channel = guild.get_channel(int(transcript_channel_id))
        if not transcript_channel:
            logger.error(f"Invalid Configuration: Transcription channel {transcript_channel_id} does not exist in Guild {guild.id}")
            await interaction.followup.send("❌ The configured transcription channel could not be found.", ephemeral=True)
            return

        subject = ticket.get("subject", tr(guild.id, "ticket_no_subject"))
        
        embed = discord.Embed(
            title=tr(guild.id, "ticket_data_title"),
            color=discord.Color.dark_grey(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name=tr(guild.id, "ticket_author_field"), value=f"<@{author_id}>", inline=True)
        embed.add_field(name=tr(guild.id, "ticket_closed_by_field"), value=f"{user.mention}", inline=True)
        embed.add_field(name=tr(guild.id, "ticket_subject_label_field"), value=f"```{subject}```", inline=False)
        embed.set_footer(text=tr(guild.id, "panel_footer"))

        try:
            await transcript_channel.send(embed=embed)
            
            await interaction.followup.send(tr(guild.id, "ticket_closed_transcript_sent"), ephemeral=True)
            
            close_ticket_db(channel.id)
            delete_ticket_by_channel_id(channel.id)
            
            logger.info(f"Audit: Ticket {channel.id} successfully closed by {user.id}")
            sleep(5)
            await channel.delete(reason=f"Ticket closed by {user.name} ({user.id})")

        except discord.Forbidden:
            logger.error(f"Permission Failure: The bot does not have permission to manage/delete the channel {channel.id} in the Guild {guild.id}")
            await interaction.followup.send("❌ Permission Error: The bot does not have permission to delete this channel.", ephemeral=True)
        except Exception as e:
            logger.exception(f"Unexpected error while closing ticket {channel.id}: {e}")


    async def notify_member(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        await interaction.response.defer(ephemeral=True)

        if not await self._is_staff(guild, user):
            logger.warning(f"Security: User {user.id} attempted to use the notification button without being a staff member.")
            return await interaction.followup.send(tr(guild.id, "notify_no_permission"), ephemeral=True)

        ticket = get_ticket_by_channel_id(channel.id)
        if not ticket:
            return await interaction.followup.send(tr(guild.id, "ticket_not_found_db"), ephemeral=True)

        ticket_user_id = int(ticket.get("user_id"))

        ticket_user = guild.get_member(ticket_user_id)
        if not ticket_user:
            try:
                ticket_user = await guild.fetch_member(ticket_user_id)
            except discord.NotFound:
                logger.error(f"Notification Failed: User {ticket_user_id} left server {guild.id}")
                return await interaction.followup.send("❌ The ticket creator is no longer on this server.", ephemeral=True)
            except discord.HTTPException:
                logger.exception(f"Network error while retrieving user {ticket_user_id}")
                return await interaction.followup.send("❌ Error contacting the Discord API.", ephemeral=True)

        await interaction.followup.send(
            tr(guild.id, "member_notified", member=ticket_user.name),
            ephemeral=True,
        )
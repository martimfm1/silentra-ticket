import discord
from services.logs import logger
from discord.ui import Button, View
from database.repository import get_server_config
from services.translation_service import tr
from views.ticket_modal import TicketModal



class TicketView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        
        create_button = Button(
            label=tr(guild_id, "button_open_ticket"),
            style=discord.ButtonStyle.gray,
            emoji="🎫",
            custom_id=f"create_ticket_btn:{guild_id}",
        )
        create_button.callback = self.create_ticket
        self.add_item(create_button)

    async def create_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        guild_id = guild.id

        try:
            config = get_server_config(guild_id) or {}

            required_keys = ["ticket_category_id", "admin_role_name", "transcript_channel_id"]
            missing = [key for key in required_keys if not config.get(key)]

            if missing:
                key_names = {
                    "ticket_category_id": tr(guild_id, "config_ticket_category"),
                    "admin_role_name": tr(guild_id, "config_admin_role"),
                    "transcript_channel_id": tr(guild_id, "config_transcript_channel"),
                }
                missing_readable = ", ".join(key_names[k] for k in missing if k in key_names)
                
                logger.warning(f"Incomplete Configuration: Guild {guild_id} attempted to instantiate a ticket, but the following fields are missing: {missing}")
                
                await interaction.response.send_message(
                    tr(guild_id, "cannot_open_tickets_missing", missing=missing_readable),
                    ephemeral=True,
                )
                return

            await interaction.response.send_modal(TicketModal(guild_id=guild_id))
            logger.debug(f"UI: Opening modal sent to user {interaction.user.id} in Guild {guild_id}")

        except discord.InteractionResponded:
            logger.warning(f"UI Split-Second: Double-click detected for user {interaction.user.id}")
        except Exception as e:
            logger.exception(f"Critical error processing ticket panel activation in Guild {guild_id}: {e}")
            
            try:
                await interaction.response.send_message(
                    "❌ The support system encountered an internal instability while loading the form. Please try again.",
                    ephemeral=True
                )
            except Exception:
                pass

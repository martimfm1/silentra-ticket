import logging
import discord
from discord.ui import Button, View
from database.repository import get_server_config
from services.translation_service import tr
from views.ticket_modal import TicketModal

logger = logging.getLogger(__name__)

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

            required_keys = ["TICKET_CATEGORY_ID", "ADMIN_ROLE_NAME", "TRANSCRIPT_CHANNEL_ID"]
            missing = [key for key in required_keys if not config.get(key)]

            if missing:
                key_names = {
                    "TICKET_CATEGORY_ID": tr(guild_id, "config_ticket_category"),
                    "ADMIN_ROLE_NAME": tr(guild_id, "config_admin_role"),
                    "TRANSCRIPT_CHANNEL_ID": tr(guild_id, "config_transcript_channel"),
                }
                missing_readable = ", ".join(key_names[k] for k in missing if k in key_names)
                
                logger.warning(f"Configuração Incompleta: Guild {guild_id} tentou instanciar ticket, mas faltam os campos: {missing}")
                
                await interaction.response.send_message(
                    tr(guild_id, "cannot_open_tickets_missing", missing=missing_readable),
                    ephemeral=True,
                )
                return

            await interaction.response.send_modal(TicketModal(guild_id=guild_id))
            logger.debug(f"UI: Modal de abertura enviado para o utilizador {interaction.user.id} na Guild {guild_id}")

        except discord.InteractionResponded:
            logger.warning(f"UI Split-Second: Duplo clique detetado para o utilizador {interaction.user.id}")
        except Exception as e:
            logger.exception(f"Erro crítico ao processar acionamento do painel de tickets na Guild {guild_id}: {e}")
            
            try:
                await interaction.response.send_message(
                    "❌ O sistema de suporte encontrou uma instabilidade interna ao carregar o formulário. Por favor, tenta novamente.",
                    ephemeral=True
                )
            except Exception:
                pass

import logging
import discord
from discord.ui import Modal, TextInput
from services.translation_service import tr
from database.repository import get_server_config, create_ticket_db
from views.ticket_buttons import TicketButtons

logger = logging.getLogger(__name__)

class TicketModal(Modal):
    def __init__(self, guild_id: int):
        super().__init__(title=tr(guild_id, "modal_open_ticket_title"))
        self.guild_id = guild_id
        
        self.subject = TextInput(
            label=tr(guild_id, "modal_subject_label"), 
            max_length=255,
            required=True
        )
        self.add_item(self.subject)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        await interaction.response.defer(ephemeral=True)

        config = get_server_config(guild.id) or {}
        category_id = config.get("TICKET_CATEGORY_ID")
        admin_role_name = config.get("ADMIN_ROLE_NAME")
        transcript_channel_id = config.get("TRANSCRIPT_CHANNEL_ID")

        missing = []
        if not category_id: missing.append(tr(guild.id, "config_ticket_category"))
        if not admin_role_name: missing.append(tr(guild.id, "config_admin_role"))
        if not transcript_channel_id: missing.append(tr(guild.id, "config_transcript_channel"))

        if missing:
            await interaction.followup.send(
                tr(guild.id, "cannot_open_ticket_missing", missing=", ".join(missing)),
                ephemeral=True
            )
            return

        sanitized_name = f"ticket-{member.name.lower()}".replace(" ", "-")
        existing_channel = discord.utils.get(guild.text_channels, name=sanitized_name)
        if existing_channel:
            logger.warning(f"Segurança: Utilizador {member.id} tentou duplicar ticket no canal existente {existing_channel.id}")
            await interaction.followup.send("❌ Já tens um ticket ativo aberto no servidor.", ephemeral=True)
            return

        category = guild.get_channel(int(category_id))
        if not category or not isinstance(category, discord.CategoryChannel):
            logger.error(f"Erro de Infraestrutura: Categoria de tickets {category_id} não existe na Guild {guild.id}")
            await interaction.followup.send("❌ Erro de Configuração: A categoria de suporte configurada foi eliminada ou é inválida.", ephemeral=True)
            return

        admin_role = discord.utils.get(guild.roles, name=admin_role_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True,
            ),
        }

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
            )

        try:
            ticket_channel = await guild.create_text_channel(
                name=sanitized_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket aberto pelo utilizador: {member.name} ({member.id})"
            )
        except discord.Forbidden:
            logger.critical(f"Falha de Permissão: O bot não tem 'Manage Channels' na Guild {guild.id}")
            await interaction.followup.send("❌ Falha crítica: O Bot não tem permissões administrativas para criar canais de texto.", ephemeral=True)
            return
        except Exception:
            logger.exception(f"Erro inesperado ao instanciar canal de texto para o utilizador {member.id}")
            await interaction.followup.send("❌ Ocorreu um erro interno ao processar a criação do canal.", ephemeral=True)
            return

        db_success = create_ticket_db(guild.id, ticket_channel.id, member.id, self.subject.value)
        if not db_success:
            logger.critical(f"Falha de Transação: Destruindo canal órfão {ticket_channel.id} devido a erro na gravação da BD.")
            await ticket_channel.delete(reason="Rollback: Falha ao registar o ticket na Base de Dados.")
            await interaction.followup.send("❌ Sistema temporariamente indisponível. Por favor, tenta novamente mais tarde.", ephemeral=True)
            return

        embed = discord.Embed(
            title=tr(guild.id, "ticket_opened_title", member=member.display_name),
            description=tr(guild.id, "ticket_opened_desc"),
            color=discord.Color.dark_grey(),
        )
        embed.add_field(name="\u200b", value=tr(guild.id, "ticket_opened_guidance"), inline=False)
        embed.add_field(
            name="\u200b",
            value=tr(guild.id, "ticket_subject_field", subject=self.subject.value),
            inline=False,
        )
        embed.set_footer(text=tr(guild.id, "panel_footer"))

        view = TicketButtons(guild_id=guild.id, admin_role_name=admin_role_name)
        content = member.mention
        allowed_mentions = discord.AllowedMentions(users=[member])

        if admin_role:
            content += f" {admin_role.mention}"
            allowed_mentions.roles = [admin_role]

        try:
            await ticket_channel.send(
                content=content,
                embed=embed,
                view=view,
                allowed_mentions=allowed_mentions,
            )
            
            await interaction.followup.send(
                tr(guild.id, "ticket_created_success", channel=ticket_channel.mention),
                ephemeral=True,
            )
            logger.info(f"Sucesso: Ticket {ticket_channel.id} instanciado e registado para o utilizador {member.id}")
            
        except Exception:
            logger.exception(f"Erro ao popular conteúdo inicial no canal de tickets {ticket_channel.id}")
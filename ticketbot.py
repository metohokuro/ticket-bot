import discord
from discord.ext import commands
from discord import app_commands
import os

# Botの設定
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


class TicketView(discord.ui.View):
    def __init__(self, role: discord.Role, category: discord.CategoryChannel, log_channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.role = role
        self.category = category
        self.log_channel = log_channel

    @discord.ui.button(label="チケットを作成", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild

        # チケットチャンネル名を定義
        channel_name = f"ticket-{interaction.user.name}"

        # 同名のチャンネルが既に存在しているか確認
        existing_channel = discord.utils.get(self.category.channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message("既にチケットが存在します！", ephemeral=True)
            return

        # チャンネルを作成
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),  # デフォルトでは非公開
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),  # 作成者にアクセスを許可
            self.role: discord.PermissionOverwrite(view_channel=True, send_messages=True)  # 指定ロールにアクセスを許可
        }

        channel = await self.category.create_text_channel(name=channel_name, overwrites=overwrites)

        await interaction.response.send_message(f"チケットチャンネル {channel.mention} を作成しました！", ephemeral=True)

        # チャンネルに初期メッセージを送信
        delete_view = DeleteTicketView(channel, self.log_channel, interaction.user)
        await channel.send(
            f"{self.role.mention} チケットが作成されました。\n{interaction.user.mention} がこのチケットを作成しました。\n"
            f"解決したら以下のボタンを押してチャンネルを削除してください。",
            view=delete_view
        )

        # ログチャンネルに通知を送信
        await self.log_channel.send(f"チケットチャンネル {channel.mention} が作成されました。\n作成者: {interaction.user.mention}")


class DeleteTicketView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, log_channel: discord.TextChannel, ticket_creator: discord.Member):
        super().__init__(timeout=None)
        self.channel = channel
        self.log_channel = log_channel
        self.ticket_creator = ticket_creator

    @discord.ui.button(label="チケットを削除", style=discord.ButtonStyle.red, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # チケットのメッセージをファイルに保存
        transcript_file = f"{self.channel.name}_transcript.txt"
        with open(transcript_file, "w", encoding="utf-8") as file:
            async for message in self.channel.history(oldest_first=True):
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                file.write(f"[{timestamp}] {message.author}: {message.content}\n")

        # ログチャンネルにファイルを送信
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        await self.log_channel.send(
            f" {timestamp} チケットチャンネル {self.channel.name} が削除されました。\n削除者: {interaction.user.mention}",
            file=discord.File(transcript_file)
        )

        # チケット作成者にDMを送信
        try:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            await self.ticket_creator.send(
                f"{timestamp}あなたのチケットチャンネル `{self.channel.name}` が削除されました。\n以下がチケットの記録です。",
                file=discord.File(transcript_file)
            )
        except discord.Forbidden:
            await self.log_channel.send(f"チケット作成者 {self.ticket_creator.mention} へのDM送信に失敗しました。")

        # 一時ファイルを削除
        os.remove(transcript_file)

        # チャンネル削除
        await self.channel.delete(reason=f"チケット削除 by {interaction.user}")


@bot.tree.command(name="ticket", description="チケットを作成するボタンを送信します")
@app_commands.describe(
    role="チケットにアクセスできるロール",
    category="チケットチャンネルを作成するカテゴリー",
    log_channel="チケットのログを送信するチャンネル",
    title="埋め込みメッセージのタイトル（省略可能）",
    description="埋め込みメッセージの説明（省略可能）"
)
async def ticket(
    interaction: discord.Interaction,
    role: discord.Role,
    category: discord.CategoryChannel,
    log_channel: discord.TextChannel,
    title: str = "チケット発行",
    description: str = "チケットを発行する場合は下のボタンを押してください"
):
    # Embedの作成
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )

    # ボタン付きのメッセージを送信
    view = TicketView(role=role, category=category, log_channel=log_channel)
    await interaction.response.send_message(embed=embed, view=view)
# Botの起動
@bot.event
async def on_ready():
    print(f"ログインしました：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンドを {len(synced)} 個同期しました")
    except Exception as e:
        print(f"スラッシュコマンドの同期に失敗しました: {e}")
bot.run('とーくん')

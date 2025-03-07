import discord
from discord.ext import commands
from discord import app_commands
import os

# Botの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# サーバーIDとカテゴリIDを保存するファイル
SERVER_FILE = 'servers.txt'

# サーバーIDに対応するカテゴリ情報を保存する
def get_server_categories(server_id):
    # ファイルがあれば読み込む、なければ空の辞書を返す
    if os.path.exists(SERVER_FILE):
        with open(SERVER_FILE, 'r') as file:
            for line in file:
                server, category = line.strip().split(':')
                if int(server) == server_id:
                    return category
    return None

# サーバーIDとカテゴリIDを保存する
def save_server_categories(server_id, category):
    with open(SERVER_FILE, 'a') as file:
        file.write(f"{server_id}:{category}\n")

# サーバーのカテゴリを削除する
def remove_server_categories(server_id):
    if os.path.exists(SERVER_FILE):
        with open(SERVER_FILE, 'r') as file:
            lines = file.readlines()

        with open(SERVER_FILE, 'w') as file:
            for line in lines:
                if not line.startswith(f"{server_id}:"):
                    file.write(line)

# /select コマンド
@bot.tree.command(name="select", description="カテゴリを選択してサーバーに保存します")
@app_commands.describe(category="選択するカテゴリ")
async def select(interaction: discord.Interaction, category: str):
    server_id = interaction.guild.id

    existing_category = get_server_categories(server_id)
    if existing_category:
        remove_server_categories(server_id)  # 既存のカテゴリを削除
        await interaction.response.send_message(f"既存のカテゴリ `{existing_category}` を削除しました。新しいカテゴリ `{category}` を保存します。")
    else:
        await interaction.response.send_message(f"カテゴリ `{category}` を保存しました。")
    
    save_server_categories(server_id, category)

# /ticket コマンド
@bot.tree.command(name="ticket", description="チケット作成コマンド")
@app_commands.describe(staff_role="スタッフロール", log_channel="ログチャンネル")
async def ticket(interaction: discord.Interaction, staff_role: discord.Role, log_channel: discord.TextChannel):
    # ボタンの作成
    button = discord.ui.Button(label="チケットを作成", style=discord.ButtonStyle.primary)
    
    async def button_callback(interaction):
        category = get_server_categories(interaction.guild.id)
        if not category:
            await interaction.response.send_message("カテゴリが設定されていません。`/select` コマンドで設定してください。")
            return

        # チケットチャンネルの作成
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            staff_role: discord.PermissionOverwrite(view_channel=True)
        }
        
        # カテゴリを指定してチャンネルを作成
        category_channel = discord.utils.get(interaction.guild.categories, name=category)
        if category_channel:
            ticket_channel = await interaction.guild.create_text_channel(
                "チケット-" + interaction.user.name, 
                category=category_channel,
                overwrites=overwrites
            )
            
            # ログチャンネルにメッセージを送信
            await log_channel.send(f"{interaction.user.mention} がチケットチャンネル {ticket_channel.mention} を作成しました！")
            
            # チャンネル削除ボタンを表示
            delete_button = discord.ui.Button(label="チャンネル削除", style=discord.ButtonStyle.danger)
            
            async def delete_button_callback(interaction):
                await ticket_channel.delete()
                await log_channel.send(f"{interaction.user.mention} がチャンネル {ticket_channel.mention} を削除しました。")
                await interaction.response.send_message(f"{ticket_channel.mention} チャンネルを削除しました。")
            
            delete_button.callback = delete_button_callback
            
            # ボタンを送信
            view = discord.ui.View()
            view.add_item(delete_button)
            await ticket_channel.send("チャンネル削除ボタンを押して、チケットチャンネルを削除できます。", view=view)
        else:
            await interaction.response.send_message("カテゴリが見つかりません。`/select` でカテゴリを設定してください。")

    # ボタンのコールバックを設定
    button.callback = button_callback
    
    # ボタンをビューに追加
    view = discord.ui.View()
    view.add_item(button)
    
    # ユーザーにボタンを送信
    await interaction.response.send_message("チケットを作成するためのボタンです。", view=view)

# ボットの起動
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

bot.run('YOUR_BOT_TOKEN')

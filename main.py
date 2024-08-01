import os
import subprocess
from flask import Flask, request
from telethon import TelegramClient, events
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher
from threading import Thread

app = Flask(__name__)

# Your bot token and API credentials
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'

bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

client = TelegramClient('session_name', API_ID, API_HASH)

def start(update, context):
    update.message.reply_text('Hello! I am your deployment bot. Use /help to see available commands.')

def help_command(update, context):
    update.message.reply_text('/start - Start the bot\n'
                              '/deploy <repo_url> - Deploy the specified repository to Heroku\n'
                              '/setappname <app_name> - Set a custom name for the Heroku app\n'
                              '/status - Check the status of the latest deployment\n'
                              '/logs - Retrieve logs from Heroku')

def deploy(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        update.message.reply_text('Please set a Heroku app name first using /setappname command.')
        return

    repo_url = context.args[0]  # Example: "https://github.com/user/repo"
    app_name = user_sessions[user_id]['app_name']

    # Clone the repository
    subprocess.run(['git', 'clone', repo_url])
    
    # Change directory to the repository
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    os.chdir(repo_name)
    
    # Add and commit any changes (if needed)
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', 'Deploy via Telegram Bot'])
    
    # Create Heroku app or set remote if it already exists
    subprocess.run(['heroku', 'git:remote', '-a', app_name])
    subprocess.run(['git', 'push', 'heroku', 'master'])
    
    # Go back to the original directory
    os.chdir('..')
    
    update.message.reply_text('Deployment started!')

def set_app_name(update, context):
    user_id = update.message.from_user.id
    app_name = context.args[0]
    user_sessions[user_id] = {'app_name': app_name}
    update.message.reply_text(f'Heroku app name set to {app_name}.')

def check_status(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        update.message.reply_text('Please set a Heroku app name first using /setappname command.')
        return

    app_name = user_sessions[user_id]['app_name']
    status = subprocess.run(['heroku', 'ps', '-a', app_name], capture_output=True, text=True)
    update.message.reply_text(f'Status of {app_name}:\n{status.stdout}')

def get_logs(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        update.message.reply_text('Please set a Heroku app name first using /setappname command.')
        return

    app_name = user_sessions[user_id]['app_name']
    logs = subprocess.run(['heroku', 'logs', '--tail', '-a', app_name], capture_output=True, text=True)
    update.message.reply_text(f'Logs of {app_name}:\n{logs.stdout}')

def handle_update(update):
    dispatcher.process_update(update)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("deploy", deploy, pass_args=True))
dispatcher.add_handler(CommandHandler("setappname", set_app_name, pass_args=True))
dispatcher.add_handler(CommandHandler("status", check_status))
dispatcher.add_handler(CommandHandler("logs", get_logs))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    handle_update(update)
    return 'OK'

if __name__ == '__main__':
    Thread(target=app.run, kwargs={'port': int(os.environ.get('PORT', 5000))}).start()
    
    # Start the Telegram bot
    updater = Updater(token=BOT_TOKEN, use_context=True)
    updater.dispatcher = dispatcher
    updater.start_polling()
    updater.idle()

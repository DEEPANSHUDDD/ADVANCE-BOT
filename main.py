import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, Dispatcher, Filters, MessageHandler, Updater
from flask import Flask, request
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Access the bot token, owner ID, and Telethon API credentials from environment variables
BOT_TOKEN = os.getenv('TOKEN')
OWNER_ID = os.getenv('OWNER_ID')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_NAME = 'my_telegram_session'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not BOT_TOKEN:
    raise ValueError("No TOKEN provided. Please set the TOKEN environment variable.")

if not OWNER_ID:
    raise ValueError("No OWNER_ID provided. Please set the OWNER_ID environment variable.")

if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH must be set for Telethon.")

if not OPENAI_API_KEY:
    raise ValueError("No OPENAI_API_KEY provided. Please set the OPENAI_API_KEY environment variable.")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Initialize the Telethon client
telethon_client = TelegramClient(StringSession(), API_ID, API_HASH)

# Store user sessions and predefined commands
user_sessions = {}
predefined_commands = {
    'update_bot': 'git pull origin main',
    'restart_bot': 'sudo systemctl restart telegram_bot.service',
    'run_script': 'sh /path/to/your/script.sh',
    'check_disk': 'df -h'
}

def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Heroku Deployment", callback_data='deploy')],
        [InlineKeyboardButton("Run Telethon Script", callback_data='run_telethon_script')],
        [InlineKeyboardButton("AI", callback_data='ai')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Hello! I am your deployment bot. Choose an option:', reply_markup=reply_markup)

def button(update, context):
    query = update.callback_query
    query.answer()
    if query.data == 'deploy':
        context.bot.send_message(chat_id=query.message.chat_id, text="You selected Heroku Deployment. Use /help to see available commands.")
    elif query.data == 'run_telethon_script':
        context.bot.send_message(chat_id=query.message.chat_id, text="You selected to run a Telethon script. Use 'dk ai' followed by your request to run the script.")
    elif query.data == 'ai':
        context.bot.send_message(chat_id=query.message.chat_id, text="You selected AI. Use 'dk ai' followed by your request to interact with AI.")

def help_command(update, context):
    update.message.reply_text('/start - Start the bot and see options\n'
                              '/setheroku <heroku_api_key> - Set your Heroku API key\n'
                              '/setappname <app_name> - Set a custom name for the Heroku app\n'
                              '/deploy <repo_url> - Deploy the specified repository to Heroku\n'
                              '/status - Check the status of the latest deployment\n'
                              '/logs - Retrieve logs from Heroku\n'
                              '/exec <command> - Execute a predefined command\n'
                              '/setopenai <api_key> - Set the OpenAI API key')

def set_heroku(update, context):
    user_id = update.message.from_user.id
    heroku_api_key = context.args[0]
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['heroku_api_key'] = heroku_api_key
    update.message.reply_text('Heroku API key set.')

def set_app_name(update, context):
    user_id = update.message.from_user.id
    app_name = context.args[0]
    if user_id not in user_sessions:
        update.message.reply_text('Please set your Heroku API key first using /setheroku command.')
        return
    user_sessions[user_id]['app_name'] = app_name
    update.message.reply_text(f'Heroku app name set to {app_name}.')

def deploy(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or 'heroku_api_key' not in user_sessions[user_id] or 'app_name' not in user_sessions[user_id]:
        update.message.reply_text('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    repo_url = context.args[0]  # Example: "https://github.com/user/repo"
    app_name = user_sessions[user_id]['app_name']
    heroku_api_key = user_sessions[user_id]['heroku_api_key']

    # Clone the repository
    subprocess.run(['git', 'clone', repo_url])
    
    # Change directory to the repository
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    os.chdir(repo_name)
    
    # Add and commit any changes (if needed)
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', 'Deploy via Telegram Bot'])
    
    # Authenticate and create Heroku app or set remote if it already exists
    env = os.environ.copy()
    env['HEROKU_API_KEY'] = heroku_api_key
    subprocess.run(['heroku', 'auth:token'], input=heroku_api_key, text=True, env=env)
    subprocess.run(['heroku', 'create', app_name], env=env)
    subprocess.run(['heroku', 'git:remote', '-a', app_name], env=env)
    subprocess.run(['git', 'push', 'heroku', 'master'], env=env)
    
    # Go back to the original directory
    os.chdir('..')
    
    update.message.reply_text('Deployment started!')

def check_status(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or 'app_name' not in user_sessions[user_id] or 'heroku_api_key' not in user_sessions[user_id]:
        update.message.reply_text('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    app_name = user_sessions[user_id]['app_name']
    heroku_api_key = user_sessions[user_id]['heroku_api_key']
    env = os.environ.copy()
    env['HEROKU_API_KEY'] = heroku_api_key

    status = subprocess.run(['heroku', 'ps', '-a', app_name], capture_output=True, text=True, env=env)
    update.message.reply_text(f'Status of {app_name}:\n{status.stdout}')

def get_logs(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or 'app_name' not in user_sessions[user_id] or 'heroku_api_key' not in user_sessions[user_id]:
        update.message.reply_text('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    app_name = user_sessions[user_id]['app_name']
    heroku_api_key = user_sessions[user_id]['heroku_api_key']
    env = os.environ.copy()
    env['HEROKU_API_KEY'] = heroku_api_key

    logs = subprocess.run(['heroku', 'logs', '--tail', '-a', app_name], capture_output=True, text=True, env=env)
    update.message.reply_text(f'Logs of {app_name}:\n{logs.stdout}')

def exec_command(update, context):
    user_id = str(update.message.from_user.id)
    if user_id != OWNER_ID:
        update.message.reply_text('You do not have permission to use this command.')
        return
    
    command_key = context.args[0]
    if command_key in predefined_commands:
        command = predefined_commands[command_key]
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        update.message.reply_text(f'Command executed. Output:\n{result.stdout}')
    else:
        update.message.reply_text('Command not found.')

def run_telethon_script(update, context):
    user_id = str(update.message.from_user.id)
    if user_id != OWNER_ID:
        update.message.reply_text('You do not have permission to use this command.')
        return
    
    message = ' '.join(context.args)
    with telethon_client:
        telethon_client.loop.run_until_complete(send_telethon_message(message))
    update.message.reply_text(f'Telethon script executed with message: {message}')

async def send_telethon_message(message):
    await telethon_client.send_message('me', message)

def handle_ai_request(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    if 'openai_api_key' not in user_sessions[user_id]:
        user_sessions[user_id]['openai_api_key'] = OPENAI_API_KEY

    openai.api_key = user_sessions[user_id]['openai_api_key']
    user_request = update.message.text.replace('dk ai', '').strip()
    
    try:
        if user_request.lower().startswith('image:'):
            description = user_request[len('image:'):].strip()
            response = openai.Image.create(
                prompt=description,
                n=1,
                size="512x512"
            )
            image_url = response['data'][0]['url']
            update.message.reply_text(f'Here is the generated image: {image_url}')
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": user_request}]
            )
            text = response.choices[0].message['content'].strip()
            update.message.reply_text(f'AI Response: {text}')
    except Exception as e:
        update.message.reply_text(f'Error: {str(e)}')

def set_openai(update, context):
    user_id = update.message.from_user.id
    openai_api_key = context.args[0]
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['openai_api_key'] = openai_api_key
    update.message.reply_text('OpenAI API key set.')

def handle_message(update, context):
    if 'dk ai' in update.message.text.lower():
        handle_ai_request(update, context)
    else:
        # Process other commands here if necessary
        pass

# Add handlers to the dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("setheroku", set_heroku, pass_args=True))
dispatcher.add_handler(CommandHandler("setappname", set_app_name, pass_args=True))
dispatcher.add_handler(CommandHandler("deploy", deploy, pass_args=True))
dispatcher.add_handler(CommandHandler("status", check_status))
dispatcher.add_handler(CommandHandler("logs", get_logs))
dispatcher.add_handler(CommandHandler("exec", exec_command, pass_args=True))
dispatcher.add_handler(CommandHandler("runtelethon", run_telethon_script, pass_args=True))
dispatcher.add_handler(CommandHandler("setopenai", set_openai, pass_args=True))
dispatcher.add_handler(CallbackQueryHandler(button))

# Add a message handler to handle commands in groups and private chats
dispatcher.add_handler(MessageHandler(Filters.text & (Filters.chat_type.groups | Filters.chat_type.private), handle_message))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return 'OK'

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': int(os.environ.get('PORT', 5000))}).start()
    
    # Start the Telegram bot
    updater.start_polling()
    updater.idle()



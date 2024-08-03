import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import openai
from dotenv import load_dotenv
import subprocess
import github  # Ensure github.py is in the same directory

# Load environment variables from .env file
load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN provided. Please set the BOT_TOKEN environment variable.")
if not OWNER_ID:
    raise ValueError("No OWNER_ID provided. Please set the OWNER_ID environment variable.")
if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH must be set for Pyrogram.")
if not OPENAI_API_KEY:
    raise ValueError("No OPENAI_API_KEY provided. Please set the OPENAI_API_KEY environment variable.")

openai.api_key = OPENAI_API_KEY

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_sessions = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = [
        [InlineKeyboardButton("Heroku Deployment", callback_data='deploy')],
        [InlineKeyboardButton("Run Pyrogram Script", callback_data='run_pyrogram_script')],
        [InlineKeyboardButton("AI", callback_data='ai')],
        [InlineKeyboardButton("GitHub", callback_data='github')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply("Hello! I am your deployment bot. Choose an option:", reply_markup=reply_markup)

@app.on_callback_query()
async def button(client, callback_query):
    if callback_query.data == 'deploy':
        await callback_query.message.edit("You selected Heroku Deployment. Use /help to see available commands.")
    elif callback_query.data == 'run_pyrogram_script':
        await callback_query.message.edit("You selected to run a Pyrogram script. Use 'dk ai' followed by your request to run the script.")
    elif callback_query.data == 'ai':
        await callback_query.message.edit("You selected AI. Use 'dk ai' followed by your request to interact with AI.")
    elif callback_query.data == 'github':
        await callback_query.message.edit("You selected GitHub. Use the available GitHub commands to interact with GitHub.")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply('/start - Start the bot and see options\n'
                        '/setopenai <api_key> - Set the OpenAI API key\n'
                        '/setheroku <api_key> - Set the Heroku API key\n'
                        '/setappname <app_name> - Set the Heroku app name\n'
                        '/setgithub <api_key> - Set the GitHub API key\n'  # Added this line
                        '/deploy <repo_url> - Deploy the specified repository to Heroku\n'
                        '/status - Check the status of the latest deployment\n'
                        '/logs - Retrieve logs from Heroku\n'
                        '/exec <command> - Execute a predefined command\n'
                        '/ai <query> - Interact with GPT-4 and generate images using OpenAI\n'
                        '/github - Interact with GitHub (Use /github_help for GitHub commands)')

@app.on_message(filters.command("setopenai") & filters.user(OWNER_ID))
async def set_openai(client, message):
    user_id = message.from_user.id
    openai_api_key = message.text.split(' ', 1)[1]
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['openai_api_key'] = openai_api_key
    openai.api_key = openai_api_key  # Update the API key for current requests
    await message.reply('OpenAI API key set.')

@app.on_message(filters.command("setheroku") & filters.user(OWNER_ID))
async def set_heroku(client, message):
    user_id = message.from_user.id
    heroku_api_key = message.text.split(' ', 1)[1]
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['heroku_api_key'] = heroku_api_key
    await message.reply('Heroku API key set.')

@app.on_message(filters.command("setappname") & filters.user(OWNER_ID))
async def set_app_name(client, message):
    user_id = message.from_user.id
    app_name = message.text.split(' ', 1)[1]
    if user_id not in user_sessions:
        await message.reply('Please set your Heroku API key first using /setheroku command.')
        return
    user_sessions[user_id]['app_name'] = app_name
    await message.reply(f'Heroku app name set to {app_name}.')

@app.on_message(filters.command("setgithub") & filters.user(OWNER_ID))  # Added this function
async def set_github(client, message):
    user_id = message.from_user.id
    github_api_key = message.text.split(' ', 1)[1]
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['github_api_key'] = github_api_key
    github.HEADERS["Authorization"] = f"token {github_api_key}"  # Update the GitHub API key
    await message.reply('GitHub API key set.')

@app.on_message(filters.command("deploy") & filters.user(OWNER_ID))
async def deploy(client, message):
    user_id = message.from_user.id
    repo_url = message.text.split(' ', 1)[1]  # Example: "https://github.com/user/repo"
    
    if user_id not in user_sessions:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    app_name = user_sessions[user_id].get('app_name')
    heroku_api_key = user_sessions[user_id].get('heroku_api_key')

    if not app_name or not heroku_api_key:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    try:
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
        
        await message.reply('Deployment started!')
    except Exception as e:
        await message.reply(f'Error during deployment: {str(e)}')

@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def check_status(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    app_name = user_sessions[user_id].get('app_name')
    heroku_api_key = user_sessions[user_id].get('heroku_api_key')

    if not app_name or not heroku_api_key:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    try:
        env = os.environ.copy()
        env['HEROKU_API_KEY'] = heroku_api_key

        status = subprocess.run(['heroku', 'ps', '-a', app_name], capture_output=True, text=True, env=env)
        await message.reply(f'Status of {app_name}:\n{status.stdout}')
    except Exception as e:
        await message.reply(f'Error checking status: {str(e)}')

@app.on_message(filters.command("logs") & filters.user(OWNER_ID))
async def get_logs(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    app_name = user_sessions[user_id].get('app_name')
    heroku_api_key = user_sessions[user_id].get('heroku_api_key')

    if not app_name or not heroku_api_key:
        await message.reply('Please set your Heroku API key and app name first using /setheroku and /setappname commands.')
        return

    try:
        env = os.environ.copy()
        env['HEROKU_API_KEY'] = heroku_api_key

        logs = subprocess.run(['heroku', 'logs', '--tail', '-a', app_name], capture_output=True, text=True, env=env)
        await message.reply(f'Logs of {app_name}:\n{logs.stdout}')
    except Exception as e:
        await message.reply(f'Error retrieving logs: {str(e)}')

@app.on_message(filters.command("exec") & filters.user(OWNER_ID))
async def exec_command(client, message):
    command = message.text.split(' ', 1)[1]
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        await message.reply(f'Command executed. Output:\n{result.stdout}')
    except Exception as e:
        await message.reply(f'Error executing command: {str(e)}')

@app.on_message(filters.command("github_help") & filters.user(OWNER_ID))
async def github_help(client, message):
    await github.github_help(client, message)

@app.on_message(filters.command("clone") & filters.user(OWNER_ID))
async def clone_repo(client, message):
    await github.clone_repo(client, message)

@app.on_message(filters.command("create_repo") & filters.user(OWNER_ID))
async def create_repo(client, message):
    await github.create_repo(client, message)

@app.on_message(filters.command("commit") & filters.user(OWNER_ID))
async def commit_changes(client, message):
    await github.commit_changes(client, message)

@app.on_message(filters.command("push") & filters.user(OWNER_ID))
async def push_changes(client, message):
    await github.push_changes(client, message)

@app.on_message(filters.command("pull") & filters.user(OWNER_ID))
async def pull_changes(client, message):
    await github.pull_changes(client, message)

@app.on_message(filters.command("view_file") & filters.user(OWNER_ID))
async def view_file(client, message):
    await github.view_file(client, message)

@app.on_message(filters.command("edit_file") & filters.user(OWNER_ID))
async def edit_file(client, message):
    await github.edit_file(client, message)

@app.on_message(filters.command("add_file") & filters.user(OWNER_ID))
async def add_file(client, message):
    await github.add_file(client, message)

@app.on_message(filters.command("remove_file") & filters.user(OWNER_ID))
async def remove_file(client, message):
    await github.remove_file(client, message)

@app.on_message(filters.command("list_repos") & filters.user(OWNER_ID))
async def list_repos(client, message):
    await github.list_repos(client, message)

@app.on_message(filters.text & (filters.group | filters.private))
async def handle_message(client, message):
    user_id = message.from_user.id
    if user_id == OWNER_ID and 'dk ai' in message.text.lower():
        await handle_ai_request(client, message)

async def handle_ai_request(client, message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    if 'openai_api_key' not in user_sessions[user_id]:
        user_sessions[user_id]['openai_api_key'] = OPENAI_API_KEY

    openai.api_key = user_sessions[user_id]['openai_api_key']
    user_request = message.text.replace('dk ai', '').strip()

    try:
        if user_request.lower().startswith('image:'):
            description = user_request[len('image:'):].strip()
            response = openai.Image.create(
                prompt=description,
                n=1,
                size="512x512"
            )
            image_url = response['data'][0]['url']
            await message.reply_photo(image_url)
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": user_request}]
            )
            text = response.choices[0].message['content'].strip()
            await message.reply(f"Deepanshu's assistant: {text}")
    except Exception as e:
        await message.reply(f'Error: {str(e)}')

if __name__ == '__main__':
    app.run()
        

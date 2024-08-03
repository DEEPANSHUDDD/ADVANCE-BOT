import os
import requests
import base64
from pyrogram import Client, filters
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OWNER_ID = int(os.getenv('OWNER_ID'))
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    raise ValueError("No GITHUB_TOKEN provided. Please set the GITHUB_TOKEN environment variable.")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

@app.on_message(filters.command("github_help") & filters.user(OWNER_ID))
async def github_help(client, message):
    await message.reply('/clone <repo_url> - Clone a GitHub repository\n'
                        '/create_repo <repo_name> - Create a new GitHub repository\n'
                        '/commit <repo_path> <commit_message> - Commit changes in a repository\n'
                        '/push <repo_path> - Push changes to GitHub\n'
                        '/pull <repo_path> - Pull changes from GitHub\n'
                        '/view_file <repo> <path> - View a file in a GitHub repository\n'
                        '/edit_file <repo> <path> <content> - Edit a file in a GitHub repository\n'
                        '/add_file <repo> <path> <content> - Add a new file to a GitHub repository\n'
                        '/remove_file <repo> <path> - Remove a file from a GitHub repository\n'
                        '/list_repos - List all repositories')

@app.on_message(filters.command("clone") & filters.user(OWNER_ID))
async def clone_repo(client, message):
    repo_url = message.text.split(' ', 1)[1]
    try:
        subprocess.run(['git', 'clone', repo_url])
        await message.reply('Repository cloned successfully.')
    except Exception as e:
        await message.reply(f'Error cloning repository: {str(e)}')

@app.on_message(filters.command("create_repo") & filters.user(OWNER_ID))
async def create_repo(client, message):
    repo_name = message.text.split(' ', 1)[1]
    try:
        subprocess.run(['gh', 'repo', 'create', repo_name, '--public'])
        await message.reply('Repository created successfully.')
    except Exception as e:
        await message.reply(f'Error creating repository: {str(e)}')

@app.on_message(filters.command("commit") & filters.user(OWNER_ID))
async def commit_changes(client, message):
    parts = message.text.split(' ', 2)
    repo_path = parts[1]
    commit_message = parts[2]
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', commit_message])
        os.chdir('..')
        await message.reply('Changes committed successfully.')
    except Exception as e:
        await message.reply(f'Error committing changes: {str(e)}')

@app.on_message(filters.command("push") & filters.user(OWNER_ID))
async def push_changes(client, message):
    repo_path = message.text.split(' ', 1)[1]
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'push'])
        os.chdir('..')
        await message.reply('Changes pushed to GitHub successfully.')
    except Exception as e:
        await message.reply(f'Error pushing changes: {str(e)}')

@app.on_message(filters.command("pull") & filters.user(OWNER_ID))
async def pull_changes(client, message):
    repo_path = message.text.split(' ', 1)[1]
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'pull'])
        os.chdir('..')
        await message.reply('Changes pulled from GitHub successfully.')
    except Exception as e:
        await message.reply(f'Error pulling changes: {str(e)}')

@app.on_message(filters.command("view_file") & filters.user(OWNER_ID))
async def view_file(client, message):
    parts = message.text.split(' ', 2)
    repo = parts[1]
    path = parts[2]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        file_content = base64.b64decode(response.json()['content']).decode('utf-8')
        await message.reply(f"Content of {path}:\n{file_content}")
    else:
        await message.reply(f"Error fetching file: {response.json().get('message')}")

@app.on_message(filters.command("edit_file") & filters.user(OWNER_ID))
async def edit_file(client, message):
    parts = message.text.split(' ', 3)
    repo = parts[1]
    path = parts[2]
    content = parts[3]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    # Get the file's SHA
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        await message.reply(f"Error fetching file: {response.json().get('message')}")
        return

    sha = response.json()['sha']

    data = {
        "message": f"Edit {path} via Telegram bot",
        "committer": {
            "name": "Telegram Bot",
            "email": "bot@example.com"
        },
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }

    response = requests.put(url, json=data, headers=HEADERS)
    if response.status_code == 200:
        await message.reply(f"File {path} edited successfully.")
    else:
        await message.reply(f"Error editing file: {response.json().get('message')}")

@app.on_message(filters.command("add_file") & filters.user(OWNER_ID))
async def add_file(client, message):
    parts = message.text.split(' ', 3)
    repo = parts[1]
    path = parts[2]
    content = parts[3]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    data = {
        "message": f"Add {path} via Telegram bot",
        "committer": {
            "name": "Telegram Bot",
            "email": "bot@example.com"
        },
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }

    response = requests.put(url, json=data, headers=HEADERS)
    if response.status_code == 201:
        await message.reply(f"File {path} added successfully.")
    else:
        await message.reply(f"Error adding file: {response.json().get('message')}")

@app.on_message(filters.command("remove_file") & filters.user(OWNER_ID))
async def remove_file(client, message):
    parts = message.text.split(' ', 2)
    repo = parts[1]
    path = parts[2]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    # Get the file's SHA
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        await message.reply(f"Error fetching file: {response.json().get('message')}")
        return

    sha = response.json()['sha']

    data = {
        "message": f"Remove {path} via Telegram bot",
        "committer": {
            "name": "Telegram Bot",
            "email": "bot@example.com"
        },
        "sha": sha
    }

    response = requests.delete(url, json=data, headers=HEADERS)
    if response.status_code == 200:
        await message.reply(f"File {path} removed successfully.")
    else:
        await message.reply(f"Error removing file: {response.json().get('message')}")

@app.on_message(filters.command("list_repos") & filters.user(OWNER_ID))
async def list_repos(client, message):
    url = "https://api.github.com/user/repos"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        repos = response.json()
        repo_list = "\n".join([repo['full_name'] for repo in repos])
        await message.reply(f"Your repositories:\n{repo_list}")
    else:
        await message.reply(f"Error fetching repositories: {response.json().get('message')}")

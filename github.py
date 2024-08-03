import os
import requests
import base64
import subprocess
from pyrogram import Client, filters
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OWNER_ID = int(os.getenv('OWNER_ID'))
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

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

async def clone_repo(client, message):
    repo_url = message.text.split(' ', 1)[1]
    try:
        result = subprocess.run(['git', 'clone', repo_url], capture_output=True, text=True)
        await message.reply('Repository cloned successfully.')
    except Exception as e:
        await message.reply(f'Error cloning repository: {str(e)}')

async def create_repo(client, message):
    repo_name = message.text.split(' ', 1)[1]
    try:
        response = requests.post(
            'https://api.github.com/user/repos',
            headers=HEADERS,
            json={"name": repo_name}
        )
        if response.status_code == 201:
            await message.reply('Repository created successfully.')
        else:
            await message.reply(f'Error creating repository: {response.json().get("message")}')
    except Exception as e:
        await message.reply(f'Error creating repository: {str(e)}')

async def commit_changes(client, message):
    parts = message.text.split(' ', 2)
    repo_path = parts[1]
    commit_message = parts[2]
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'add', '.'])
        result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
        os.chdir('..')
        await message.reply('Changes committed successfully.')
    except Exception as e:
        await message.reply(f'Error committing changes: {str(e)}')

async def push_changes(client, message):
    repo_path = message.text.split(' ', 1)[1]
    try:
        os.chdir(repo_path)
        result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        os.chdir('..')
        await message.reply('Changes pushed to GitHub successfully.')
    except Exception as e:
        await message.reply(f'Error pushing changes: {str(e)}')

async def pull_changes(client, message):
    repo_path = message.text.split(' ', 1)[1]
    try:
        os.chdir(repo_path)
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        os.chdir('..')
        await message.reply('Changes pulled from GitHub successfully.')
    except Exception as e:
        await message.reply(f'Error pulling changes: {str(e)}')

async def view_file(client, message):
    parts = message.text.split(' ', 2)
    repo = parts[1]
    path = parts[2]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            file_content = base64.b64decode(response.json()['content']).decode('utf-8')
            await message.reply(f"Content of {path}:\n{file_content}")
        else:
            await message.reply(f"Error fetching file: {response.json().get('message')}")
    except Exception as e:
        await message.reply(f'Error viewing file: {str(e)}')

async def edit_file(client, message):
    parts = message.text.split(' ', 3)
    repo = parts[1]
    path = parts[2]
    content = parts[3]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    try:
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
    except Exception as e:
        await message.reply(f'Error editing file: {str(e)}')

async def add_file(client, message):
    parts = message.text.split(' ', 3)
    repo = parts[1]
    path = parts[2]
    content = parts[3]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    try:
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
    except Exception as e:
        await message.reply(f'Error adding file: {str(e)}')

async def remove_file(client, message):
    parts = message.text.split(' ', 2)
    repo = parts[1]
    path = parts[2]

    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    try:
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
    except Exception as e:
        await message.reply(f'Error removing file: {str(e)}')

async def list_repos(client, message):
    url = "https://api.github.com/user/repos"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            repos = response.json()
            repo_list = "\n".join([repo['full_name'] for repo in repos])
            await message.reply(f"Your repositories:\n{repo_list}")
        else:
            await message.reply(f"Error fetching repositories: {response.json().get('message')}")
    except Exception as e:
        await message.reply(f'Error listing repositories: {str(e)}')

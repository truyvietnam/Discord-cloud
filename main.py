from flask import Flask, Response, abort, render_template_string, url_for
import discord
import os
import requests
from discord.ext import commands
import math
import json
import threading
import io
from dotenv import load_dotenv

app = Flask(__name__)

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
USER_TOKEN = os.getenv('USER_TOKEN')

MAX_CHUNK_SIZE = 25 * 1024 * 1024  # 25MB in bytes
UPLOADS_FILE = 'uploads.json'

def fetch_links(links):
    converted_links = []
    for link in links:
        converted_links.append(link.replace("'", '"'))

    if len(converted_links) < 40:
        response = requests.post(
            "https://discord.com/api/v9/attachments/refresh-urls",
        json={"attachment_urls": converted_links},
        headers={"Authorization": USER_TOKEN}
    )
        return response.json()['refreshed_urls']
    else:
        new_refreshed_links = []
        for i in range(0, len(converted_links), 40):
            response = requests.post(
            "https://discord.com/api/v9/attachments/refresh-urls",
                json={"attachment_urls": converted_links[i:i+40]},
                headers={"Authorization": USER_TOKEN})
            new_refreshed_links.extend(response.json()['refreshed_urls'])
        
        return new_refreshed_links
    

    
def refresh_link(file: str):
    try:
        if os.path.exists(UPLOADS_FILE) and os.path.getsize(UPLOADS_FILE) > 0:
            with open(UPLOADS_FILE, 'r') as json_file:
                uploads_data = json.load(json_file)
        else:
            uploads_data = {}
    except json.JSONDecodeError:
        uploads_data = {}

    new_chunk_links = []
    file_need_to_refresh = uploads_data[file]
    links_count = len(file_need_to_refresh['chunk_links'])
    new_links = fetch_links(file_need_to_refresh['chunk_links'])

    for i in range(links_count):
        new_chunk_links.append(new_links[i]['refreshed'])

    
    uploads_data[file]['chunk_links'] = new_chunk_links

    with open(UPLOADS_FILE, 'w') as json_file:
        json.dump(uploads_data, json_file, indent=4)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def upload(ctx, file_path: str):
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            await ctx.send("File not found. Please check the file path.")
            return

        file_size = os.path.getsize(file_path)
        chunk_count = math.ceil(file_size / MAX_CHUNK_SIZE)
        file_name = os.path.basename(file_path)

        await ctx.send(f"Uploading file: {file_name}")
        await ctx.send(f"File size: {file_size / (1024 * 1024):.2f} MB")
        await ctx.send(f"Number of chunks: {chunk_count}")

        chunk_links = []

        with open(file_path, 'rb') as file:
            for i in range(chunk_count):
                chunk = file.read(MAX_CHUNK_SIZE)
                chunk_io = io.BytesIO(chunk)
                chunk_io.seek(0)
                chunk_file = discord.File(fp=chunk_io, filename=f"{file_name}.part{i+1}")
                message = await ctx.send(f"Uploading chunk {i+1}/{chunk_count}", file=chunk_file)
                chunk_links.append(message.attachments[0].url)

        await ctx.send("File upload complete!")

        # Store file information in JSON
        upload_info = {
            "file_name": file_name,
            "total_chunks": chunk_count,
            "chunk_links": chunk_links
        }

        # Load existing data
        try:
            if os.path.exists(UPLOADS_FILE) and os.path.getsize(UPLOADS_FILE) > 0:
                with open(UPLOADS_FILE, 'r') as json_file:
                    uploads_data = json.load(json_file)
            else:
                uploads_data = {}
        except json.JSONDecodeError:
            uploads_data = {}

        # Add new upload info
        uploads_data[file_name] = upload_info

        # Save updated data
        with open(UPLOADS_FILE, 'w') as json_file:
            json.dump(uploads_data, json_file, indent=4)

        await ctx.send(f"File information stored in {UPLOADS_FILE}")

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

def stream_file(chunk_links):
    for link in chunk_links:
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            yield from response.iter_content(chunk_size=8192)
        else:
            abort(500, description=f"Failed to download chunk from {link}")

@app.route('/')
def index():
    try:
        with open(UPLOADS_FILE, 'r') as json_file:
            uploads_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        uploads_data = {}

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Available Files</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { margin-bottom: 10px; }
            a { color: #1a73e8; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>Available Files for Download</h1>
        <ul>
        {% for filename in files %}
            <li><a href="{{ url_for('download_file', filename=filename) }}">{{ filename }}</a></li>
        {% endfor %}
        </ul>
    </body>
    </html>
    '''
    return render_template_string(html, files=uploads_data.keys())

@app.route('/download/<filename>')
def download_file(filename):
    try:
        refresh_link(filename)
        # Load the uploads data
        with open(UPLOADS_FILE, 'r') as json_file:
            uploads_data = json.load(json_file)
        
        # Check if the file exists in our records
        if filename not in uploads_data:
            abort(404, description="File not found")
        
        file_info = uploads_data[filename]
        chunk_links = file_info['chunk_links']
        
        # Stream the file
        return Response(
            stream_file(chunk_links),
            content_type='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        abort(500, description=str(e))

def run_flask():
    app.run(debug=False, use_reloader=False)

def run_bot():
    bot.run(TOKEN)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_bot)

    flask_thread.start()
    bot_thread.start()

    flask_thread.join()
    bot_thread.join()
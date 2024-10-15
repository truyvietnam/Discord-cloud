from flask import Flask, Response, abort, render_template, url_for, request, redirect, flash
import os
import requests
import math
import json
import io
from dotenv import load_dotenv
import logging

app = Flask(__name__)

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
        #for some reason I cannot get too much link refreshed so I just choose 40
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

    return render_template('index.html', files=uploads_data.keys())

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        with open(UPLOADS_FILE, 'r') as json_file:
            uploads_data = json.load(json_file)
        
        if filename in uploads_data:
            del uploads_data[filename]
            
            with open(UPLOADS_FILE, 'w') as json_file:
                json.dump(uploads_data, json_file, indent=4)
            
            flash(f"File '{filename}' has been deleted.")
        else:
            flash(f"File '{filename}' not found.")
    
    except Exception as e:
        flash(f"An error occurred while deleting the file: {str(e)}")
    
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    if file:
        filename = file.filename
        chunk_links = []
        chunk_number = 1
        current_chunk = io.BytesIO()
        current_chunk_size = 0

        logging.info(f"Starting upload for file: {filename}")

        while True:
            # Read 1MB at a time
            chunk = file.read(1024 * 1024)
            if not chunk:
                # End of file
                if current_chunk_size > 0:
                    # Upload the last chunk if there's any data
                    current_chunk.seek(0)
                    chunk_link = upload_chunk_to_discord(current_chunk, f"{filename}.part{chunk_number}", chunk_number)
                    if chunk_link:
                        chunk_links.append(chunk_link)
                        logging.info(f"Uploaded final chunk {chunk_number}: {chunk_link}")
                    else:
                        flash(f"Failed to upload final chunk {chunk_number}")
                        return redirect(url_for('index'))
                break

            current_chunk.write(chunk)
            current_chunk_size += len(chunk)

            if current_chunk_size >= MAX_CHUNK_SIZE:
                # Upload the current chunk
                current_chunk.seek(0)
                chunk_link = upload_chunk_to_discord(current_chunk, f"{filename}.part{chunk_number}", chunk_number)
                if chunk_link:
                    chunk_links.append(chunk_link)
                    logging.info(f"Uploaded chunk {chunk_number}: {chunk_link}")
                else:
                    flash(f"Failed to upload chunk {chunk_number}")
                    return redirect(url_for('index'))

                # Reset for the next chunk
                chunk_number += 1
                current_chunk = io.BytesIO()
                current_chunk_size = 0

        # Store file information in JSON
        upload_info = {
            "file_name": filename,
            "total_chunks": chunk_number,
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
        uploads_data[filename] = upload_info

        # Save updated data
        with open(UPLOADS_FILE, 'w') as json_file:
            json.dump(uploads_data, json_file, indent=4)

        flash(f"File '{filename}' uploaded successfully")
        logging.info(f"File information stored in {UPLOADS_FILE}")

        return redirect(url_for('index'))

def upload_chunk_to_discord(file_data, filename, chunk_number):
    url = f"https://discord.com/api/v9/channels/{os.getenv('UPLOAD_CHANNEL_ID')}/messages"
    headers = {
        "Authorization": f"Bot {TOKEN}"
    }
    files = {
        'file': (filename, file_data, 'application/octet-stream')
    }
    data = {
        "content": f"Uploading chunk {chunk_number}"
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()['attachments'][0]['url']
    except requests.RequestException as e:
        logging.error(f"Error uploading chunk: {str(e)}")
        return None

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

if __name__ == '__main__':
    app.secret_key = '1234567890'  # Set a secret key for flash messages
    run_flask()

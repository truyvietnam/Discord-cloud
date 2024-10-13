# Discord-cloud
Chatgpt made this shit

# What is this
This python code use discord as storage.

Upload file from your local storage, split it into 25MB (limit that discord bot can upload) chunks and upload to discord, store the download links to each chunks

Renew your download links every time you download thank to https://github.com/ShufflePerson/Discord_CDN

# How to use (on window computer)
1. Install python
2. Create a discord bot (IMPORTANT: toggle Message Content Intent)
3. Download as zip and extract it to somewhere
4. Open Command Prompt on folder that you extracted it and type ``pip install -r req.txt`` to install python package
5. Type ``python main.py`` to start the website on local ip and start the bot
6. Add your discord bot to somewhere and type ``!upload <YOUR_FILE_PATH>``
   
There download links will be stored in ``uploads.json``

You can open browser and go to your localhost with port 5000 to download file

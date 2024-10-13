# Discord-cloud
Chatgpt made this shit

# What is this
This python code use discord as storage.

Upload file from your local storage, split it into 25MB (limit that discord bot can upload) chunks and upload to discord, store the download links to each chunks

Renew your download links every time you download thank to https://github.com/ShufflePerson/Discord_CDN

# Warning
This has high risk of being banned and discord can delete your files so this is only use for fun and you shouldn't upload important file

Also you should create a new discord account, make a bot and get the bot and that acc token

# How to use (on window computer)
1. Install python
2. Create a discord bot (IMPORTANT: toggle Message Content Intent)
3. Copy your discord bot token and get a random discord user token (for renew links), fill it in ``.env`` file
4. Download as zip and extract it to somewhere
5. Open Command Prompt on folder that you extracted it and type ``pip install -r req.txt`` to install python package
6. Type ``python main.py`` to start the website on local ip and start the bot
7. Add your discord bot to somewhere and type ``!upload <YOUR_FILE_PATH>``
   
Those download links will be stored in ``uploads.json``

You can open a browser and go to your localhost with port 5000 to download files

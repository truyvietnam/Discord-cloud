# Discord-cloud
Chatgpt made this shit

# What is this
This python script use discord as a cloud storage.

Upload file from your local storage, split it into 25MB (limit that discord bot can upload) chunks and upload to discord, store the download links to each chunks

Renew your download links every time you download thank to https://github.com/ShufflePerson/Discord_CDN

# Warning
This has high risk of being banned and discord can delete your files so this is only use for fun and you shouldn't upload important file

Also you should create a new discord account, make a bot and get the bot and that acc token

# How to use
1. Create a new discord bot and user, get their tokens
2. Get the bot into a server, and get channel id in that server
3. Put tokens and channel id into ``.env`` file
4. Install requirement package
5. Run the python script

Those download links will be stored in ``uploads.json``

You can open a browser and go to your localhost with port 5000 to download files, upload file and delete file (only remove from uploads.json)

# Demo
https://maple-road-dogwood.glitch.me/

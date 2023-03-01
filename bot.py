#All of our imports as usual
import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import io
import aiohttp

intents = discord.Intents.default()
intents.message_content = True

#Create our Discord bot object to interact with API
client = discord.Client(intents=intents)

#Quick helper method to help with program arg creation
def readFullFile(fileName):
    file = open(fileName, mode='r')
    returnStr = file.read()
    file.close()
    return returnStr

# ========================================================
# = PROGRAM VARIABLES
# ========================================================

#Securely load Tokens from another file
#This wants type hints or it gets upset when accessing
tokens: dict = json.loads(readFullFile('tokens.json'))

var = {"Prefix": ".",
       "Admin": [299335413229944833, 187294722581069824]
       }

STATE = 1

responsesDict = {}

# ========================================================
# = PROGRAM FUNCTIONS
# ========================================================

def setKeywords(updatedDict):
    global responsesDict
    responsesDict = updatedDict

def getKeywords():
    global responsesDict
    return responsesDict

def reloadResponses():
    global programArgs, PROGRAM_STATE

    print("Reloading responses")

    #Authenticate to access Google Sheets first
    scope = ['https://www.googleapis.com/auth/drive']
    #TODO change this before push to prod
    key = ServiceAccountCredentials.from_json_keyfile_name("key.json")
    googleClient = gspread.authorize(key)

    #Open our Google Sheets with all the event data
    dataSheet = googleClient.open('DiscordBotResponses').sheet1

    #Populate our program with data from Google Sheets
    data = {}
    for i in range(2, len(dataSheet.col_values(1)) + 1):
        row = dataSheet.row_values(i)
        keyword = row[0].lower()
        type = row[1]
        response = row[2]
        imageLink = None
        if type == "Image":
            imageLink = row[3]

        data[keyword] = {"response": response, "link": imageLink}

    setKeywords(data)
    return "Data has been re-loaded"

def ping():
    return f"Bong! Response time: {str(round(client.latency * 1000,2))}ms"

def setState(newState):
    global STATE
    STATE = newState

def executeAdminCommand(msgCont):
    if msgCont == "ping":
        return ping()
    elif msgCont == "reload":
        return reloadResponses()
    elif msgCont == "on":
        setState(1)
        return None
    elif msgCont == "off":
        setState(0)
        return None

# ========================================================
# = DISCORD API STARTUP EVENT
# ========================================================

@client.event
async def on_ready():
    reloadResponses()
    setState(1)
    print('Bot is online & listening.')

# ========================================================
# = DISCORD API MESSAGE EVENT
# ========================================================

@client.event
async def on_message(message):
    
    #Ensure the bot doesn't respond to itself
    if message.author == client.user:
        return

    #Execute admin commands
    if message.content[0] == var["Prefix"] and message.author.id in var["Admin"]:
        response = executeAdminCommand(message.content[1:])
        if response is not None:
            await message.channel.send(response)
        return

    #Respond with fun stuff

    for word in getKeywords():
        if word in message.content.lower():
            response = getKeywords()[word]["response"]
            imageLink = getKeywords()[word]["link"]
            if imageLink is not None:
                async with aiohttp.ClientSession() as session:
                    async with session.get(imageLink) as resp:
                        if resp.status != 200:
                            await message.channel.send('Could not download file.')
                        data = io.BytesIO(await resp.read())
                        await message.channel.send(response)
                        await message.channel.send(file=discord.File(data, "file.png"))
            else:
                await message.channel.send(response)
            return

client.run(tokens["PROD"])

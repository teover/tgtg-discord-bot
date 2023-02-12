from tgtg import TgtgClient

import discord
from discord import Intents
from discord.ext import tasks, commands

import datetime
import time
import pickle

from settings import *

bot = commands.Bot(command_prefix='!', intents=Intents.all(), case_insensitive=True)

STORE_PING_COOLDOWN_HOURS_DEFAULT = 8

startup_timestamp = datetime.datetime.now()

user_stores_dict = {}
user_cooldown_dict = {}


with open('user_cooldown_dict.pkl', 'rb') as f:
    user_cooldown_dict = pickle.load(f)

with open('user_stores_dict.pkl', 'rb') as f:
    user_stores_dict = pickle.load(f)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    my_cog = MyCog(bot)
    my_cog.printer.start()

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.index = 0
        self.bot = bot
        self.channel = bot.get_channel(ID_TGTG_CHANNEL)
        self.storeAddWaitQueue = []


    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=60.0)
    async def printer(self):
        print(self.index)


        out_str = "```"
        mention_str = ''
        client = TgtgClient(access_token=credentials['access_token'], refresh_token=credentials['refresh_token'], user_id=credentials['user_id'], cookie=credentials['cookie'])
        items = client.get_items()


        for item in items:
            out_str += f"{item['store']['store_name']}, Tilgjengelig: {item['items_available']}\n"
            for user in user_stores_dict:
                for store in user_stores_dict[user]:
                    delta = user_stores_dict[user][store] - datetime.datetime.now()
                    if item['store']['store_name'] in store and item['items_available'] > 0 and int(delta.total_seconds()) < 0:
                        mention_str += f" <@{user}> {item['store']['store_name']} har lagt ut noe nytt!"
                        
                        if user_cooldown_dict[user]:
                            user_cooldown = user_cooldown_dict[user]
                        else: 
                            user_cooldown = STORE_PING_COOLDOWN_HOURS_DEFAULT

                        user_stores_dict[user][store] = (datetime.datetime.now()+ datetime.timedelta(hours=user_cooldown)) # update next ping time to x hours in the future
        out_str += '```'

        with open('user_stores_dict.pkl', 'wb') as f:
            pickle.dump(user_stores_dict, f)
        
        await self.channel.send(f'{mention_str}\n{out_str}')
        self.index += 1

    @printer.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()

@bot.command(name='add', help='Aktiverer varsel for en butikk')
async def add(ctx, store: str, store2: str = '', store3: str = ''):
    if store2:  # Update name if it is multi part
        store = f'{store} {store2}'
        if store3:
            store = f'{store} {store2} {store3}'

    if str(ctx.author.id) in user_stores_dict:
        user_stores_dict[str(ctx.author.id)][store] = datetime.datetime.now()
    else:
        user_stores_dict[str(ctx.author.id)] = {}
        user_stores_dict[str(ctx.author.id)][store] = datetime.datetime.now()


    await ctx.send(f'Lagt til varsel for {store}')

@bot.command(name='remove', help='Fjern varsel for en butikk')
async def remove(ctx, store: str, store2: str = '', store3: str = ''):
    if store3:
        store = f'{store} {store2} {store3}'
    elif store2:  # Update name if it is multi part
        store = f'{store} {store2}'


    user_stores_dict[str(ctx.author.id)][store] = (datetime.datetime.now()+ datetime.timedelta(days=1000))
    await ctx.send(f'Fjernet til varsel for {store}')

@bot.command(name='cooldown', help='Sett cooldown timer for varsling')
async def cooldown(ctx, cooldowntime: int = STORE_PING_COOLDOWN_HOURS_DEFAULT):

    user_cooldown_dict[str(ctx.author.id)] =  cooldowntime

    with open('user_cooldown_dict.pkl', 'wb') as f:
        pickle.dump(user_cooldown_dict, f)
        
    await ctx.send(f'Timer oppdatert til {cooldowntime} timer')

bot.run(TOKEN)

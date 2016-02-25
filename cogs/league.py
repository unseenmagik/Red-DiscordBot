import discord
from discord.ext import commands
import aiohttp
import asyncio
from .utils import checks
from .utils.dataIO import fileIO
from bs4 import BeautifulSoup
import logging
import random
from riotwatcher import RiotWatcher
from riotwatcher import LoLException, error_404, error_429
import py_gg
import __main__
import os

logger = logging.getLogger("__main__")

#WARNING: Tons of shitty code ahead, wear safety glasses.

class League:
    """League of Legends commands."""

    def __init__(self, bot):
        self.bot = bot
        self.champions_api_key = "f50df5f5e26458582329147ecc380f8a"
        self.riot_api_key = "f7db88da-1d63-4b5b-bc81-03730e9b3b20"
        self.riot_api = RiotWatcher(self.riot_api_key)
        py_gg.init(self.champions_api_key)
        self.champions_api = py_gg
        self.regions = ['br', 'eune', 'euw', 'lan', 'las', 'na', 'oce', 'ru', 'tr', 'jp']
        self.roles = {'adc': 'ADC', 'carry': 'ADC', 'jungle': 'Jungle', 'mid': 'Middle', 'middle': 'Middle', 'support': 'Support', 'sup': 'Support', 'top': 'Top', 'hard': 'Top', 'bot': 'ADC'}
        self.champions = fileIO("data/league/champions.json","load")
        self.champion_names = fileIO("data/league/champ_names.json","load")

    #debugging things
    @commands.command(pass_context=True, no_pm=True)
    async def jsonsort(self, ctx):
        self.champions = SortedDict(self.champions)
        print(self.champions)

    @commands.command(pass_context=True, no_pm=True)
    async def jsonload(self, ctx):
        champions = self.champions_api.champion.all()
        champs = {}
        for c in champions:
            champs[c['key']] = c['name']
        print(champs)

    @commands.group(pass_context=True)
    async def lol(self, ctx):
        """League of Legends commands."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help lol for info.")

    #commands
    @lol.command(pass_context=True, no_pm=True)
    async def status(self, ctx, region: str = None):
        if region is None:
            await self.bot.say("Todo: full server list")
        else:
            try:
                if region in self.regions:
                    server = self.riot_api.get_server_status(region=self.regions[self.regions.index(region)])
                    print(server)
                    await self.bot.say("**{}** status:\n{}: {}\n{}: {}\n{}: {}\n{}: {}\n"
                        .format(server['name'], 
                            server['services'][0]['name'], server['services'][0]['status'], 
                            server['services'][1]['name'], server['services'][1]['status'],
                            server['services'][2]['name'], server['services'][2]['status'],
                            server['services'][3]['name'], server['services'][3]['status']))
            except LoLException as e:
                if e == error_429:
                    print('We should retry in {} seconds.'.format(e.headers['Retry-After']))
 
    @lol.command(pass_context=True, no_pm=True)
    async def summoner(self, ctx, region: str, *, name: str):
        try:
            if region in self.regions:
                summoner = self.riot_api.get_summoner(name=name, region=self.regions[self.regions.index(region)])
                try:
                    league = self.riot_api.get_league(summoner_ids=[summoner["id"]], region=self.regions[self.regions.index(region)])
                    league_name = league[str(summoner["id"])][0]['tier']
                    for m in league[str(summoner["id"])][0]['entries']:
                        if str(summoner["id"]) in m['playerOrTeamId']:
                            division = m['division']
                            wins = m['wins']
                            losses = m['losses']
                            points = m['leaguePoints']
                    await self.bot.say('**ID:** {} **Lvl:** {}\n**League:** {} **Division:** {} **League points:** {}\n**Wins:** {} **Losses:** {}'
                        .format(str(summoner["id"]), str(summoner['summonerLevel']), league_name, division, points, wins, losses))
                except LoLException as e:
                    if e == error_429:
                        print('We should retry in {} seconds.'.format(e.headers['Retry-After']))
                    elif e == error_404:
                        await self.bot.say(':warning: Ranked games not found, here some normal stats instead.')
                        await self.bot.say('**ID:** {} **Lvl:** {}'.format(str(summoner["id"]), str(summoner['summonerLevel'])))
        except LoLException as e:
            if e == error_429:
                print('We should retry in {} seconds.'.format(e.headers['Retry-After']))
            elif e == error_404:
                await self.bot.say(':x: Summoner not found.')

    @lol.command(pass_context=True, no_pm=True)
    async def counters(self, ctx, role: str, *, champion: str):
        try:
            valid_roles = []
            ##role = role.lower()
            #champion = champion.lower()
            if role in self.roles:
                if champion in self.champions:
                    matchups = self.champions_api.champion.matchup(self.champions[champion])
                    for m in matchups:
                        if self.roles[role] in m['role']:
                            found = True
                            matchups = m['matchups']
                            #filtered_matchups = []
                            #for m in matchups:
                            #    if m['games'] > 100:
                            #        print(m['games'], matchups.index(m))
                            #        filtered_matchups.append(dict(matchups[matchups.index(m)]))
                            sorted_matchups = sorted(matchups, key=lambda k: float(k['statScore']))
                            message = "Best counterpicks for {} ({}):\n".format(self.champion_names[self.champions[champion]], self.roles[role]) 
                            for i in range(1, 11):
                                message += "{}. {} ({}% winrate in {} matches)\n".format(i, self.champion_names[sorted_matchups[i-1]['key']], -(sorted_matchups[i-1]['winRate']-100), sorted_matchups[i-1]['games'])
                            await self.bot.say(message)
                            break
                        else:
                            found = False
                            valid_roles.append(m['role'])
                    if found == False:
                        await self.bot.say(":warning: Counters for this position not found. Known positions are: " + ", ".join(valid_roles))
                else:
                    await self.bot.say(":warning: Can't find this champion. Do you even play LoL?")
            else:
                await self.bot.say(":warning: Unknown role. Valid roles: " + ", ".join(self.roles))
        except Exception as e:
            print(e)

    @lol.command(pass_context=True, no_pm=True)
    async def skills(self, ctx, role: str, sorting: str, *, champion: str):
        try:
            valid_roles = []
            if champion in self.champions:
                skills = self.champions_api.champion.skills(self.champions[champion], sorting)
                for m in skills:
                    if self.roles[role] in m['role']:
                        if sorting == "winning":
                            found = True
                            message = "Most winning skill order for {} (Position: {}) ({}% winrate in {} matches): \n".format(self.champion_names[self.champions[champion]], m['role'], m['winPercent'], m['games'])
                            for s in m['order']:
                                message += str(s) + ">"
                            await self.bot.say(message[:-1])
                            break
                        elif sorting == "popular":
                            found = True
                            message = "Most popular skill order for {} (Position: {}) ({}% winrate in {} matches): \n".format(self.champion_names[self.champions[champion]], m['role'], m['winPercent'], m['games'])
                            for s in m['order']:
                                message += str(s) + ">"
                            await self.bot.say(message[:-1])
                            break
                        else:
                            await self.bot.say(":warning: Unknown sorting, try 'winning' or 'popular'")
                            break
                    else:
                        found = False
                        valid_roles.append(m['role'])
                if found == False:
                    await self.bot.say(":warning: Can't find data for this position, try one of these: " + ", ".join(valid_roles))
            else:
                await self.bot.say(":warning: Can't find this champion. Do you even play LoL?")
        except Exception as e:
            print(e)

    @lol.command(pass_context=True, no_pm=True)
    async def bans(self, ctx, role: str):
        """To do later. Champions.gg api can't retrieve bans for current patch."""
        pass

    @lol.command(pass_context=True, no_pm=True)
    async def best(self, ctx, role: str):
        """self.champions_api.stats.role(self.roles[role], order="most)"""
        pass

    @lol.command(pass_context=True, no_pm=True)
    async def champion(self, ctx):
        """self.champions_api.stats.champs"""
        pass

    @lol.command(pass_context=True, no_pm=True)
    async def items(self, ctx):
        pass

    @lol.command(pass_context=True, no_pm=True)
    async def runes(self, ctx):
        pass

def check_folder():
    if not os.path.exists("data/league"):
        print("Creating data/league folder...")
        os.makedirs("data/league")

def check_file():
    champions = {'aatrox': 'Aatrox', 'ahri': 'Ahri', 'akali': 'Akali', 'alistar': 'Alistar', 'amumu': 'Amumu', 'anivia': 'Anivia', 
        'annie': 'Annie', 'ashe': 'Ashe', 'azir': 'Azir', 'bard': 'Bard', 'blitzcrank': 'Blitzcrank', 'brand': 'Brand', 'braum': 'Braum', 
        'caitlyn': 'Caitlyn', 'cassiopeia': 'Cassiopeia', 'chogath': 'Chogath', 'corki': 'Corki', 'darius': 'Darius', 'diana': 'Diana', 
        'draven': 'Draven', 'drmundo': 'DrMundo', 'ekko': 'Ekko', 'elise': 'Elise', 'evelynn': 'Evelynn', 'ezreal': 'Ezreal', 
        'fiddlesticks': 'FiddleSticks', 'fiora': 'Fiora', 'fizz': 'Fizz', 'galio': 'Galio', 'gangplank': 'Gangplank', 'garen': 'Garen', 
        'gnar': 'Gnar', 'gragas': 'Gragas', 'graves': 'Graves', 'hecarim': 'Hecarim', 'heimerdinger': 'Heimerdinger', 'illaoi': 'Illaoi', 
        'irelia': 'Irelia', 'janna': 'Janna', 'jarvaniv': 'JarvanIV', 'jax': 'Jax', 'jayce': 'Jayce', 'jhin': 'Jhin', 'jinx': 'Jinx', 
        'kalista': 'Kalista', 'karma': 'Karma', 'karthus': 'Karthus', 'kassadin': 'Kassadin', 'katarina': 'Katarina', 'kayle': 'Kayle', 
        'kennen': 'Kennen', 'khazix': 'Khazix', 'kindred': 'Kindred', 'kogmaw': 'KogMaw', 'leblanc': 'Leblanc', 'leesin': 'LeeSin', 
        'leona': 'Leona', 'lissandra': 'Lissandra', 'lucian': 'Lucian', 'lulu': 'Lulu', 'lux': 'Lux', 'malphite': 'Malphite', 
        'malzahar': 'Malzahar', 'maokai': 'Maokai', 'masteryi': 'MasterYi', 'missfortune': 'MissFortune', 'monkeyking': 'MonkeyKing', 
        'mordekaiser': 'Mordekaiser', 'morgana': 'Morgana', 'nami': 'Nami', 'nasus': 'Nasus', 'nautilus': 'Nautilus', 'nidalee': 'Nidalee', 
        'nocturne': 'Nocturne', 'nunu': 'Nunu', 'olaf': 'Olaf', 'orianna': 'Orianna', 'pantheon': 'Pantheon', 'poppy': 'Poppy', 
        'quinn': 'Quinn', 'rammus': 'Rammus', 'reksai': 'RekSai', 'renekton': 'Renekton', 'rengar': 'Rengar', 'riven': 'Riven', 
        'rumble': 'Rumble', 'ryze': 'Ryze', 'sejuani': 'Sejuani', 'shaco': 'Shaco', 'shen': 'Shen', 'shyvana': 'Shyvana', 'singed': 'Singed', 
        'sion': 'Sion', 'sivir': 'Sivir', 'skarner': 'Skarner', 'sona': 'Sona', 'soraka': 'Soraka', 'swain': 'Swain', 'syndra': 'Syndra', 
        'tahmkench': 'TahmKench', 'talon': 'Talon', 'taric': 'Taric', 'teemo': 'Teemo', 'thresh': 'Thresh', 'tristana': 'Tristana', 
        'trundle': 'Trundle', 'tryndamere': 'Tryndamere', 'twistedfate': 'TwistedFate', 'twitch': 'Twitch', 'udyr': 'Udyr', 'urgot': 'Urgot', 
        'varus': 'Varus', 'vayne': 'Vayne', 'veigar': 'Veigar', 'velkoz': 'Velkoz', 'vi': 'Vi', 'viktor': 'Viktor', 'vladimir': 'Vladimir', 
        'volibear': 'Volibear', 'warwick': 'Warwick', 'xerath': 'Xerath', 'xinzhao': 'XinZhao', 'yasuo': 'Yasuo', 'yorick': 'Yorick', 
        'zac': 'Zac', 'zed': 'Zed', 'ziggs': 'Ziggs', 'zilean': 'Zilean', 'zyra': 'Zyra', 
        #variants
        'monkey king': 'MonkeyKing', 'wukong': 'MonkeyKing', 'lee sin': 'LeeSin', 'lee sin': 'LeeSin', 'jarvan iv': 'JarvanIV', 
        'tf': 'TwistedFate', 'twisted fate': 'TwistedFate', 'miss fortune': 'MissFortune', 'master yi': 'MasterYi', 'yi': 'MasterYi',
        'tahm kench': 'TahmKench',}

    names = {'Alistar': 'Alistar', 'Mordekaiser': 'Mordekaiser', 'Shaco': 'Shaco', 
        'Khazix': "Kha'Zix", 'JarvanIV': 'Jarvan IV', 'Volibear': 'Volibear', 
        'Tristana': 'Tristana', 'Varus': 'Varus', 'Viktor': 'Viktor', 'Velkoz': "Vel'Koz", 
        'Heimerdinger': 'Heimerdinger', 'Ashe': 'Ashe', 'Anivia': 'Anivia', 'Trundle': 'Trundle', 
        'Leona': 'Leona', 'Malphite': 'Malphite', 'MissFortune': 'Miss Fortune', 'Azir': 'Azir', 
        'Akali': 'Akali', 'Yorick': 'Yorick', 'Kindred': 'Kindred', 'Vi': 'Vi', 
        'Irelia': 'Irelia', 'Renekton': 'Renekton', 'Kalista': 'Kalista', 'MasterYi': 'Master Yi', 
        'Kayle': 'Kayle', 'Cassiopeia': 'Cassiopeia', 'Soraka': 'Soraka', 'Kennen': 'Kennen', 
        'Nunu': 'Nunu', 'Fizz': 'Fizz', 'Jayce': 'Jayce', 'Diana': 'Diana', 
        'Sona': 'Sona', 'MonkeyKing': 'Wukong', 'Ryze': 'Ryze', 'Gangplank': 'Gangplank', 
        'Nami': 'Nami', 'Veigar': 'Veigar', 'Malzahar': 'Malzahar', 'Hecarim': 'Hecarim', 
        'Illaoi': 'Illaoi', 'Janna': 'Janna', 'Lulu': 'Lulu', 'Riven': 'Riven', 'Zyra': 'Zyra', 
        'Chogath': "Cho'Gath", 'Evelynn': 'Evelynn', 'Taric': 'Taric', 'TwistedFate': 'Twisted Fate', 
        'Udyr': 'Udyr', 'Karthus': 'Karthus', 'Syndra': 'Syndra', 'Zac': 'Zac', 'Sion': 'Sion', 
        'Annie': 'Annie', 'Xerath': 'Xerath', 'Bard': 'Bard', 'Vayne': 'Vayne', 
        'Corki': 'Corki', 'Yasuo': 'Yasuo', 'Jinx': 'Jinx', 'Teemo': 'Teemo', 
        'Twitch': 'Twitch', 'Galio': 'Galio', 'Kassadin': 'Kassadin', 'Morgana': 'Morgana', 
        'Aatrox': 'Aatrox', 'Thresh': 'Thresh', 'Pantheon': 'Pantheon', 'Braum': 'Braum', 
        'Lucian': 'Lucian', 'Singed': 'Singed', 'Elise': 'Elise', 'Ziggs': 'Ziggs', 
        'Katarina': 'Katarina', 'TahmKench': 'Tahm Kench', 'Zed': 'Zed', 'Lux': 'Lux', 
        'Sivir': 'Sivir', 'Darius': 'Darius', 'Swain': 'Swain', 'Gragas': 'Gragas', 
        'Rengar': 'Rengar', 'Talon': 'Talon', 'Sejuani': 'Sejuani', 'LeeSin': 'Lee Sin', 
        'Maokai': 'Maokai', 'Nocturne': 'Nocturne', 'Quinn': 'Quinn', 'Lissandra': 'Lissandra', 
        'Gnar': 'Gnar', 'Blitzcrank': 'Blitzcrank', 'Brand': 'Brand', 'Garen': 'Garen', 
        'Ezreal': 'Ezreal', 'Ekko': 'Ekko', 'Jax': 'Jax', 'Tryndamere': 'Tryndamere', 
        'Caitlyn': 'Caitlyn', 'Draven': 'Draven', 'Warwick': 'Warwick', 'Shyvana': 'Shyvana', 
        'Orianna': 'Orianna', 'Nidalee': 'Nidalee', 'Nasus': 'Nasus', 'Ahri': 'Ahri', 
        'Rumble': 'Rumble', 'RekSai': "Rek'Sai", 'KogMaw': "Kog'Maw", 'Urgot': 'Urgot', 
        'Olaf': 'Olaf', 'Jhin': 'Jhin', 'Nautilus': 'Nautilus', 'Amumu': 'Amumu', 
        'XinZhao': 'Xin Zhao', 'Karma': 'Karma', 'Vladimir': 'Vladimir', 'DrMundo': 
        'Dr. Mundo', 'Skarner': 'Skarner', 'FiddleSticks': 'Fiddlesticks', 'Zilean': 'Zilean', 
        'Shen': 'Shen', 'Graves': 'Graves', 'Leblanc': 'LeBlanc', 'Rammus': 
        'Rammus', 'Fiora': 'Fiora', 'Poppy': 'Poppy'}

    f = "data/league/champions.json"
    if not fileIO(f, "check"):
        print("Creating default league's champions.json...")
        fileIO(f, "save", champions)

    f = "data/league/champ_names.json"
    if not fileIO(f, "check"):
        print("Creating default league's champ_names.json...")
        fileIO(f, "save", names)

def setup(bot):
    check_folder()
    check_file()
    n = League(bot)
    bot.add_cog(n)
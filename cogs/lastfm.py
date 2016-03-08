import discord
import pylast
from cogs.utils.dataIO import fileIO
from __main__ import send_cmd_help

class Scrobbler(object):
    def __init__(self,bot):
        self.bot = bot
        self.settings = fileIO('data/lastfm/settings.json','load')
        self.valid_settings = self.check_settings()
        if not self.valid_settings:
            raise RuntimeError("You need to set your lastfm settings.")
        self.network = self.setup_network()
        self.audio = None

    def setup_network(self):
        api_key = self.settings.get('APIKEY')
        api_secret = self.settings.get('APISECRET')
        username = self.settings.get('USERNAME')
        password = pylast.md5(self.settings.get('PASSWORD'))
        net = pylast.LastFMNetwork(api_key=api_key,api_secret=api_secret,
                                   username=username,password_hash=password)
        return net

    def check_settings(self):
        ret = True
        for k in self.settings:
            if k == '':
                print("Error: You need to set your {} in data/lastfm/settings.json")
                ret = False
                break
        return ret

    @commands.group(pass_context=True)
    async def lastfmset(self,ctx):
        if ctx.invoked_subcommand is None:
            send_cmd_help(ctx)

def check_folders():
    if not os.exists('data/lastfm'):
        print('Creating data/lastfm folder.')
        os.mkdir('data/lastfm')

def check_files():
    s = {'APIKEY':'','APISECRET':'','USERNAME':'','PASSWORD':''}

    f = "data/lastfm/settings.json"
    if not fileIO(f, "check"):
        print("Creating default lastfm's settings.json...")
        fileIO(f, "save", s)

def setup(bot):
    check_folders()
    check_files()
    n = Scrobbler(bot)
    bot.add_cog(n)
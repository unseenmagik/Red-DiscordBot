from . import plugin
import importlib

importlib.reload(plugin)

def setup(bot):
    n = plugin.Class(bot)
    bot.add_cog(n)
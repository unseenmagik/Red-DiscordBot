import discord
from discord.ext import commands

class Ignoring(commands.CheckFailure):
    pass

class Bot(discord.ext.commands.Bot):
    def client_dispatch(self,event_name,*args,**kwargs):
        super(discord.Client,self).__thisclass__.dispatch(event_name,*args,**kwargs)

    def dispatch(self,event_name,*args,**kwargs):
        try:
            self.client_dispatch(event_name,*args,**kwargs)
        except Ignoring:
            print('Server or channel ignored. Ignoring on_message.')
        else:
            ev = 'on_' + event_name
            if ev in self.extra_events:
                for event in self.extra_events[ev]:
                    coro = self._run_extra(event, event_name, *args, **kwargs)
                    discord.utils.create_task(coro, loop=self.loop)
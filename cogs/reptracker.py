import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os

class RepTracker:
    """Keep track of user scores through @mention++/--"""
    def __init__(self,bot):
        self.bot = bot
        self.scores = fileIO("data/reptracker/scores.json", "load")

    def _process_scores(self,member_id,score_to_add):
        if member_id in self.scores:
            if "score" in self.scores.get(member_id,{}):
                self.scores[member_id]["score"] += score_to_add
            else:
                self.scores[member_id]["score"] = score_to_add
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["score"] = score_to_add

    def _add_reason(self,member_id,reason):
        if reason == "":
            return
        if member_id in self.scores:
            if "reasons" in self.scores.get(member_id,{}):
                old_reasons = self.scores[member_id].get("reasons",[])
                new_reasons = [reason] + old_reasons[:4]
                self.scores[member_id]["reasons"] = new_reasons
            else:
                self.scores[member_id]["reasons"] = [reason]
        else:
            self.scores[member_id] = {}
            self.scores[member_id]["reasons"] = [reason]

    def _fmt_reasons(self,reasons):
        if len(reasons) == 0:
            return None
        ret = "```Latest Reasons:\n"
        for num,reason in enumerate(reasons):
            ret += "\t"+str(num+1)+") "+str(reason)+"\n"
        return ret+"```"

    @commands.command(pass_context=True)
    async def rep(self,ctx):
        """Checks a user's rep, requires @ mention 

           Example: !rep @Red"""
        if len(ctx.message.mentions) != 1:
            await send_cmd_help(ctx)
            return
        member = ctx.message.mentions[0]
        if self.scores.get(member.id,0) != 0:
            member_dict = self.scores[member.id]
            await self.bot.say(member.name+" has "+str(member_dict["score"])+" points!")
            reasons = self._fmt_reasons(member_dict["reasons"])
            if reasons: 
                await self.bot.send_message(ctx.message.author,reasons)
        else:
            await self.bot.say(member.name+" has no rep!")

    async def check_for_score(self,message):
        user = message.author
        content = message.content
        mentions = message.mentions
        if message.author.id == self.bot.user.id:
            return
        first_word = content.split(" ")[0]
        reason = content[len(first_word)+1:]
        for member in mentions:
            if member.id in first_word.lower():
                if "++" in first_word.lower() or "--" in first_word.lower():
                    if member == user:
                        await self.bot.send_message(message.channel,"You can't modify your own rep, jackass.")
                if "++" in first_word.lower():
                    self._process_scores(member.id,1)
                    self._add_reason(member.id,reason)
                elif "--" in first_word.lower():
                    self._process_scores(member.id,-1)
                    self._add_reason(member.id,reason)
                fileIO("data/reptracker/scores.json", "save", self.scores)
                return

        if "++" in first_word or "--" in first_word:
            if "@" not in first_word:
                await self.bot.send_message(message.channel,"You need to use an @ mention for score tracking.")

def check_folder():
    if not os.path.exists("data/reptracker"):
        print("Creating data/reptracker folder...")
        os.makedirs("data/reptracker")

def check_file():
    scores = {}

    f = "data/reptracker/scores.json"
    if not fileIO(f, "check"):
        print("Creating default reptracker's scores.json...")
        fileIO(f, "save", scores)

def setup(bot):
    check_folder()
    check_file()
    n = RepTracker(bot)
    bot.add_listener(n.check_for_score, "on_message")
    bot.add_cog(n)
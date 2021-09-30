from discord.ext import commands
from discord.utils import get

import constants


def is_role_requests_channel(ctx):
    return ctx.channel.name == constants.role_requests


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(is_role_requests_channel)
    async def addrole(self, ctx, *, role=None):
        if role is None:
            await ctx.author.send('you forget to ask for a role')
            await ctx.message.delete()
            return
        role_clean = role.lower().strip("\"'")
        if role_clean not in\
                [x.lower() for x in constants.self_assignable_roles]:
            await ctx.author.send('you cannot give yourself the role: '
                                  + role + "\n or that role doesnt exist")
            await ctx.message.delete()
        else:
            roles = ctx.message.guild.roles
            role_obj = get(roles,
                           name=next(x for x in constants.self_assignable_roles
                                     if x.lower() == role_clean))
            await ctx.author.add_roles(role_obj)
            await ctx.message.add_reaction('✔')

    @commands.command()
    @commands.check(is_role_requests_channel)
    async def removerole(self, ctx, *, role=None):
        if role is None:
            await ctx.author.send('you forget to say which role to remove')
            await ctx.message.delete()
            return
        role_clean = role.lower().strip("\"'")
        if role_clean not in\
                [x.lower() for x in constants.self_assignable_roles]:
            await ctx.author.send('you cannot remove yourself from the role: '
                                  + role + "\n or that role doesnt exist")
            await ctx.message.delete()
        else:
            roles = ctx.message.guild.roles
            role_obj = get(roles,
                           name=next(x for x in constants.self_assignable_roles
                                     if x.lower() == role_clean))
            await ctx.author.remove_roles(role_obj)
            await ctx.message.add_reaction('✔')

    @commands.command()
    @commands.check(is_role_requests_channel)
    async def listroles(self, ctx):
        await ctx.author\
            .send("Self assignable roles:\n\n"
                  + "\n\n".join([x[0] + ": " + x[1] for x in
                                 zip(constants
                                     .self_assignable_roles,
                                     constants.
                                     self_assignable_roles_descriptions)])
                  + '\n\n\nCommands:\n\n use ?addrole'
                  + ' "rolename" in role-requests'
                  + " to add yourself to a role, or you can"
                  + '\n\n use ?removerole "rolename" to remove it.')
        await ctx.message.add_reaction('✔')

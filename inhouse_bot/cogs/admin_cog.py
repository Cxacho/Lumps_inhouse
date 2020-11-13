from typing import Union

import discord
from discord.ext import commands

from inhouse_bot import game_queue, matchmaking_logic
from inhouse_bot.orm import session_scope
from inhouse_bot.common_utils.get_last_game import get_last_game
from inhouse_bot.inhouse_bot import InhouseBot


class AdminCog(commands.Cog, name="Admin"):
    def __init__(self, bot: InhouseBot):
        self.bot = bot

    @commands.group(case_insensitive=True)
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"The accepted subcommands are "
                f"{', '.join([c.name for c in self.walk_commands() if type(c) == commands.Command])}"
            )

    @admin.command()
    async def reset(
        self, ctx: commands.Context, member_or_channel: Union[discord.Member, discord.TextChannel] = None
    ):
        """
        Resets the queue status for a channel or a player

        If no argument is given, resets the queue in the current channel
        """
        if not member_or_channel or type(member_or_channel) == discord.TextChannel:
            channel = ctx.channel if not member_or_channel else member_or_channel
            game_queue.reset_queue(channel.id)
            await ctx.send(f"Queue has been reset in {channel.name}")

        elif type(member_or_channel) == discord.Member:
            game_queue.remove_player(member_or_channel.id)
            await ctx.send(f"{member_or_channel.name} has been removed from all queues")

    @admin.command()
    async def won(self, ctx: commands.Context, member: discord.Member):
        """
        Scores the user’s last game as a win and recomputes ratings based on it
        """
        # TODO LOW PRIO Make a function that recomputes *all* ratings to allow to re-score/delete/cancel any game

        matchmaking_logic.score_game_from_winning_player(player_id=member.id, server_id=ctx.guild.id)

        await ctx.send(
            f"{member.name}’s last game has been scored as a win for his team and ratings have been recalculated"
        )

    @admin.command()
    async def cancel(self, ctx: commands.Context, member: discord.Member):
        """
        Cancels the user’s ongoing game if it was not scored yet
        """
        with session_scope() as session:
            game, participant = get_last_game(player_id=member.id, server_id=ctx.guild.id, session=session)

            if game and game.winner:
                await ctx.send("The game has already been scored and cannot be canceled anymore")
                return

            session.delete(game)

        await ctx.send(f"{member.name}’s ongoing game was cancelled and deleted from the database")
import io
import random
import zipfile

import aiohttp
import discord
import psutil
from discord import option, slash_command
from discord.ext import commands, bridge

import data
import utils


class Utility(commands.Cog, name="utility"):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(brief="Generate a sona!")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sonagen(self, ctx):
        """ Generate a random sona """
        primary_color = discord.Color.random()
        color = random.choice(data.colors)
        species = random.choice(list(data.species))
        sonatype = random.choice(["Feral", "Anthro"])
        sex = random.choice(["Male", "Male", "Male", "Male", "Female", "Female", "Female", "Female", "Intersex"])
        if sonatype == "Feral":
            heightstring = f"**Height to shoulders**: {random.randint(data.species[species][0], data.species[species][1])}cm"
        else:
            heightstring = f"**Height**: {random.randint(130, 240)}cm"

        embed = discord.Embed(title="Your Sona:", color=primary_color, description=f"""
**Species**: {sonatype} {species}
**Primary Color**: {str(primary_color)} (embed color)
**Secondary Color**: {color}
{heightstring}
**Sex**: {sex}
""")
        return await ctx.respond("Sure, here's your freshly generated sona!", embed=embed)

    @slash_command(brief="Get all server stickers & emojis!")
    @discord.default_permissions(manage_guild=True)
    async def emoji_downloader(self, ctx):
        """ Download this server's emojis and stickers """
        saved_emojis = []
        saved_stickers = []
        total = len(ctx.guild.emojis) + len(ctx.guild.stickers)
        current = 0
        message = await ctx.respond(f"Downloading, this might take some time... (0 of {total})")
        zip_buffer = io.BytesIO()  # Create a BytesIO object to hold the ZIP file
        with zipfile.ZipFile(zip_buffer, 'w') as zipped_f:  # Create a ZIP file inside the buffer
            for emoji in ctx.guild.emojis:
                emoji_file_name = (emoji.name if emoji.name not in saved_emojis else emoji.name + str(saved_emojis.count(emoji.name) + 1)) + emoji.url[-4:]
                zipped_f.writestr(f"emojis/{emoji_file_name}", await emoji.read())
                saved_emojis.append(emoji.name)
                current += 1
                await message.edit_original_response(content=f"Downloading, this might take some time... ({current} of {total})")

            async with aiohttp.ClientSession() as session:
                for sticker in ctx.guild.stickers:
                    async with session.get(sticker.url) as response:
                        sticker_file_name = (sticker.name if sticker.name not in saved_stickers else sticker.name + str(saved_stickers.count(sticker.name) + 1)) + ".png"
                        zipped_f.writestr(f"stickers/{sticker_file_name}", await response.read())
                        saved_stickers.append(sticker.name)

        zip_buffer.seek(0)  # Reset the buffer position to the beginning so the next line reads the file from the start
        await message.edit_original_response(content="Here are all emojis and stickers of this guild!", file=discord.File(zip_buffer, filename="emojis_and_stickers.zip"))

    @bridge.bridge_command(brief="Get rid of bots")
    @option("day", int, description="Select the desired day of a month", min_value=1, max_value=31)
    @option("month", int, description="Select the desired month number", min_value=1, max_value=12)
    @bridge.has_permissions(ban_members=True)
    async def botcollector(self, ctx, day: int, month: int):
        """ Get members created on a certain day """
        if day == 0 or month == 0:
            return await ctx.respond("0 is not a valid number!")
        output = ""
        message = await ctx.respond("Fetching...")
        for member in ctx.guild.members:
            if not member.bot:
                if member.created_at.day == day and member.created_at.month == month:
                    output += f"{member.mention} "
        if output == "":
            output = "No one found!"
        await message.edit_original_response(content=output)

    @bridge.bridge_command(brief="Get all non-verified accounts")
    @bridge.has_permissions(ban_members=True)
    async def pending(self, ctx: discord.ApplicationContext):
        """ Get all non-verified accounts (unsure what that means) """
        output = ""
        for member in ctx.guild.members:
            if member.pending:
                output += " " + member.mention
        if not output:
            output = "No members found!"
        await ctx.respond(output)

    @slash_command(brief="Announce something!")
    @option("channel", discord.TextChannel, description="The channel to announce in")
    @option("message", str, description="The message to announce")
    @option("embed", bool, description="Whether to make it an embed", required=False, default=False)
    @option("attachment", discord.Attachment, description="A nice image", required=False, default=None)
    @discord.default_permissions(manage_guild=True)
    async def announce(self, ctx, channel: discord.TextChannel, message: str, embed: bool, attachment: discord.Attachment):
        """ Announce something in a channel """
        await ctx.defer(ephemeral=True)
        if not channel.can_send():
            return await ctx.respond(f"I don't have permissions to send messages to {channel.mention}!", ephemeral=True)
        if embed:
            view = ConfirmView()
            await ctx.respond("Are you sure? Embeds don't actually send pings to any roles or users", view=view, ephemeral=True)
            await view.wait()
            if not view.confirmed:
                return
            message_embed = discord.Embed(colour=discord.Color.random(), description=message)
            if attachment:
                message_embed.set_image(url=attachment.url)
            await channel.send(embed=message_embed)
        else:
            if attachment:
                file = await attachment.to_file()
                await channel.send(content=message, file=file)
            else:
                await channel.send(message)
        await ctx.respond("Message successfully sent!", ephemeral=True)

    @slash_command(brief="Information about the server")
    async def serverinfo(self, ctx):
        """ Get the current server's info """
        guild = ctx.guild
        owner = await discord.utils.get_or_fetch(guild, 'member', guild.owner_id)
        embed = discord.Embed(color=discord.Color.random(), title=guild.name)
        embed.description = f"""
**Owner:** {owner.mention}
**Members:** {guild.member_count}
**Roles:** {len(guild.roles)}
**Verification:** {str(guild.verification_level).title()}
**Channels:** {len(guild.text_channels)} Text, {len(guild.voice_channels)} Voice
**Created:** <t:{round(guild.created_at.timestamp())}:R>
**Emojis:** {len(guild.emojis)}
**Stickers:** {len(guild.stickers)}
        """
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"ID: {guild.id}")
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        features = ", ".join(guild.features).replace("_", " ").title()
        embed.add_field(name="Features", value=features)
        await ctx.respond(embed=embed)

    @bridge.bridge_command(aliases=["information", "ping", "latency", "pong", "servers", "guilds", "support", "invite"], description="Displays information about Paw")
    async def info(self, ctx: bridge.BridgeContext):
        embed = discord.Embed()
        vram = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        divamount = 1000000000
        embed.description = f"""
{self.bot.user.name} is a bot developed by TPK to provide social interaction commands and other fun things! Sponsored by [Blue Atomic](https://github.com/BlueAtomic)
**Users:** {sum(x.member_count for x in self.bot.guilds)}
**API Latency:** {round(self.bot.latency * 1000)}ms
**RAM:** {round((vram.used / divamount), 2)}GB used out of {round((vram.total / divamount), 2)}GB total ({round(((vram.used / vram.total) * 100), 2)}% used)
**Disk:** {round((disk_usage.free / divamount), 2)}GB free out of {round((disk_usage.total / divamount), 2)}GB total ({round((((disk_usage.used / disk_usage.total * 100) - 100) * (-1)), 2)}% free)

[[Github]](https://github.com/MiataBoy/Paw) [[Privacy Policy]](https://gist.github.com/MiataBoy/20fda9024f277ea5eb2421adbebc2f23) [[Terms of Service]](https://gist.github.com/MiataBoy/81e96023a2aa055a038edab02e7e7792)
        """
        embed.colour = utils.Colors.blue
        await ctx.respond(embed=embed)


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.confirmed = False
        self.disable_on_timeout = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button, interaction):
        self.confirmed = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button, interaction):
        self.confirmed = False
        self.disable_all_items()
        await interaction.response.edit_message(content="Cancelled", view=None)
        self.stop()


def setup(bot):
    bot.add_cog(Utility(bot))

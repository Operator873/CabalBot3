import irc.client
from ib3 import Bot
from ib3.auth import SASL
from ib3.connection import SSL
from ib3.mixins import DisconnectOnError, PingServer
from ib3.nick import Ghost
from irc.bot import Channel
from irc.client import NickMask

from datetime import datetime


class CabalBot(SASL, SSL, DisconnectOnError, PingServer, Ghost, Bot):
    def __init__(self, config, channels, admins):
        # Set up the bot
        self.owner = config["admin"]["owner"]
        self.admins = admins

        self.nickname = config["bot"]['botname']
        self.bot_account = config["bot"]["botaccount"]
        self.bot_passwd = config["bot"]["botpassword"]        
        self.cmd_char = config["bot"]["botcmdchar"]
        self.home_channel = config["bot"]['botchannel']

        self.channels = channels.append(self.home_channel)

        self.server = config["server"]["url"]
        self.port = int(config["server"]["port"])
        
        self.quiet = False
        self.notify = True
        self.listen = True
        self.error_msg = f"Unrecognized command. Try doing {self.cmd_char}help"

        super().__init__(
            server_list=[(self.server, self.port)],
            nickname=self.nickname,
            realname="CabalBot",
            username=self.bot_account,
            ident_password=self.bot_passwd,
            channels=self.channels,
            max_pings=2,
            ping_interval=300,
        )

    # Built in logging, janky
    def log_this(self, data) -> None:
        with open("../logs/cabal.log", 'a') as log:
            log.write(f"{datetime.now()} -- {data}\n")
    
    # Convert a mask into a nick
    def get_nick(self, mask) -> str:
        return NickMask(mask).nick

    # Mask to cloak
    def get_cloak(self, mask) -> str:
        return NickMask(mask).host
    
    # Handle CTCP stuff
    def on_ctcp(self, c, event) -> None:
        # Answer VERSION requests. Common for IRCops
        if event.arguements[0] == "VERSION":
            c.ctcp_reply(
                self.get_nick(event.source),
                f"CabalBot v3.0 by Operator873 // Owner: {self.owner} @ {self.home_channel}"
            )
        elif (
            event.arguements[0] == "PING" and
            len(event.arguments) > 1
        ): # Answer server PINGs. Very important
            c.ctcp_reply(self.get_nick(event.source), f"PING {event.arguements[1]}")
    
    # Log any ACTIONs sent to the bot and ignore them
    def on_action(self, c, event) -> None:
        self.log_this(f"ACTION > {self.channel}: {self.get_nick(event.source)} ==> {event}\n")
    
    # Respond to queries (PM/DMs)
    def on_privmsg(self, c, event) -> None:
        message = event.arguements[0]
        self.log_this(f"PM > From {event.source}: {message}")
        
        # Only consider the message if it's from the owner or an admin
        if (
            self.get_nick(event.source) == self.owner or
            self.get_nick(event.source) in self.admins
        ):
            # If the message doesn't have the command character or doesn't start with bot nick, ignore it
            if message[0] != self.cmd_char or not message.lower().startswith(self.nickname.lower()):
                return
            else:
                # Handle 'PM only' commands here
                pass
    
    def on_pubmsg(self, c, event) -> None:
        known_commands = [
            "hi"
        ]

        message = event.arguements[0].split(" ")
        chan = event.target

        if chan not in self.channels:
            # We're not even in that channel so dump it
            return
        
        if (
            message[0] != self.cmd_char or
            not message.lower().startswith(self.nickname.lower())
        ):
            # Ignore messages not meant for the bot
            return
        
        # Split off the actual command from any trailing string
        if len(message.split(" ")) > 1:
            cmd, args = message.split(" ", 1)
            # Bot nick commands should disregard first word
            if cmd.lower().startswith(self.nickname.lower()):
                cmd, args = args.split(" ", 1)
        else:
            cmd = message.strip()

        # Strip the character out now
        cmd = cmd.replace(self.cmd_char, "")
        
        # Check for the command and dump if it's not known
        if cmd not in known_commands:
            return
        
        # Log the command we are going to process for possible debugging
        self.log_this(f"COMMAND > {event.source} in {event.target} did command: {message}")

        # Hello command. Good for checking the bot is working correctly and can see input
        if cmd.lower() == "hi":
            self.msg(f"Hello {self.get_nick(event.source)}! I saw your message!", chan)
        
        # Get Central Auth for an account
        elif cmd.lower() == "ca":
            self.msg(self.do_ca(args))

    def is_chan_admin(self, source, target) -> bool:
        chan: Channel = self.channels.get(target)
        return (
            chan.is_oper(self.get_nick(source)) or
            self.get_nick(source) in self.admins
        )
    
    def msg(self, message, target=None) -> None:
        if not target:
            target = self.home_channel
        
        try:
            self.connection.privmsg(target, message)
        except irc.client.MessageTooLong:
            self.log_this(f"MSG TOO LONG > {message}")
            self.connection.privmsg(
                target,
                f"I tried to send a response that was too long. Pinging {self.owner}"
            )
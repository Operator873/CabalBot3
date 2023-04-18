import threading
from configparser import ConfigParser
from modules import ircbot, rcbot, cabalsql

class BotThread(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.b = bot
    
    def run(self):
        self.b.start()

if __name__ == "__main__":
    global irc, rc

    conf = ConfigParser()
    conf.read_string(open("cabal.conf", "r").read())

    sql = cabalsql.Connection(conf["mysql"])
    chans, admins = sql.get_bot_settings()

    irc = ircbot.CabalBot(conf, chans, admins)
    rc = rcbot.RecentChangesBot(sql)

    try:
        irc_thread = BotThread(irc)
        rc_thread = BotThread(rc)

        irc_thread.run()
        rc_thread.run()
    except KeyboardInterrupt:
        irc.disconnect("Killed by a KeyboardInterrupt")
    except Exception as e:
        with open("./logs/cabal.lot", "a") as log:
            log.write(f"UNHANDLED EXCEPTION > {str(e)}")
        irc.disconnect("CabalBot encountered and error and unexpectedly closed.")
    finally:
        raise SystemExit()


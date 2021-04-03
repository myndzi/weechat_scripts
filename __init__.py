## hack weechat import paths
import sys
import os

PACKAGE_PARENT = "."
SCRIPT_DIR = os.path.dirname(
    os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__)))
)
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
## /

from scripts.counter import CommandTracker
from api import Script, TwitchIrc, prnt, timer_callback


class Testing(Script):
    def on_register(self):
        prnt("", "registered")

    def before_shutdown(self):
        prnt("", "shutting down")


if __name__ == "__main__":
    testing = Testing(
        "Testing",
        "myndzi",
        "0.0.1",
        "MIT",
        "Counts the number of times a command is seen",
    )
    commandtracker_cb = testing.register_event(
        CommandTracker("!uguu", "!quack", "!croak", "!speen")
    )
    testing_shutdown = testing.shutdown
    testing.install()

    # irc = TwitchIrc()
    # irc_cb = irc.callback("irc_cb")

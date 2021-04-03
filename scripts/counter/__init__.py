from typing import Any, Dict, List, Set
from datetime import datetime, timedelta
from pprint import pformat, pprint
from api import (
    Glob,
    IrcMessage,
    MessageTag,
    Script,
    Command,
    Message,
    Event,
    ReturnCode,
    TwitchIrc,
    TwitchMessage,
    prnt,
    timer_callback,
    set_timeout,
    say,
    # irc_raw_in_cb,
)


def irc_in2_privmsg_cb(*args):
    prnt("", pformat(args))
    return ReturnCode.OK


class CommandTracker(Event):
    def __init__(self, *commands: str):
        self.commands: Dict[str, Dict[str, Any]] = {
            k: {
                "next_allowed": datetime.now(),
                "users": set(),
                "timer": None,
            }
            for k in commands
        }

        super().__init__("", "irc.twitch.#dunkorslam", "")

    def callback(self, msg: Message):
        if not msg.notify_level == 1:
            return

        m = msg.message2
        if not m.startswith("!"):
            return

        firstword = m.split(" ")[0]
        if not firstword in self.commands:
            return

        if datetime.now() < self.commands[firstword]["next_allowed"]:
            return

        self.touch(firstword, msg.prefix2)

    def reset(self, command: str, cooldown: bool):
        # prnt("", f"resetting {command = }")
        if cooldown:
            self.commands[command]["next_allowed"] = datetime.now() + timedelta(0, 600)

        self.commands[command]["users"].clear()
        self.clear_timeout(command)

    def clear_timeout(self, command):
        clear = self.commands[command]["timer"]
        if clear:
            clear()

    def report(self, command):
        uniq = len(self.commands[command]["users"])
        prnt("", f"{command = } {uniq = }")
        if uniq >= 10:
            self.reset(command, True)
            say("irc.twitch.#dunkorslam", f"{uniq} {command} combo! dnkWTF")
        else:
            self.reset(command, False)

    def touch(self, command, user):
        # prnt("", f"touch {user = } {command = }")
        self.commands[command]["users"].add(user)
        self.clear_timeout(command)
        self.commands[command]["timer"] = set_timeout(
            20000, lambda x: self.report(command)
        )


class Test(Command):
    def callback(self, data: str, buffer: str, args: str) -> int:
        prnt("", "bar")
        return ReturnCode.OK.value


class Counter(Script):
    def on_register(self):
        prnt("", "registered")

    def before_shutdown(self):
        prnt("", "shutting down")


# def install():
#     counter = Counter(
#         "Counter",
#         "myndzi",
#         "0.0.1",
#         "MIT",
#         "Counts the number of times a command is seen",
#     )
#     test_cb = counter.register_command(Test("test", "do a bar", "", "", ""))

#     # irc = TwitchIrc()

#     # irc.on('PRIVMSG', ['#dunkorslam'], counter.count)

#     # irc_cb = irc.callback("irc_cb")

#     commandtracker_cb = counter.register_event(
#         CommandTracker("!uguu", "!quack", "!croak", "!speen")
#     )
#     counter_shutdown = counter.shutdown
#     counter.install()

#     # def testing(server: str, msg: TwitchMessage) -> ReturnCode:
#     #     prnt("", f"{msg.display_name}: {msg.params[1]}")
#     #     return ReturnCode.OK

#     # irc = TwitchIrc()
#     # irc.on(testing, "PRIVMSG", ["#dunkorslam", Glob("!*")])
#     # irc_cb = irc.callback("irc_cb")

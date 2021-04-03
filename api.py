from abc import abstractmethod
from collections import defaultdict
import re
from types import LambdaType
import weechat as w
import inspect
from typing import (
    Any,
    Dict,
    DefaultDict,
    List,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypedDict,
    Callable,
    Union,
)
from enum import Enum
from datetime import datetime
from uuid import uuid4
from pprint import pformat, pprint

from pydle.features.ircv3.tags import TaggedMessage
from pydle.features.ctcp import is_ctcp, construct_ctcp, parse_ctcp
from pydle.features.rfc1459.parsing import parse_user


class IrcMessage:
    server: str
    nick: str
    user: str
    host: str
    source: str
    command: str
    params: List[str]
    tags: Dict[str, str]

    def __init__(self, server: str, line: str):
        msg = TaggedMessage.parse(line.encode())

        source = msg.source
        nick, user, host = parse_user(source)

        if isinstance(msg.command, int):
            command = f"{msg.command:03}"
        else:
            command = msg.command.upper()

        params = msg.params

        if command == "PRIVMSG":
            if is_ctcp(params[1]):
                type, params = parse_ctcp(params[1])
                command = f"CTCP_{type.upper()}"
                params[1] = params
        elif command == "NOTICE":
            if is_ctcp(msg.params[1]):
                type, params = parse_ctcp(params[1])
                command = f"CTCPREPLY_{type.upper()}"
                params[1] = params

        self.server = server
        self._source = source
        self.nick = nick
        self.user = user
        self.host = host
        self.command = command
        self.params = params
        self.tags = msg.tags

    def __str__(self):
        command = self.command
        params = self.params
        type = None
        if command.startswith("CTCP_"):
            command = "PRIVMSG"
            type = command.split("_")[1]
        if command.startswith("CTCPREPLY_"):
            command = "NOTICE"
            type = command.split("_")[1]

        parts = []
        if self.tags and len(self.tags) > 0:
            serialized = ";".join([f"{k}={v}" for k, v in self.tags.items()])
            parts.append(f"@{serialized}")

        source = ""
        if self.nick:
            source += self.nick
        if self.user:
            source += f"!{self.user}"
        if self.host:
            source += f"@{self.host}"

        if source:
            parts.append(f":{source}")

        parts.append(self.command)

        if params:
            params = self.params
            if type and len(params) == 1:
                params[1] = construct_ctcp(type)
            elif type:
                params[1] = construct_ctcp(type, params[1])

            if len(params) > 1:
                parts.append(f":{' '.join(params)}")
            elif len(params) == 1:
                parts.append(params[0])

        return f"{' '.join(parts)}\r\n"


class TwitchMessage(IrcMessage):
    display_name: str

    def __init__(self, server: str, line: str):
        super().__init__(server, line)
        if "display-name" in self.tags:
            self.display_name = self.tags["display-name"]
        else:
            self.display_name = self.nick


class Matcher:
    spec: Any

    @abstractmethod
    def matches(self, target: str):
        pass


class String(Matcher):
    spec: str

    def __init__(self, spec: str):
        self.spec = spec

    def matches(self, target: str):
        return target == self.spec


class RegExp(Matcher):
    spec: Pattern

    def __init__(self, spec: str):
        self.spec = re.compile(spec)

    def matches(self, target: str):
        return self.spec.fullmatch(target) is not None


class Glob(RegExp):
    def __init__(self, spec: str):
        super().__init__(re.escape(spec.replace("*", "\x00")).replace("\x00", ".*"))


def match_array(spec: List[Matcher], target: List[str]) -> bool:
    if len(spec) > len(target):
        return False

    for idx, item in enumerate(spec):
        if item is not None and not item.matches(target[idx]):
            return False

    return True


MessageFilterLambda = Callable[[IrcMessage], bool]


def match_message(command: str, params: List[Matcher]) -> MessageFilterLambda:
    return lambda msg: msg.command == command and match_array(params, msg.params)


# IrcResponseCallback = Callable[[bool, Union[None, List[List[str]]]], None]


# class AsyncIrcResponse:
#     callback: IrcResponseCallback
#     capture: LambdaType[IrcMessage]
#     error: LambdaType[IrcMessage]
#     done: LambdaType[IrcMessage]
#     results: List[List[str]]

#     def __init__(
#         self,
#         callback: IrcResponseCallback,
#         error=LambdaType[IrcMessage],
#         done=LambdaType[IrcMessage],
#         capture=Optional[LambdaType[IrcMessage]],
#     ):
#         self.callback = callback
#         self.capture = capture
#         self.error = error
#         self.done = done
#         self.results = []

#     def on_message(self, msg: IrcMessage):
#         if self.error and self.error(msg):
#             self.callback(True, None)
#         elif self.capture and self.capture(msg):
#             self.results.append(msg.params)
#         elif self.done and self.done(msg):
#             self.callback(False, self.results)


class ReturnCode(Enum):
    OK = w.WEECHAT_RC_OK
    OK_EAT = w.WEECHAT_RC_OK_EAT
    ERROR = w.WEECHAT_RC_ERROR


IrcCallback = Callable[[str, IrcMessage], ReturnCode]
IrcCallbackTuple = Tuple[MessageFilterLambda, IrcCallback]


callback_rexp = re.compile("(\S+)(\s*=\s*[^\s\.]callback\([^\)]+\).*)", re.DOTALL)


def assert_named_correctly(callback_name: str):
    for frame in inspect.stack():
        if frame.code_context and ".callback(" in frame.code_context[0]:
            left, right = frame.code_context[0].strip(" \r\n").split("=")
            left = left.strip()
            right = right.strip()
            if left == callback_name:
                return
            raise AssertionError(
                f"Weechat requires callbacks to exist in global scope of the source script. Use `{callback_name} = {right}`"
            )
    w.prnt("", "could not identify callsite, can't verify callback is named correctly")


class Irc:
    Message: Type[IrcMessage]
    callbacks: DefaultDict[str, List[IrcCallbackTuple]]

    def __init__(self):
        self.Message = IrcMessage
        self.callbacks = defaultdict(list)

    def on(
        self,
        callback: IrcCallback,
        command: str,
        params: List[Union[str, Matcher]] = [],
    ) -> None:
        ps: List[Matcher] = [p if isinstance(p, Matcher) else String(p) for p in params]
        self.callbacks[command].append((match_message(command, ps), callback))

    def callback(self, callback_name: str) -> Callable[[str, str, str], int]:
        ret = lambda *args: self._callback(*args).value
        assert_named_correctly(callback_name)

        w.hook_signal("*,irc_raw_in_*", callback_name, "")
        return ret

    def _callback(self, data: str, signal: str, payload: str) -> ReturnCode:
        server, command = signal.split(",")
        command = command[11:]

        if len(self.callbacks[command]) == 0:
            return ReturnCode.OK

        r: ReturnCode = ReturnCode.OK
        msg = self.Message(server, payload)
        for filter, callback in self.callbacks[command]:
            if not filter(msg):
                continue

            r = callback(server, msg)

            if not r == ReturnCode.OK:
                return r

        return ReturnCode.OK


class TwitchIrc(Irc):
    def __init__(self):
        super().__init__()
        self.Message = TwitchMessage


# def irc_raw_in_cb(data, signal, payload):
#     if data == "synthetic":
#         return ReturnCode.OK

#     server = signal.split(",")[0]
#     msg = parse_irc(server, payload)
#     prnt("", pformat(msg))
#     return ReturnCode.OK


class MessageTag:
    NO_FILTER = "no_filter"
    NO_HIGHLIGHT = "no_highlight"
    NO_LOG = "no_log"
    LOG0 = "log0"
    LOG1 = "log1"
    LOG2 = "log2"
    LOG3 = "log3"
    LOG4 = "log4"
    LOG5 = "log5"
    LOG6 = "log6"
    LOG7 = "log7"
    LOG8 = "log8"
    LOG9 = "log9"
    NOTIFY_NONE = "notify_none"
    NOTIFY_MESSAGE = "notify_message"
    NOTIFY_PRIVATE = "notify_private"
    NOTIFY_HIGHLIGHT = "notify_highlight"
    SELF_MSG = "self_msg"

    @staticmethod
    def NICK(nick: str) -> str:
        return "nick_{}".format(nick)

    @staticmethod
    def PREFIX_NICK(color: str) -> str:
        return "prefix_nick_{}".format(color)

    @staticmethod
    def HOST(host: str) -> str:
        return "host_{}".format(host)

    @staticmethod
    def IRC(command_or_numeric: Union[int, str]) -> str:
        return "irc_{}".format(str(command_or_numeric).lower())

    IRC_NUMERIC = "irc_numeric"
    IRC_ERROR = "irc_error"
    IRC_ACTION = "irc_action"
    IRC_CTCP = "irc_ctcp"
    IRC_CTCP_REPLOY = "irc_ctcp_reply"
    IRC_SMART_FILTER = "irc_smart_filter"
    AWAY_INFO = "away_info"


class MessageDict(TypedDict):
    modified: Set[str]
    ptr: str
    buffer_name: str
    y: int
    date: datetime
    date_printed: datetime
    str_time: str
    tags: Set[str]
    displayed: int
    notify_level: int
    highlight: int
    prefix: str
    message: str


class Message:
    modified: Set[str]
    ptr: str
    buffer_name: str
    y: int
    date: datetime
    date_printed: datetime
    str_time: str
    tags: Set[str]
    displayed: int
    notify_level: int
    highlight: int
    prefix: str
    message: str

    def __init__(self, htable: dict):
        _modified: Set[str] = set()
        data: MessageDict = {
            "modified": set(),
            "ptr": htable["buffer"],
            "buffer_name": htable["buffer_name"],
            "y": int(htable["y"]),
            "date": datetime.fromtimestamp(int(htable["date"])),
            "date_printed": datetime.fromtimestamp(int(htable["date_printed"])),
            "str_time": htable["str_time"],
            "tags": set(htable["tags"].split(",")),
            "displayed": int(htable["displayed"]),
            "notify_level": int(htable["notify_level"]),
            "highlight": int(htable["highlight"]),
            "prefix": htable["prefix"],
            "message": htable["message"],
        }
        data["tags"].discard("")
        for k, v in data.items():
            object.__setattr__(self, k, v)
        object.__setattr__(self, "_modified", _modified)

    @property
    def prefix2(self) -> str:
        return w.string_remove_color(self.prefix, "")

    @property
    def message2(self) -> str:
        return w.string_remove_color(self.message, "")

    def __setattr__(self, name: str, value: Union[datetime, Set[str], int, str]):
        data = object.__getattribute__(self, "data")
        if hasattr(self, name) and not name.startswith("_"):
            if type(data[name]) != type(value):
                raise TypeError(
                    "Invalid type: Provided: {}; '{}.{}': {}".format(
                        type(value),
                        object.__getattribute__(self, "__class__").__name__,
                        name,
                        type(data[name]),
                    )
                )
            object.__setattr__(self, name, value)
            object.__getattribute__(self, "modified").add(name)
        else:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__, name
                )
            )

    def _diff(self):
        res = {}
        for k in self.modified:
            if isinstance(k, str):
                res[k] = self.__dict__[k]
            elif isinstance(k, int):
                res[k] = str(self.__dict__[k])
            elif isinstance(k, datetime):
                res[k] = str(int(self.__dict__[k].timestamp()))
            elif isinstance(k, set):
                res[k] = ",".join(self.__dict__[k])


class FormattedMessage(Message):
    pass


class FreeMessage(Message):
    pass


def get_message(htable: dict):
    # prnt("", pformat(htable))
    if htable["buffer_type"] == "formatted":
        return FormattedMessage(htable)
    elif htable["buffer_type"] == "free":
        return FreeMessage(htable)
    else:
        raise TypeError("htable is not a known buffer type")


class Event:
    def __init__(
        self,
        buffer_type: str,
        buffer_name: str,
        match_tags: str,
    ):
        self.ptr = None
        self.buffer_type = buffer_type
        self.buffer_name = buffer_name
        self.match_tags = match_tags

    def hook(self):
        """Install the hook for an event

        Raises:
            AssertionError: Raises if hook() is called in error or the callback variable is not set up correctly
        """
        assert self.ptr is None, "Event hook already installed"

        callback_name = self.__class__.__name__.lower() + "_cb"
        try:
            modname = next(
                inspect.getmodule(x[0]).__name__
                for x in inspect.stack()
                if x[1] != __file__
            )
            exec("from {} import {}".format(modname, callback_name))
            assert eval(callback_name) == self._callback
        except (AssertionError, ImportError) as e:
            raise AssertionError(
                "Weechat requires callbacks to exist in global scope of the source script. Use `{} = script.register_event({}(...))`".format(
                    callback_name, self.__class__.__name__
                )
            )

        ptr = w.hook_line(
            self.buffer_type, self.buffer_name, self.match_tags, callback_name, ""
        )
        assert ptr is not None, "weechat.hook_command failed"

        self.ptr = ptr

    def unhook(self):
        """Removes the hook for this command"""
        assert self.ptr is not None
        w.unhook(self.ptr)
        self.ptr = None

    def _callback(self, data: str, line: dict) -> dict:
        msg = get_message(line)
        self.callback(msg)
        return msg._diff()

    def callback(self, msg: Message) -> dict:
        """The method called when the event is matched

        Args:
            data (str): data passed from weechat (unknown??)
            line (object): object of the matching message

        Raises:
            NotImplementedError: [description]

        Returns:
            object: [description]
        """
        raise NotImplementedError("callback method not implemented")


class Command:
    def __init__(
        self,
        name: str,
        desc: str,
        args_syntax: str,
        args_desc: str,
        completion_template: str,
    ):
        """Base class for Weechat commands

        Args:
            name (str): Name of command, /<name>
            desc (str): Description of command, printed in /help <name>
            args_syntax (str): Command argument syntax, printed in /help <name>
            args_desc (str): Command argument detailed description, printed in /help <name>
            completion_template (str): Completion template for tab-completing arguments
        """
        self.ptr = None
        self.name = name
        self.desc = desc
        self.args_syntax = args_syntax
        self.args_desc = args_desc
        self.completion_template = completion_template

    def hook(self):
        """Install the hook for a command

        Raises:
            AssertionError: Raises if hook() is called in error or the callback variable is not set up correctly
        """
        assert self.ptr is None, "Command hook already installed"

        callback_name = self.name.lower() + "_cb"
        try:
            modname = next(
                inspect.getmodule(x[0]).__name__
                for x in inspect.stack()
                if x[1] != __file__
            )
            exec("from {} import {}".format(modname, callback_name))
            assert eval(callback_name) == self.callback
        except (AssertionError, ImportError) as e:
            raise AssertionError(
                "Weechat requires callbacks to exist in global scope of the source script. Use `{} = script.register_command({}(...))`".format(
                    callback_name, self.__class__.__name__
                )
            )

        ptr = w.hook_command(
            self.name,
            self.desc,
            self.args_syntax,
            self.args_desc,
            self.completion_template,
            callback_name,
            "",
        )
        assert ptr is not None, "weechat.hook_command failed"

        self.ptr = ptr

    def unhook(self):
        """Removes the hook for this command"""
        assert self.ptr is not None
        w.unhook(self.ptr)
        self.ptr = None

    def callback(self, data: str, buffer: str, args: str) -> int:
        """The method called when the command is run by the user

        Args:
            data (str): The arguments passed to the command
            buffer (str): Buffer reference for something??
            args (str): The arguments passed to the command

        Raises:
            NotImplementedError: Command is an abstract class, children must implement `callback`

        Returns:
            int: One of: weechat.WEECHAT_RC_OK, weechat.WEECHAT_RC_OK_EAT, weechat.WEECHAT_RC_ERROR
        """
        raise NotImplementedError("callback method not implemented")


class Script:
    def __init__(
        self,
        name: str,
        author: str,
        version: str,
        license: str,
        description: str,
    ) -> None:
        """Define a script

        Args:
            name (str): Name of script
            author (str): Author of script
            version (str): Version of script
            license (str): License of script
            description (str): Description of script
        """
        self.commands: List[Command] = []
        self.command_hooks: List[Command] = []
        self.events: List[Event] = []
        self.event_hooks: List[Event] = []
        self.ptr = None
        self.name = name
        self.author = author
        self.version = version
        self.license = license
        self.description = description

    def install(self):
        """Register a script

        Raises:
            AssertionError: Registration failed

        Returns:
            str: pointer to the script's handle
        """
        shutdown_name = self.name.lower() + "_shutdown"
        try:
            modname = next(
                inspect.getmodule(x[0]).__name__
                for x in inspect.stack()
                if x[1] != __file__
            )
            exec("from {} import {}".format(modname, shutdown_name))
            assert eval(shutdown_name) == self.shutdown
        except (AssertionError, ImportError):
            raise AssertionError(
                "Weechat requires callbacks to exist in global scope of the source script. Use `{} = {}.shutdown; {}.install()`".format(
                    shutdown_name,
                    self.__class__.__name__.lower(),
                    self.__class__.__name__.lower(),
                )
            )

        self.ptr = w.register(
            self.name,
            self.author,
            self.version,
            self.license,
            self.description,
            shutdown_name,
            "UTF-8",
        )

        for command in self.commands:
            try:
                command.hook()
                self.command_hooks.append(command)
            except Exception as e:
                w.prnt(
                    "",
                    "Failed to hook command {}: {}".format(
                        command.name, "; ".join(e.args)
                    ),
                )

        for event in self.events:
            try:
                event.hook()
                self.event_hooks.append(event)
            except Exception as e:
                w.prnt(
                    "",
                    "Failed to hook event {}: {}".format(
                        event.__class__.__name__, "; ".join(e.args)
                    ),
                )

        # self.event_hooks.append(w.hook_signal("*,irc_in_*", "irc_raw_in_cb", ""))
        self.on_register()

    def shutdown(self):
        self.before_shutdown()
        w.unhook_all()

        # for command in self.command_hooks:
        #     try:
        #         command.unhook()
        #     except Exception as e:
        #         w.prnt(
        #             "",
        #             "Failed to unhook command {}: {}".format(
        #                 command.name, "; ".join(e.args)
        #             ),
        #         )
        self.command_hooks.clear()

        # for event in self.event_hooks:
        #     try:
        #         event.unhook()
        #     except Exception as e:
        #         w.prnt(
        #             "",
        #             "Failed to unhook event {}: {}".format(
        #                 event.__class__.__name__, "; ".join(e.args)
        #             ),
        #         )
        self.event_hooks.clear()

        return ReturnCode.OK.value

    def register_command(self, command: Command) -> Callable[[str, str, str], int]:
        self.commands.append(command)
        return command.callback

    def register_event(self, event: Event) -> Callable[[str, dict], dict]:
        self.events.append(event)
        return event._callback

    def before_shutdown(self):
        """This function is called before shutting down the script"""
        pass

    def on_register(self):
        """This function is called on successful registration with WeeChat"""
        pass


def prnt(buffer: str, text: str):
    w.prnt(buffer, text)


_timers: Dict[str, Callable[[int], Any]] = {}


def timer_callback(data: str, remaining_calls: str) -> int:
    cb = _timers.pop(data, None)
    if cb:
        cb(int(remaining_calls))
    return ReturnCode.OK.value


def _cancel_timer(uuid: str, ptr: str):
    # w.prnt("", f"canceling timer {uuid = } {ptr = }")
    _timers.pop(uuid, None)
    w.unhook(ptr)


def set_timeout(delay: int, cb: Callable[[int], Any]) -> Callable:
    uuid = str(uuid4())
    _timers[uuid] = cb
    ptr = w.hook_timer(delay, 0, 1, "timer_callback", uuid)
    # w.prnt("", f"setting timer {uuid = } {ptr = } {len(_timers)}")
    return lambda: _cancel_timer(uuid, ptr)


def say(target: str, msg: str):
    buf = w.buffer_search("==", target)
    ret = w.command(buf, f"/say {msg}")
    if ret == ReturnCode.ERROR:
        raise RuntimeError("weechat.command() failed")
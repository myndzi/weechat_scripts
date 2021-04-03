# weechat scripting api stubs for vscode

# return codes

from typing import Optional


WEECHAT_RC_OK = -1
WEECHAT_RC_OK_EAT = -1
WEECHAT_RC_ERROR = -1

# configuration files
WEECHAT_CONFIG_READ_OK = -1
WEECHAT_CONFIG_READ_MEMORY_ERROR = -1
WEECHAT_CONFIG_READ_FILE_NOT_FOUND = -1
WEECHAT_CONFIG_WRITE_OK = -1
WEECHAT_CONFIG_WRITE_ERROR = -1
WEECHAT_CONFIG_WRITE_MEMORY_ERROR = -1
WEECHAT_CONFIG_OPTION_SET_OK_CHANGED = -1
WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE = -1
WEECHAT_CONFIG_OPTION_SET_ERROR = -1
WEECHAT_CONFIG_OPTION_SET_OPTION_NOT_FOUND = -1
WEECHAT_CONFIG_OPTION_UNSET_OK_NO_RESET = -1
WEECHAT_CONFIG_OPTION_UNSET_OK_RESET = -1
WEECHAT_CONFIG_OPTION_UNSET_OK_REMOVED = -1
WEECHAT_CONFIG_OPTION_UNSET_ERROR = -1

# sorted lists
WEECHAT_LIST_POS_SORT = -1
WEECHAT_LIST_POS_BEGINNING = -1
WEECHAT_LIST_POS_END = -1

# hotlist
WEECHAT_HOTLIST_LOW = -1
WEECHAT_HOTLIST_MESSAGE = -1
WEECHAT_HOTLIST_PRIVATE = -1
WEECHAT_HOTLIST_HIGHLIGHT = -1

# hook process
WEECHAT_HOOK_PROCESS_RUNNING = -1
WEECHAT_HOOK_PROCESS_ERROR = -1

# hook connect
WEECHAT_HOOK_CONNECT_OK = -1
WEECHAT_HOOK_CONNECT_ADDRESS_NOT_FOUND = -1
WEECHAT_HOOK_CONNECT_IP_ADDRESS_NOT_FOUND = -1
WEECHAT_HOOK_CONNECT_CONNECTION_REFUSED = -1
WEECHAT_HOOK_CONNECT_PROXY_ERROR = -1
WEECHAT_HOOK_CONNECT_LOCAL_HOSTNAME_ERROR = -1
WEECHAT_HOOK_CONNECT_GNUTLS_INIT_ERROR = -1
WEECHAT_HOOK_CONNECT_GNUTLS_HANDSHAKE_ERROR = -1
WEECHAT_HOOK_CONNECT_MEMORY_ERROR = -1
WEECHAT_HOOK_CONNECT_TIMEOUT = -1
WEECHAT_HOOK_CONNECT_SOCKET_ERROR = -1

# hook signal
WEECHAT_HOOK_SIGNAL_STRING = -1
WEECHAT_HOOK_SIGNAL_INT = -1
WEECHAT_HOOK_SIGNAL_POINTER = -1


def register(
    name: str,
    author: str,
    version: str,
    license: str,
    description: str,
    shutdown_function: str,
    charset: str,
):
    """Register a script with Weechat

    Args:
            name (string): Name of script
            author (string): Author of script
            version (string): Version of script
            license (string): License of script
            description (string): Description of script
            shutdown_function (string): Function name to call when unloading
            charset (string): Charset of the script itself
    """
    pass


def prnt(buffer: str, text: str):
    """Print text to a Weechat buffer

    Args:
            buffer (string): Buffer to print to. If "", prints to weechat buffer
            text (string): Message to print
    """
    pass


def hook_command(
    command: str,
    description: str,
    args: str,
    args_description: str,
    completion: str,
    callback: str,
    callback_data: str,
) -> str:
    """Install a command

    Args:
            command (string): Command name
            description (string): Description of command
            args (string): Argument descriptor
            args_description (string): Description of arguments (displayed in /help <command>)
            completion (string): Completion template
            callback (string): Name of function to execute when command is run
            callback_data (string): Pointer to callback data for reusing memory. Use "" for NULL

    Returns:
            str: Pointer to the installed hook
    """
    return ""


def hook_print(
    buffer: str,
    tags: str,
    message: str,
    strip_colors: int,
    callback: str,
    callback_data: str,
) -> str:
    """Install an event handler (after display)

    Args:
            buffer (str): The buffer pointer to hook; "" for any
            tags (str): Comma-separated list of weechat "tags" to match against. "it is possible to combine many tags as a logical "and" with separator +; wildcard * is allowed in tags"
            message (str): "only messages with this string will be caught (optional, case insensitive)"
            strip_colors (int): "if 1, colors will be stripped from message displayed, before calling callback"
            callback (str): Name of function to execute when a message matches
            callback_data (str): "pointer given to callback when it is called by WeeChat; if not NULL, it must have been allocated with malloc (or similar function) and it is automatically freed when the hook is deleted"

    Returns:
            str: Pointer to the installed hook
    """
    return ""


def hook_line(
    buffer_type: str, buffer_name: str, tags: str, callback: str, callback_data: str
) -> str:
    """Install an event handler (before display)

    Args:
        buffer_type (str): "catch lines on the given buffer type (if NULL or empty string, formatted is the default):"
            "formatted": catch lines on formatted buffers only (default)
            "free": catch lines on buffers with free content only
            "*": catch lines on all buffer types
        buffer_name (str): "comma-separated list of buffer masks (see buffer_match_list); NULL, empty string or "*" matches any buffer"
        tags (str): "catch only messages with these tags (optional): comma-separated list of tags that must be in message (logical "or"); it is possible to combine many tags as a logical "and" with separator +; wildcard * is allowed in tags"
        callback (str): Name of function to execute when a message matches
        callback_data (str): "pointer given to callback when it is called by WeeChat; if not NULL, it must have been allocated with malloc (or similar function) and it is automatically freed when the hook is deleted"

    Returns:
        str: Pointer to the installed hook
    """
    return ""


def hook_timer(
    interval: int,
    align_second: int,
    max_calls: int,
    callback: str,
    callback_data: str,
) -> str:
    """Sets a timer

    Args:
        interval (int): Frequency in milliseconds
        align_second (int): (0 = no?), (1-60): align to this second value
        max_calls (int): Number of times to execute
        callback (str): Name of function to execute when timer triggers
        callback_data (str): ????

    Returns:
        str: Pointer to the installed hook
    """
    pass


def unhook(ptr: str):
    """Unhook the hook referenced by the given pointer

    Args:
            ptr (string): Pointer to hook to unhook
    """


def unhook_all():
    """Unhook all hooks installed by this script"""


def string_remove_color(text: str, replacement: str) -> str:
    return ""


def command(buffer: Optional[str], input: str) -> int:
    return -1


def buffer_search(plugin: str, buffer_name: str) -> str:
    """Get a pointer reference to a buffer by plugin and buffer name.

    Args:
        plugin (str): Plugin to search in. `irc` is default. `==` is special; pass a fully qualified buffer name
        buffer_name (str): The buffer name to search for

    Returns:
        str: The pointer reference to the buffer
    """
    return ""


def hook_signal_send(signal: str, signal_type: int, signal_data: str):
    """Send a signal

    Args:
        signal (str): Name of signal to send
        signal_type (int): Type of data in `signal_data`
        signal_data (str): Data to send with the signal
    """
    pass


def hook_signal(signal: str, callback: str, callback_data: str):
    """Hook a signal

    Args:
        signal (str): The signal to hook
        callback (str): The name of the function to call
        callback_data (str): Arbitrary data to pass to the callback
    """
    pass


def hook_modifier(modifier: str, callback: str, callback_data: str):
    """Hook and modify data

    Args:
        modifier (str): The modifier to hook
        callback (str): The name of the function to call
        callback_data (str): Arbitrary data to pass to the callback
    """
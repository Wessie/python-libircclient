from __future__ import absolute_import
from functools import partial
from .lib.irc import ffi, lib
from .lib import convert_char_array, convert_strings


__all__ = ["Session"]


def event_callback(_self, session, event, origin, params, count):
    """
    Generic event handler, used for most events.
    """
    event, origin = convert_strings(event, origin)
    params = convert_char_array(params, count)

    print session, event, origin, params, count
event_callback.signature = "void(irc_session_t*, const char*, const char*, const char**, unsigned int)"


def event_dcc_chat(_self, session, nick, address, dccid):
    """
    Event handler for DCC CHAT requests.
    """
    nick, address = convert_strings(nick, address)

    print session, nick, address, dccid
event_dcc_chat.signature = "void(irc_session_t*, const char*, const char*, irc_dcc_t)"


def event_dcc_send(_self, session, nick, address, filename, size, dccid):
    """
    Event handler for DCC SEND requests.
    """
    nick, address, filename = convert_strings(nick, address, filename)

    print session, nick, address, filename, size, dccid
event_dcc_send.signature = "void(irc_session_t*, const char*, const char*, const char*, unsigned long, irc_dcc_t)"


def eventcode_callback(_self, session, event, origin, params, count):
    """
    Event handler for numeric events.
    """
    # Convert ourself to python objects as early as possible.
    origin = convert_strings(origin)
    params = convert_char_array(params, count)

    print session, event, origin, params, count
eventcode_callback.signature = "void(irc_session_t*, unsigned int, const char*, const char**, unsigned int)"


# A list of callback events we know off, this to simplify our struct populating.
_callback_members = {
    event_callback: [
        'event_connect',
        'event_nick',
        'event_quit',
        'event_join',
        'event_part',
        'event_mode',
        'event_umode',
        'event_topic',
        'event_kick',
        'event_channel',
        'event_privmsg',
        'event_notice',
        'event_channel_notice',
        'event_invite',
        'event_ctcp_req',
        'event_ctcp_rep',
        'event_ctcp_action',
        'event_unknown',
        ],
    eventcode_callback: [
        'event_numeric',
        ],
    event_dcc_chat: [
        'event_dcc_chat_req',
        ],
    event_dcc_send: [
        'event_dcc_send_req',
        ],
}



class Session(object):
    """
    A session for an IRC client.
    """
    def __init__(self):
        super(Session, self).__init__()

        self._create_callbacks()

        self._session = lib.irc_create_session(self._callbacks)

    def _create_callbacks(self):
        """
        Creates our C struct filled with our base-callbacks.

        Sets the result as `self._callbacks`.
        """
        callbacks = ffi.new("irc_callbacks_t *")

        for func, events in _callback_members.iteritems():
            # We want our callbacks to know which session they belong to,
            # while they do get their respective C session, they do not get
            # the python one, now they will!

            # Save the signature since partial will not copy them.
            signature = func.signature
            # Wrap the function so we pass it our current session
            func = partial(func, _self=self)
            # And get our cdata function type!
            func = ffi.callback(signature, func)

            for event in events:
                setattr(callbacks, event, func)

        self._callbacks = callbacks


    def add_handler(self, event, callback):
        pass

    def remove_handler(self, callback):
        pass

    def connect(self, server, port, passwd, nick, username, realname):
        pass

    def disconnect(self):
        ffi.irc_disconnect(self._session)

    def connected(self):
        return bool(ffi.irc_is_connected(self._session))

    def run(self):
        """
        Runs the client event loop until disconnect or call to quit.
        """
        ffi.irc_run(self._session)

    def join(self, channel, key=None):
        """
        Joins a channel on the server.
        """
        pass

    def part(self, channel):
        """
        Parts a channel, part message is not supported.
        """
        pass

    def invite(self, nick, channel):
        """
        Invites someone to a channel.
        """
        pass

    def names(self, channel):
        """
        Ask for the list of users in the channel.
        """
        pass

    def list(self, channels*):
        """
        Ask for a list of channels on the active server, if a channel is given it will instead
        return a list of users. This supports multiple channels.
        """
        pass

    def topic(self, channel, topic=None):
        """
        Sets the topic if topic is not None, otherwise returns the current topic.
        """
        pass

    def channel_mode(self, channel, mode=None):
        """
        Set channel mode.
        """
        pass

    def kick(self, nick, channel, reason):
        """
        Kicks someone from a channel.
        """
        pass

    def msg(self, nch, text):
        pass

    def me(self, nch, text):
        pass

    def notice(self, nch, text):
        pass

    def ctcp_request(self, nick, request):
        pass

    def ctcp_reply(self, nick, reply):
        pass

    def nick(self, newnick):
        pass

    def quit(self, reason):
        ffi.irc_cmd_quit(self._session, reason)

    def user_mode(self, mode):
        pass

    def whois(self, nick):
        pass

    def raw(self, format, *args, **kwargs):
        format = format.format(*args, **kwargs)


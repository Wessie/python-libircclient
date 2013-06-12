from __future__ import absolute_import
from functools import partial
from .lib.irc import ffi, lib
from .lib import convert_char_array, convert_strings
import threading
import collections


__all__ = ["Session"]


def call_handlers(event, h1, h2, args=None, kwargs=None):
    args = args or []
    kwargs = kwargs or {}

    for handler in h1.get_handlers_from_event(event):
        handler(*args, **kwargs)
    for handler in h2.get_handlers_from_event(event):
        handler(*args, **kwargs)


def event_callback(self, pyevent, session, event, origin, params, count):
    """
    Generic event handler, used for most events.
    """
    event, origin = convert_strings(event, origin)
    params = convert_char_array(params, count)

    call_handlers(pyevent, handlers, self.handlers,
                  (self, event, origin, params))
    print session, event, origin, params, count

event_callback.signature = ("void(irc_session_t*, const char*,"
                            "const char*, const char**, unsigned int)")


def event_dcc_chat(self, pyevent, session, nick, address, dccid):
    """
    Event handler for DCC CHAT requests.
    """
    nick, address = convert_strings(nick, address)

    call_handlers(pyevent, handlers, self.handlers,
                  (self, nick, address, dccid))
    print session, nick, address, dccid

event_dcc_chat.signature = ("void(irc_session_t*, const char*,"
                            "const char*, irc_dcc_t)")


def event_dcc_send(self, pyevent, session, nick,
                   address, filename, size, dccid):
    """
    Event handler for DCC SEND requests.
    """
    nick, address, filename = convert_strings(nick, address, filename)

    call_handlers(handlers, self.handlers,
                  (self, nick, address, filename, size, dccid))
    print session, nick, address, filename, size, dccid

event_dcc_send.signature = ("void(irc_session_t*, const char*, const char*,"
                            "const char*, unsigned long, irc_dcc_t)")


def eventcode_callback(self, pyevent, session, event, origin, params, count):
    """
    Event handler for numeric events.
    """
    # Convert ourself to python objects as early as possible.
    origin, = convert_strings(origin)
    params = convert_char_array(params, count)

    for handler in handlers.get_handlers_from_event(pyevent):
        handler(self, event, origin, params)
    print session, event, origin, params, count

eventcode_callback.signature = ("void(irc_session_t*, unsigned int,"
                                "const char*, const char**, unsigned int)")


# A list of callback events we know off, this to simplify our struct creation
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


class Handlers(object):
    events = set(
        event[6:] for sublist in
        _callback_members.itervalues() for event in sublist
    )

    def __init__(self):
        super(Handlers, self).__init__()
        self._callbacks = collections.defaultdict(list)

    def register(self, event, name=None):
        def wrapper(func):
            if not (event in self.events):
                # TODO: Check if we should raise an exception instead
                return func

            if name is not None:
                self._callback_names[name] = func
            self._callbacks[event].append(func)
            return func
        return wrapper

    def unregister(self, name):
        func = self._callback_names.get(name, None)
        if func is None:
            raise HandlerError("Handler does not exist with name: %r" % name)

        for _, l in self._callbacks.iteritems():
            l.remove(func)

    def get_handlers_from_event(self, event):
        event = event.lstrip("event_")
        return self._callbacks.get(event, [])


handlers = Handlers()


class Session(object):
    """
    A session for an IRC client.
    """
    def __init__(self):
        super(Session, self).__init__()

        self._create_callbacks()

        self._session = lib.irc_create_session(self._callbacks)

        self.handlers = Handlers()

    def _create_callbacks(self):
        """
        Creates our C struct filled with our base-callbacks.

        Sets the result as `self._callbacks`.
        """
        callbacks = ffi.new("irc_callbacks_t *")
        callback_store = []

        for origin_func, events in _callback_members.iteritems():
            # We want our callbacks to know which session they belong to,
            # while they do get their respective C session, they do not get
            # the python one, now they will!

            # Save the signature since partial will not copy them.
            signature = origin_func.signature

            for event in events:
                 # Wrap the function so we pass it our current session
                func = partial(origin_func, self, event)
                # And get our cdata function type!
                func = ffi.callback(signature, func)
                # set it on the struct
                setattr(callbacks, event, func)
                # Keep a reference around so it won't be deallocated
                callback_store.append(func)

        self._callbacks = callbacks
        self._callback_store = callback_store

    def connect(self, server, port, passwd, nick,
                username=ffi.NULL, realname=ffi.NULL):
        lib.irc_connect(
            self._session,
            server,
            port,
            passwd,
            nick,
            username,
            realname
        )

    def disconnect(self):
        lib.irc_disconnect(self._session)

    def connected(self):
        return bool(lib.irc_is_connected(self._session))

    def run(self, threaded=True):
        """
        Runs the client event loop until disconnect or call to quit.
        """
        if threaded:
            thread = threading.Thread(target=self.run,
                                      kwargs={"threaded": False})
            thread.daemon = True
            thread.start()
        else:
            lib.irc_run(self._session)

    def join(self, channel, key=ffi.NULL):
        """
        Joins a channel on the server.
        """
        lib.irc_cmd_join(self._session, channel, key)

    def part(self, channel):
        """
        Parts a channel, part message is not supported.
        """
        lib.irc_cmd_part(self._session, channel)

    def invite(self, nick, channel):
        """
        Invites someone to a channel.
        """
        lib.irc_cmd_invite(self._session, nick, channel)

    def names(self, *channels):
        """
        Ask for the list of users in the channel.
        """
        lib.irc_cmd_names(self._session, ",".join(channels))

    def list(self, *channels):
        """
        Ask for a list of channels on the active server, if a channel is
        given it will instead return a list of users. This supports multiple
        channels.
        """
        lib.irc_cmd_list(self._session, ",".join(channels))

    def topic(self, channel, topic=ffi.NULL):
        """
        Sets the topic if topic is not None, otherwise returns
        the current topic.
        """
        lib.irc_cmd_topic(self._session, channel, topic)

    def channel_mode(self, channel, mode=ffi.NULL):
        """
        Set channel mode.
        """
        lib.irc_cmd_channel_mode(self._session, channel, mode)

    def kick(self, nick, channel, reason=ffi.NULL):
        """
        Kicks someone from a channel.
        """
        lib.irc_cmd_kick(self._session, nick, channel, reason)

    def msg(self, nch, text):
        lib.irc_cmd_msg(self._session, nch, text)

    def me(self, nch, text):
        lib.irc_cmd_me(self._session, nch, text)

    def notice(self, nch, text):
        lib.irc_cmd_notice(self._session, nch, text)

    def ctcp_request(self, nick, request):
        lib.irc_cmd_ctcp_request(self._session, nick, request)

    def ctcp_reply(self, nick, reply):
        lib.irc_cmd_ctcp_reply(self._session, nick, reply)

    def nick(self, newnick):
        lib.irc_cmd_nick(self._session, newnick)

    def quit(self, reason=ffi.NULL):
        lib.irc_cmd_quit(self._session, reason)

    def user_mode(self, mode=ffi.NULL):
        lib.irc_cmd_user_mode(self._session, mode)

    def whois(self, *nicks):
        lib.irc_cmd_whois(self._session, ",".join(nicks))

    def raw(self, format, *args, **kwargs):
        format = format.format(*args, **kwargs)
        lib.irc_send_raw(self._session, format)

    def get_nick(self, source):
        buff = ffi.new("char[90]")
        lib.irc_target_get_nick(source, buff, 90)

        return ffi.string(buff, 90)



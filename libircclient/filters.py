def boolean_filter(func):
    filter_func = [None]

    def callback_getter(callback):
        def callback_wrapper(*args, **kwargs):
            if filter_func[0](*args, **kwargs):
                callback(*args, **kwargs)
        return callback_wrapper

    def filter_wrapper(*args, **kwargs):
        filter_func[0] = func(*args, **kwargs)

        return callback_getter

    return filter_wrapper


class Filters(object):
    @boolean_filter
    def channel(*channels):
        def filter(session, event, source, params):
            return params[0] in channels

        return filter

    @boolean_filter
    def nick(*nicks):
        def filter(session, event, source, params):
            return session.get_nick(source) in nicks
        return filter

filters = Filters()

from __future__ import absolute_import
from .irc import ffi


def convert_char_array(char_array, length):
    """
    Utility function that converts a cdata char * * into a list of python strings.

    This uses `ffi.string` internally which supports wchar_t alongside char.
    """
    strings = []
    for i in xrange(length):
        strings.append(ffi.string(char_array[i]))
    return strings

def convert_strings(*chars):
    """
    Utility function that passes all functions given to `ffi.string` and then returns it.

    This returns a generator.
    """
    return (ffi.string(string) for string in chars)

from __future__ import absolute_import
import os
from cffi import FFI
from .constants import *

CURRENT_DIR = os.path.join(os.path.dirname(__file__))

ffi = FFI()

with open(os.path.join(CURRENT_DIR, 'cffi_header.h')) as file:
    header = file.read()
ffi.cdef(header)

lib = ffi.dlopen(os.path.join(CURRENT_DIR, "libircclient.so"))

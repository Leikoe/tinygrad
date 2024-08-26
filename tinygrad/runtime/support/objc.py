from typing import Dict, Tuple, Union, Any
import functools, ctypes, ctypes.util
import tinygrad.runtime.autogen.objc as libobjc
# note: The Objective-C runtime does not expose enough information to provide completely automatic bindings of all APIs. source: https://pyobjc.readthedocs.io/en/latest/metadata/index.html
# though it's possible to parse bridgesupport files

def convert_arg(arg, arg_type):
  if isinstance(arg, ObjcObject): assert not arg.released, f"use after free ({arg})"
  if isinstance(arg, str) and arg_type is ctypes.c_char_p: return arg.encode()
  if isinstance(arg, str) and arg_type is ctypes.c_void_p: return NSString.stringWithUTF8String_(arg)
  if isinstance(arg, list) or isinstance(arg, tuple) and arg_type is ctypes.c_void_p: return (ctypes.c_void_p * len(arg))(*arg)
  return arg

@functools.lru_cache(maxsize=None)
def sel_registerName(sel: str) -> ctypes.c_void_p: return libobjc.sel_registerName(sel.encode())

def objc_msgSend(obj: ctypes.c_void_p, sel: str, *args, restype=None, argtypes=None):
  base_argtypes = [ctypes.c_void_p, ctypes.c_void_p]
  encoded_args = [convert_arg(a, t) for a, t in zip(args, argtypes)] if argtypes else []
  # print(f"Sending {sel}(restype:{restype} argtypes:{argtypes}) to ptr:{obj} with args:{args}")
  libobjc.objc_msgSend.restype, libobjc.objc_msgSend.argtypes = restype, ((base_argtypes + argtypes) if argtypes else base_argtypes)
  return libobjc.objc_msgSend(obj, sel_registerName(sel), *encoded_args)

libc = ctypes.CDLL(None)
libc.free.argtypes = [ctypes.c_void_p]

def dump_objc_methods(clz: ctypes.c_void_p) -> Dict[str, Tuple[str, str]]:
  method_count = ctypes.c_uint()
  methods_ptr = libobjc.class_copyMethodList(clz, ctypes.byref(method_count))
  assert methods_ptr is not None, f"Failed to get methods for class {clz}"

  methods = {}
  for i in range(method_count.value):
    method = methods_ptr[i]
    sel_name = ctypes.string_at(libobjc.sel_getName(libobjc.method_getName(method))).decode('ascii')
    return_type_p = libobjc.method_copyReturnType(method)
    return_type = ctypes.string_at(return_type_p).decode('ascii')
    argtypes_ps = tuple(libobjc.method_copyArgumentType(method, j) for j in range(libobjc.method_getNumberOfArguments(method)))
    methods[sel_name] = (return_type, tuple(ctypes.string_at(arg).decode('ascii') for arg in argtypes_ps))

    for p in argtypes_ps: libc.free(p)
    libc.free(return_type_p)
  libc.free(methods_ptr)
  return methods

SIMPLE_TYPES = {
    'c': ctypes.c_char,
    'i': ctypes.c_int,
    's': ctypes.c_short,
    'l': ctypes.c_long,
    'q': ctypes.c_longlong,
    'C': ctypes.c_uint8,
    'I': ctypes.c_uint,
    'S': ctypes.c_ushort,
    'L': ctypes.c_ulong,
    'Q': ctypes.c_ulonglong,
    'f': ctypes.c_float,
    'd': ctypes.c_double,
    'B': ctypes.c_bool,
    'v': None,
    '*': ctypes.c_char_p,
    '@': ctypes.c_void_p,
    '#': 'Class',
    ':': 'SEL',
    '?': '<unknown-type>',
}

@functools.lru_cache(maxsize=None)
def get_methods_rec(c: int):
  p = ctypes.c_void_p(c)
  methods = {}
  while p:
    methods.update(dump_objc_methods(p))
    p = libobjc.class_getSuperclass(p)
  return methods

def objc_type_to_ctype(t: str):
  if len(t) == 1: return SIMPLE_TYPES[t]
  if t[0] == "^": return ctypes.POINTER(objc_type_to_ctype(t[1:]))
  if t[0] in ["r", "V"]: return objc_type_to_ctype(t[1:])
  if t[0] == "{" and "=" in t and t[-1] == "}": return ctypes.Structure  # wooo! safety is out the window now
  raise ValueError(f"Unknown type {t}")

class ObjcMethod:
  def __init__(self, f, out_err=False, ret_ptr=False):
    self.f, self.out_err, self.ret_ptr = f, out_err, ret_ptr
  def __call__(self, *args, **kwargs):
    err = ctypes.c_void_p()  # find a way to not create this?
    res = self.f(*args[:-1], ctypes.byref(err), **kwargs) if self.out_err else self.f(*args, **kwargs)
    if res and self.ret_ptr: res = ObjcObject(res)
    if res and self.out_err: res = (res, None if err.value is None else ObjcObject(err.value))
    return res

@functools.lru_cache(maxsize=None)
def build_method(name, sel_name, restype, argtypes):
  """hashable args for lru_cache, this should only be ran once for each called method name"""
  # print(f"Building method {name} with sel_name {sel_name} restype {restype} argtypes {argtypes}")
  def f(p):
    _f = functools.partial(objc_msgSend, p, sel_name, restype=objc_type_to_ctype(restype),
          argtypes=[objc_type_to_ctype(t) for t in argtypes[2:]])
    return ObjcMethod(_f, out_err=name.endswith("error_"), ret_ptr=restype == "@")
  return f


class ObjcObject(ctypes.c_void_p):
  def __init__(self, p:int, manual_release=False):
    assert p, "Can't create ObjcObject with null ptr"
    super().__init__(p)
    self.methods_info = get_methods_rec(libobjc.object_getClass(self))
    self.manual_release = manual_release
    self.released = False

  @classmethod
  def from_classname(cls, name:str):
    p = libobjc.objc_getClass(name.encode())
    assert p, f"Class {name} not found"
    return cls(p, manual_release=True)

  def __repr__(self) -> str:
    return f"<{ctypes.string_at(libobjc.object_getClassName(ctypes.c_void_p(self.value))).decode()} at 0x{self.value:x}>"

  def __hash__(self) -> int:
    return 0 if self.value is None else self.value

  def __getattr__(self, name:str) -> Any:
    sel_name = name.replace("_", ":")
    if sel_name in self.methods_info: return build_method(name, sel_name, *self.methods_info[sel_name])(self)
    raise AttributeError(f"Method {name} not found on {self.__class__.__name__}")

  def __del__(self):
    if self.manual_release:
      # print(f"Releasing {self}")
      self.released = True
      self.release()

NSString: Any = ObjcObject.from_classname("NSString")

def nsstring_to_str(nsstring) -> str:
  return ctypes.string_at(nsstring.UTF8String(), size=nsstring.length()).decode()

from typing import Dict, Union, Any
import functools, ctypes, ctypes.util
# note: The Objective-C runtime does not expose enough information to provide completely automatic bindings of all APIs. source: https://pyobjc.readthedocs.io/en/latest/metadata/index.html

# import tinygrad.runtime.autogen.objc as objc
libobjc = ctypes.CDLL(ctypes.util.find_library("objc"))
libobjc.objc_msgSend.restype, libobjc.objc_msgSend.argtypes = ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]
libobjc.objc_getClass.restype, libobjc.objc_getClass.argtypes = ctypes.c_void_p, [ctypes.c_char_p]
libobjc.class_copyMethodList.restype, libobjc.class_copyMethodList.argtypes = ctypes.POINTER(ctypes.c_void_p), [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
libobjc.class_getName.restype, libobjc.class_getName.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.sel_registerName.restype, libobjc.sel_registerName.argtypes = ctypes.c_void_p, [ctypes.c_char_p]
libobjc.sel_getName.restype, libobjc.sel_getName.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.method_getName.restype, libobjc.method_getName.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
libobjc.method_getTypeEncoding.restype, libobjc.method_getTypeEncoding.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.method_copyReturnType.restype, libobjc.method_copyReturnType.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.method_getNumberOfArguments.restype, libobjc.method_getNumberOfArguments.argtypes = ctypes.c_uint, [ctypes.c_void_p]
libobjc.method_copyArgumentType.restype, libobjc.method_copyArgumentType.argtypes = ctypes.c_char_p, [ctypes.c_void_p, ctypes.c_uint]
libobjc.object_getClassName.restype, libobjc.object_getClassName.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.object_getClass.restype, libobjc.object_getClass.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
libobjc.class_getSuperclass.restype, libobjc.class_getSuperclass.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
libobjc.object_dispose.argtypes = [ctypes.c_void_p]

def convert_arg(arg, type):
  if isinstance(arg, str) and type is ctypes.c_char_p: return arg.encode()
  if isinstance(arg, str) and type is ctypes.c_void_p: return NSString.stringWithUTF8String_(arg)
  if isinstance(arg, list) or isinstance(arg, tuple) and type is ctypes.c_void_p: return (ctypes.c_void_p * len(arg))(*arg)
  return arg

@functools.lru_cache(maxsize=None)
def sel_registerName(sel: str) -> ctypes.c_void_p:
  return libobjc.sel_registerName(sel.encode())

def objc_msgSend(obj: ctypes.c_void_p, sel: str, *args, restype=None, argtypes=[]):
  base_argtypes = [ctypes.c_void_p, ctypes.c_void_p]
  encoded_args = [convert_arg(a, t) for a, t in zip(args, argtypes)]
  # print(f"Sending {sel}(restype:{restype} argtypes:{argtypes}) to ptr:{obj} with args:{args}")
  libobjc.objc_msgSend.restype, libobjc.objc_msgSend.argtypes = restype, ((base_argtypes + argtypes) if argtypes else base_argtypes)
  return libobjc.objc_msgSend(obj, sel_registerName(sel), *encoded_args)

libc = ctypes.CDLL(None)
libc.free.argtypes = [ctypes.c_void_p]

def dump_objc_methods(clz: ctypes.c_void_p):
  method_count = ctypes.c_uint()
  methods_ptr = libobjc.class_copyMethodList(clz, ctypes.byref(method_count))
  assert methods_ptr is not None, f"Failed to get methods for class {clz}"
  class_name = libobjc.class_getName(clz).decode('ascii')

  methods = {}
  for i in range(method_count.value):
    method = methods_ptr[i]
    sel_name = libobjc.sel_getName(libobjc.method_getName(method)).decode('ascii')
    return_type = libobjc.method_copyReturnType(method).decode('ascii')  # should free?
    argtypes = tuple(libobjc.method_copyArgumentType(method, j).decode('ascii') for j in range(libobjc.method_getNumberOfArguments(method)))  # should free?
    methods[sel_name] = {"restype": return_type, "argtypes": tuple(arg for arg in argtypes)}
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
def get_methods_rec(c: ctypes.c_void_p):
  methods = {}
  while c:
    methods.update(dump_objc_methods(c))
    c = libobjc.class_getSuperclass(c)
  return methods


def objc_type_to_ctype(t: str):
  if len(t) == 1:
    return SIMPLE_TYPES[t]
  elif t[0] == '^':
    return ctypes.POINTER(objc_type_to_ctype(t[1:]))
  elif t[0] == 'r':
    return objc_type_to_ctype(t[1:])
  elif t[0] == "V":
    return objc_type_to_ctype(t[1:])
  elif t.startswith("{") and "=" in t and t.endswith("}"):
    return ctypes.Structure  # wooo! safety is out the window now
  else:
    raise ValueError(f"Unknown type {t}")


@functools.lru_cache(maxsize=None)
def build_method(name, sel_name, restype, argtypes):
  """hashable args for lru_cache, this should only be ran once for each called method name"""
  print(f"Building method {name} with sel_name {sel_name} restype {restype} argtypes {argtypes}")
  f = lambda p: functools.partial(objc_msgSend,
      p,
      sel_name,
      restype=objc_type_to_ctype(restype),
      argtypes=[objc_type_to_ctype(t) for t in argtypes[2:]])
  # ugly hack to conditionally wrap without self referencing recursion. e.g: "f = lambda *args: g(f(*args))"
  _f = lambda p: ((lambda *args, **kwargs: ObjcInstance(r) if (r:=f(p)(*args, **kwargs)) is not None else None) if restype == "@" else f(p))
  return lambda p: ((lambda *args, **kwargs: (_f(p)(*args[:-1], ctypes.byref(err:=ctypes.c_void_p()), **kwargs), err if err.value else None)) if name.endswith("error_") else _f(p))


class ObjcClass(ctypes.c_void_p):
  def __init__(self, name:str):
    super().__init__(libobjc.objc_getClass(name.encode()))
    assert self.value, f"Class {name} not found"
    self.methods_info: Dict[str, Dict[str, Any]] = get_methods_rec(_metaclass_ptr:=libobjc.object_getClass(self))

  def __hash__(self) -> int:
    return self.value

  def __getattr__(self, name:str) -> Any:
    sel_name = name.replace("_", ":")
    if sel_name in self.methods_info:
      method_info = self.methods_info[sel_name]
      restype, argtypes = method_info["restype"], method_info["argtypes"]
      return build_method(name, sel_name, restype, argtypes)(self)  # use cached method

    raise AttributeError(f"Method {name} not found on {self.__class__.__name__}")


class ObjcInstance(ObjcClass):
  def __init__(self, ptr: Union[int, ctypes.c_void_p, None]):
    v = ptr.value if isinstance(ptr, ctypes.c_void_p) else ptr
    assert v, f"Can't create ObjcInstance with null ptr"
    super(ctypes.c_void_p, self).__init__(v)
    self.methods_info = get_methods_rec(libobjc.object_getClass(self))
  def __del__(self):
    # print(f"Releasing {self}")
    self.release()

NSString: Any = ObjcClass("NSString")

def nsstring_to_str(nsstring) -> str:
  return ctypes.string_at(nsstring.UTF8String(), size=nsstring.length()).decode()

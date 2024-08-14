import ctypes
from tinygrad.helpers import objc_msgSend, dump_objc_methods, libobjc, ensure_bytes, makeObjcClass

metal = ctypes.CDLL("/System/Library/Frameworks/Metal.framework/Metal")
core_graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")

metal.MTLCreateSystemDefaultDevice.restype = ctypes.c_void_p
metal.MTLCreateSystemDefaultDevice.argtypes = []

dev_ptr = metal.MTLCreateSystemDefaultDevice()

libobjc.object_getClassName.restype, libobjc.object_getClassName.argtypes = ctypes.c_char_p, [ctypes.c_void_p]
libobjc.object_getClass.restype, libobjc.object_getClass.argtypes = ctypes.c_void_p, [ctypes.c_void_p]
libobjc.class_getSuperclass.restype, libobjc.class_getSuperclass.argtypes = ctypes.c_void_p, [ctypes.c_void_p]

NSString = makeObjcClass("NSString")
# print(NSString.stringWithUTF8String_(b"Hello, World!"))
print(NSString["stringWithUTF8String_"](b"Hello, World!"))
exit(0)

# NSString = ObjcClass("NSString")
# NSArray = ObjcClass("NSArray")
# def to_nsstring(s: bytes):
#   r = NSString.stringWithUTF8String_(ctypes.create_string_buffer(s))
#   assert r is not None
#   return r
# def from_nsstring(nsstring: ctypes.c_void_p):
#     return ctypes.string_at(objc_msgSend(nsstring, "UTF8String"), size=objc_msgSend(nsstring, "length")).decode()
# def from_nsdata(nsdata: ctypes.c_void_p):
#     return ctypes.string_at(objc_msgSend(nsdata, "bytes"), size=objc_msgSend(nsdata, "length"))






# dev = ObjcClass("MTLDevice", ptr=None)
# print(dev.supportsRaytracing())

# class Metal:
#   MTLCompileOptions = ObjcClass("MTLCompileOptions")

# # options = Metal.MTLCompileOptions.new()
# # options.setFastMathEnabled_(getenv("METAL_FAST_MATH"))

# source = """
# #include <metal_stdlib>
# using namespace metal;
# kernel void r_32_256_2_20_20n1(device float* data0, const device float* data1, const device float* data2, const device float* data3, const device float* data4, const device float* data5, const device float* data6, uint3 gid [[threadgroup_position_in_grid]], uint3 lid [[thread_position_in_threadgroup]]) {
#   threadgroup float temp[256];
#   int gidx0 = gid.x; /* 32 */
#   int lidx1 = lid.x; /* 256 */
#   float acc0 = 0.0f;
#   float val0 = *(data2+gidx0);
#   float val1 = *(data3+gidx0);
#   for (int ridx0 = 0; ridx0 < 2; ridx0++) {
#     for (int ridx1 = 0; ridx1 < 20; ridx1++) {
#       for (int ridx2 = 0; ridx2 < 20; ridx2++) {
#         float val2 = *(data1+(gidx0*400)+(lidx1*25600)+(ridx0*12800)+(ridx1*20)+ridx2);
#         int alu0 = ((gidx0*100)+(lidx1*6400)+(ridx0*3200)+((ridx1/2)*10)+(ridx2/2));
#         float val3 = *(data4+alu0);
#         float val4 = *(data5+alu0);
#         float val5 = *(data6+alu0);
#         float alu1 = (val2-val0);
#         acc0 = 0;
#         acc0 = ((alu1*val1*((float)(((alu1*val1)==val3))/val4)*val5)+acc0);
#       }
#     }
#   }
#   *(temp+lidx1) = acc0;
#   threadgroup_barrier(mem_flags::mem_threadgroup);
#   if ((lidx1<1)) {
#     float acc1 = 0.0f;
#     for (int ridx3 = 0; ridx3 < 256; ridx3++) {
#       float val6 = *(temp+ridx3);
#       acc1 = (val6+acc1);
#     }
#     *(data0+gidx0) = acc1;
#   }
# }"""

# library = dev.newLibraryWithSource_options_error_(to_nsstring(source.encode()), ctypes.c_void_p(0), ctypes.c_void_p(0))
# print(library._obj)
# exit(0)
# try: library = unwrap2(self.device.device.newLibraryWithSource_options_error_(src, options, None))
# except AssertionError as e: raise CompileError(e) from e
# lib = library.libraryDataContents().bytes().tobytes()

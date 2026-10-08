"""Cross-platform Deep Memory Reclaim and Garbage Collection Utilities."""

import gc
import sys
import ctypes
import logging

logger = logging.getLogger(__name__)


def force_garbage_collection_and_trim() -> None:
    """Thu hồi bộ nhớ đa nền tảng:

    1. Thu gom toàn diện mọi thế hệ đối tượng Python (gc.collect).
    2. Gọi API giải phóng heap đặc thù của từng hệ điều hành (Linux / macOS / Windows).
    """
    # Bước 1: Thu gom rác Python VM
    # Chỉ thực hiện thu gom generation 2 nếu thực sự có rác tích tụ để tránh block event loop
    stats = gc.get_count()
    if stats[2] > 0 or stats[1] > 50:
        gc.collect(generation=2)
    else:
        gc.collect(generation=0)

    # Bước 2: OS Heap Trimming theo nền tảng
    platform = sys.platform

    if platform.startswith("linux"):
        # Linux (glibc arena trimming)
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            libc.malloc_trim.argtypes = [ctypes.c_size_t]
            libc.malloc_trim.restype = ctypes.c_int
            libc.malloc_trim(0)
        except (OSError, AttributeError) as e:
            logger.debug("Linux malloc_trim skipped: %s", e)

    elif platform == "darwin":
        # macOS (Darwin libSystem)
        try:
            libc = ctypes.CDLL("libSystem.B.dylib", use_errno=True)
            if hasattr(libc, "malloc_zone_pressure_relief"):
                libc.malloc_zone_pressure_relief.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                libc.malloc_zone_pressure_relief.restype = ctypes.c_size_t
                libc.malloc_zone_pressure_relief(None, 0)
        except (OSError, AttributeError) as e:
            logger.debug("macOS memory relief skipped: %s", e)

    elif platform == "win32":
        # Windows (Default Process Heap Compaction)
        try:
            kernel32 = ctypes.windll.kernel32
            # Bắt buộc khai báo restype và argtypes để tránh truncate 64-bit pointer thành 32-bit int
            kernel32.GetProcessHeap.restype = ctypes.c_void_p
            kernel32.HeapCompact.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel32.HeapCompact.restype = ctypes.c_size_t

            heap = kernel32.GetProcessHeap()
            if heap:
                kernel32.HeapCompact(heap, 0)
        except (OSError, AttributeError) as e:
            logger.debug("Windows HeapCompact skipped: %s", e)

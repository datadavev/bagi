"""Implement a RO FUSE drve for FSSpec filesystems."""

import errno
import logging
import os
import stat
import time

import fsspec
import mfusepy as fuse


def get_logger():
    return logging.getLogger("fuse")


class FSSpecFUSE(fuse.Operations):
    """FUSE operations adapter using an fsspec filesystem instance."""

    def __init__(self, fs: fsspec.AbstractFileSystem, path: str | None = None):
        self.fs = fs
        self.fd_counter = 0
        self.open_files: dict = {}  # type: ignore[var-annotated]
        if path is None:
            path = ""
        self.root = path.rstrip("/")

    def getattr(self, path, fh=None):
        _L = get_logger()
        _L.debug("getarr.PATH1 = %s", path)
        path = "".join([self.root, path.lstrip("/")]).rstrip("/")
        _L.debug("getarr.PATH2 = %s", path)
        try:
            info = self.fs.info(path)
        except FileNotFoundError:
            raise fuse.FuseOSError(errno.ENOENT) from None

        data = {"st_uid": info.get("uid", 1000), "st_gid": info.get("gid", 1000)}
        perm = info.get("mode", 0o777)

        if info["type"] != "file":
            data["st_mode"] = stat.S_IFDIR | perm
            data["st_size"] = 0
            data["st_blksize"] = 0
        else:
            data["st_mode"] = stat.S_IFREG | perm
            data["st_size"] = info["size"]
            data["st_blksize"] = 5 * 2**20
            data["st_nlink"] = 1
        data["st_atime"] = info["atime"] if "atime" in info else time.time()
        data["st_ctime"] = info["ctime"] if "ctime" in info else time.time()
        data["st_mtime"] = info["mtime"] if "mtime" in info else time.time()
        _L.debug("getarr INFO %s", data)
        return data

    def readdir(self, path, fh):
        _L = get_logger()
        _L.debug("readdir.PATH = %s", path)
        entries = [".", ".."]
        path = "".join([self.root, path.lstrip("/")])
        _L.debug("readdir.PATH = %s", path)
        try:
            listing = self.fs.ls(path, detail=False)
            for item in listing:
                entries.append(os.path.basename(item.rstrip("/")))
        except FileNotFoundError:
            raise fuse.FuseOSError(errno.ENOENT) from None
        _L.debug(entries)
        return entries

    def open(self, path, flags):
        path = "".join([self.root, path.lstrip("/")])
        self.fd_counter += 1
        fd = self.fd_counter
        try:
            f = self.fs.open(path, "rb")
            self.open_files[fd] = f
        except FileNotFoundError:
            raise fuse.FuseOSError(errno.ENOENT) from None
        return fd

    def read(self, path, size, offset, fh):
        path = "".join([self.root, path.lstrip("/")])
        if fh not in self.open_files:
            raise fuse.FuseOSError(errno.EBADF)
        f = self.open_files[fh]
        f.seek(offset)
        return f.read(size)

    def release(self, path, fh):
        path = "".join([self.root, path.lstrip("/")])
        if fh in self.open_files:
            self.open_files[fh].close()
            del self.open_files[fh]
        return 0

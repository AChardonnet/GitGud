import os
import hashlib
import zlib
import collections
import struct
import operator


def init(repository):
    """Initialize a new gitGud repository."""
    os.makedirs(repository, exist_ok=True)
    os.makedirs(os.path.join(repository, ".gitGud"))
    os.makedirs(os.path.join(repository, ".gitGud", "objects"))
    print(f"Initialized empty gitGud repository in {repository}")


def readFile(path):
    """Reads the contents of a file. Encoded in bytes"""
    with open(path, "rb") as file:
        return file.read()


def writeFile(path, data):
    """Write data to a file. Encoded in bytes"""
    with open(path, "wb") as file:
        file.write(data)


def hashObject(data, objectType, write=True):
    """
    Compute SHA-1 hash of the given data and optionally write it to the object database.
    Return SHA-1 object hash as hex string
    """
    header = f"{objectType} {len(data)}".encode()
    data = header + b"\x00" + data
    hash = hashlib.sha1(data).hexdigest()
    if write:
        path = os.path.join(".gitGud", "objects", hash[:2], hash[2:])
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            writeFile(path, zlib.compress(data))
    return hash


def findObject(hash):
    """
    Find an object from it's SHA-1 hash and returns it's path.
    Raise ValueError if not found.
    """
    objectDirectory = os.path.join(".gitGud", "objects", hash[:2])
    objectName = hash[2:]
    objects = []
    for object in os.listdir(objectDirectory):
        if object == objectName:
            objects.append(object)
    if len(objects) == 0:
        raise ValueError(f"Object not found")
    if len(objects) > 1:
        raise ValueError("Multiple objects found")
    return os.path.join(objectDirectory, objects[0])


def readObject(hash):
    """
    Finds then reads an object from it's SHA-1 hash and returns it's content as a tuple : (objectType, data).
    Raise ValueError if not found.
    """
    path = findObject(hash)
    objectContent = zlib.decompress(readFile(path))
    firstNulByteIndex = objectContent.index(b"\x00")
    header = objectContent[:firstNulByteIndex]
    objectType, size = header.decode().split()
    size = int(size)
    data = objectContent[firstNulByteIndex + 1 :]
    assert (
        len(data) == size
    ), f"Data is the wrong size. Expected {size}, got {len(data)}"
    return (objectType, data)


IndexEntry = collections.namedtuple(
    "IndexEntry",
    [
        "ctime_s",
        "ctime_n",
        "mtime_s",
        "mtime_n",
        "dev",
        "ino",
        "mode",
        "uid",
        "gid",
        "size",
        "sha1",
        "flags",
        "path",
    ],
)


def writeIndex(entries):
    """
    Write a list of index entries as IndexEntries objects to the index.
    """
    encodedEntries = []
    for entry in entries:
        print(
            entry.ctime_s,
            entry.ctime_n,
            entry.mtime_s,
            entry.mtime_n,
            entry.dev,
            entry.ino,
            entry.mode,
            entry.uid,
            entry.gid,
            entry.size,
            entry.sha1,
            entry.flags,
        )
        entryHead = struct.pack(
            "!LLLLLLLLLL20sH",
            entry.ctime_s,
            entry.ctime_n,
            entry.mtime_s,
            entry.mtime_n,
            entry.dev,
            entry.ino,
            entry.mode,
            entry.uid,
            entry.gid,
            entry.size,
            entry.sha1,
            entry.flags,
        )
        path = entry.path.encode()
        length = ((62 + len(path) + 8) // 8) * 8
        encodedEntry = entryHead + path + b"\x00" * (length - 62 - len(path))
        encodedEntries.append(encodedEntry)
    header = struct.pack("!4sLL", b"DIRC", 2, len(entries))
    data = header + b"".join(encodedEntries)
    hash = hashlib.sha1(data).digest()
    writeFile(os.path.join(".gitGud", "index"), data + hash)


def readIndex():
    """
    Read the index and return a list of index entries as IndexEnties objects.
    """
    try:
        data = readFile(os.path.join(".gitGud", "index"))
    except FileNotFoundError:
        return []
    hash = hashlib.sha1(data[:-20]).digest()
    assert hash == data[-20:], "Missmatched hashes"
    signature, version, nEntries = struct.unpack("!4sLL", data[:12])
    assert signature == b"DIRC", "invalid signature"
    assert version == 2, "invalid version"
    entriesData = data[12:-20]
    entries = []
    i = 0
    while i + 62 < len(entriesData):
        fieldsEnd = i + 62
        fields = struct.unpack("!LLLLLLLLLL20sH", entriesData[i:fieldsEnd])
        """
        ! : big-endian byte order
        L : 32-bit unsigned long
        20s : 20-byte string
        H : 16-bit unsigned short
        """
        pathEnd = entriesData.index(b"\x00", fieldsEnd)
        path = entriesData[fieldsEnd:pathEnd]
        entry = IndexEntry(*(fields + (path.decode(),)))
        entries.append(entry)
        entryLength = ((62 + len(path) + 8) // 8) * 8
        i += entryLength
    assert len(entries) == nEntries
    return entries


def add(paths):
    """
    Add the paths to the index
    """
    paths = [p.replace("\\", "/") for p in paths]
    indexEntries = readIndex()
    entries = [entry for entry in indexEntries if entry.path not in paths]
    for path in paths:
        hash = hashObject(readFile(path), "blob")
        stats = os.stat(path)
        flags = len(path.encode())
        assert flags < (1 << 12)
        entry = IndexEntry(
            int(stats.st_ctime),
            0,
            int(stats.st_mtime),
            0,
            stats.st_dev & 0xFFFFFFFF,  # truncating to 32-bits
            stats.st_ino & 0xFFFFFFFF,  # truncating to 32-bits
            stats.st_mode,
            stats.st_uid,
            stats.st_gid,
            stats.st_size,
            bytes.fromhex(hash),
            flags,
            path,
        )
        print(entry)
        entries.append(entry)
    entries.sort(key=operator.attrgetter("path"))
    writeIndex(entries)


def writeTree():
    """
    Write a tree object from index entries.
    """
    treeEntries = []
    for entry in readIndex():
        print(entry)
        assert "/" not in entry.path, "Can't write an other root directory"
        modeAndPath = f"{entry.mode:o} {entry.path}".encode()
        treeEntry = modeAndPath + b"\x00" + entry.sha1
        treeEntries.append(treeEntry)
    return hashObject(b"".join(treeEntries), "tree")

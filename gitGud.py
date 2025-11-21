import os
import hashlib
import zlib
import collections
import struct
import operator
import time
import sys
import stat
import difflib


def init(repository):
    """Initialize a new gitGud repository."""
    os.makedirs(repository, exist_ok=True)
    os.makedirs(os.path.join(repository, ".gitGud"))
    os.makedirs(os.path.join(repository, ".gitGud", "objects"))
    os.makedirs(os.path.join(repository, ".gitGud", "refs"))
    os.makedirs(os.path.join(repository, ".gitGud", "refs", "heads"))
    writeFile(os.path.join(repository, ".gitGud", "HEAD"), b"ref: refs/heads/master")
    print(f"Initialized empty gitGud repository in {repository}")


def readFile(path):
    """Reads the contents of a file. Encoded in bytes"""
    with open(path, "rb") as file:
        return file.read()


def writeFile(path, data):
    """Write data to a file. Encoded in bytes"""
    with open(path, "wb") as file:
        file.write(data)


def hashObject(data, objectType, write=True, gitFolder=".gitGud"):
    """
    Compute SHA-1 hash of the given data and optionally write it to the object database.
    Return SHA-1 object hash as hex string
    """
    header = f"{objectType} {len(data)}".encode()
    data = header + b"\x00" + data
    hash = hashlib.sha1(data).hexdigest()
    if write:
        path = os.path.join(gitFolder, "objects", hash[:2], hash[2:])
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            writeFile(path, zlib.compress(data))
    return hash


def findObject(hashBegin, gitFolder=".gitGud"):
    """
    Find an object from it's SHA-1 hash beginning and returns it's path.
    Raise ValueError if not found.
    """
    if len(hashBegin) < 2:
        raise ValueError("At least the first 2 characters should be provided.")
    objectDirectory = os.path.join(gitFolder, "objects", hashBegin[:2])
    objectName = hashBegin[2:]
    objects = []
    for object in os.listdir(objectDirectory):
        if object.startswith(objectName):
            objects.append(object)
    if len(objects) == 0:
        raise ValueError(f"Object not found")
    if len(objects) > 1:
        raise ValueError("Multiple objects found")
    return os.path.join(objectDirectory, objects[0])


def readObject(hashBegin, gitFolder=".gitGud"):
    """
    Finds then reads an object from it's SHA-1 hash and returns it's content as a tuple : (objectType, data).
    Raise ValueError if not found.
    """
    path = findObject(hashBegin, gitFolder=gitFolder)
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


def writeIndex(entries, gitFolder=".gitGud"):
    """
    Write a list of index entries as IndexEntries objects to the index.
    """
    encodedEntries = []
    for entry in entries:
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
    writeFile(os.path.join(gitFolder, "index"), data + hash)


def readIndex(gitFolder=".gitGud"):
    """
    Read the index and return a list of index entries as IndexEnties objects.
    """
    try:
        data = readFile(os.path.join(gitFolder, "index"))
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


def add(paths, gitFolder=".gitGud"):
    """
    Add the paths to the index
    """
    paths = [p.replace("\\", "/") for p in paths]
    indexEntries = readIndex(gitFolder=gitFolder)
    entries = [entry for entry in indexEntries if entry.path not in paths]
    for path in paths:
        hash = hashObject(readFile(path), "blob", gitFolder=gitFolder)
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
        entries.append(entry)
    entries.sort(key=operator.attrgetter("path"))
    writeIndex(entries, gitFolder=gitFolder)


def writeTree(gitFolder=".gitGud"):
    """
    Write a tree object from index entries.
    """
    treeEntries = []
    for entry in readIndex(gitFolder=gitFolder):
        assert "/" not in entry.path, "Can't write an other root directory"
        modeAndPath = f"{entry.mode:o} {entry.path}".encode()
        treeEntry = modeAndPath + b"\x00" + entry.sha1
        treeEntries.append(treeEntry)
    return hashObject(b"".join(treeEntries), "tree", gitFolder=gitFolder)


def getLocalMasterHash(gitFolder=".gitGud"):
    """
    Get the current commit hash of local master branch.
    """
    path = os.path.join(gitFolder, "refs", "heads", "master")
    try:
        return readFile(path).decode().strip()
    except FileNotFoundError:
        return None


def commit(message, author, gitFolder=".gitGud"):
    """
    Commit the current index to master with the message.
    Return the hash of the commit.
    """
    tree = writeTree(gitFolder=gitFolder)
    parent = getLocalMasterHash(gitFolder=gitFolder)
    if author is None:
        author = f"{os.environ['GIT_AUTHOR_NAME']} <{os.environ['GIT_AUTHOR_EMAIL']}>"
    timestamp = int(time.mktime(time.localtime()))
    utc = -time.timezone
    authorTime = f"{timestamp} {'+' if utc > 0 else '-'}{abs(utc) // 3600:02}{(abs(utc) // 60) % 60:02}"
    lines = ["tree " + tree]
    if parent:
        lines.append("parent " + parent)
    lines.append(f"author {author} {authorTime}")
    lines.append(f"committer {author} {authorTime}")
    lines.append("")
    lines.append(message)
    lines.append("")
    data = "\n".join(lines).encode()
    hash = hashObject(data, "commit", gitFolder=gitFolder)
    newMasterPath = os.path.join(gitFolder, "refs", "heads", "master")
    writeFile(newMasterPath, (hash + "\n").encode())
    print(f"commited to master: {hash :.7}")
    return hash


def catFile(mode, hashBegin, gitFolder=".gitGud"):
    """
    Prints contents or info about an object with an hash begining.
    If mode is 'commit', 'tree', or 'blob', print the raw data bytes of the object.
    If mode is 'size', print the size of the object.
    If mode is 'type', print the type of the object.
    If mode is 'pretty', print a prettified version of the object.
    """
    objectType, data = readObject(hashBegin, gitFolder=gitFolder)
    if mode in ["commit", "tree", "blob"]:
        if mode != objectType:
            raise ValueError(f"Wrong object type. Expected {objectType}, got {mode}")
        sys.stdout.buffer.write(data)
    elif mode == "size":
        print(len(data))
    elif mode == "type":
        print(objectType)
    elif mode == "pretty":
        if objectType in ["commit", "blob"]:
            sys.stdout.buffer.write(data)
        elif objectType == "tree":
            for mode, path, hash in readTree(data=data, gitFolder=gitFolder):
                type = "tree" if stat.S_ISDIR(mode) else "blob"
                print(f"{mode:06o} {type} {hash}\t{path}")
        else:
            assert False, "unhandled object type {!r}".format(objectType)
    else:
        raise ValueError("unexpected mode {!r}".format(mode))


def readTree(hash=None, data=None, gitFolder=".gitGud"):
    if hash is not None:
        objectType, data = readObject(hash, gitFolder=gitFolder)
        assert objectType == "tree"
    elif data is None:
        raise ValueError("must specify hash or data")
    entries = []
    i = 0
    atEnd = False
    while not atEnd:
        end = data.find(b"\x00", i)
        if end == -1:
            atEnd = True
            break
        mode, path = data[i:end].decode().split()
        mode = int(mode, 8)
        hash = data[end + 1 : end + 21]
        entries.append((mode, path, hash.hex()))
        i = end + 21
    return entries


def lsFiles(details=False, gitFolder=".gitGud"):
    """Print a list of the files in index (including mode, SHA-1, and stage number if "details" is True)."""
    for entry in readIndex(gitFolder=gitFolder):
        if details:
            flags = (entry.flags >> 12) & 3
            print(f"{entry.mode:6o} {entry.sha1.hex()} {flags}\t{entry.path}")
        else:
            print(entry.path)


def getStatus(gitFolder=".gitGud"):
    paths = set()
    for root, directories, files in os.walk("."):
        directories[:] = [
            directory for directory in directories if directory != ".gitGud"
        ]
        for file in files:
            path = os.path.join(root, file)
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            paths.add(path)
    entriesByPath = {entry.path: entry for entry in readIndex(gitFolder=gitFolder)}
    enrtyPaths = set(entriesByPath)
    changed = {
        path
        for path in (paths & enrtyPaths)
        if hashObject(readFile(path), "blob", write=False, gitFolder=gitFolder)
        != entriesByPath[path].sha1.hex()
    }
    new = paths - enrtyPaths
    deleted = enrtyPaths - paths
    return (sorted(changed), sorted(new), sorted(deleted))


def status(gitFolder=".gitGud"):
    changed, new, deleted = getStatus(gitFolder=gitFolder)
    if changed:
        print("changed files:")
        for path in changed:
            print("    " + path)
    if new:
        print("new files:")
        for path in new:
            print("    " + path)
    if deleted:
        print("deleted files:")
        for path in deleted:
            print("    " + path)


def diff(gitFolder=".gitGud"):
    changed, _, _ = getStatus(gitFolder=gitFolder)
    entriesByPath = {entry.path: entry for entry in readIndex(gitFolder=gitFolder)}
    for i, path in enumerate(changed):
        hash = entriesByPath[path].sha1.hex()
        objectType, data = readObject(hash, gitFolder=gitFolder)
        assert objectType == "blob"
        indexLines = data.decode().splitlines()
        workingLines = readFile(path).decode().splitlines()
        diffLines = difflib.unified_diff(
            indexLines,
            workingLines,
            f"{path} (index)",
            f"{path} (working copy)",
            lineterm="",
        )
        for line in diffLines:
            print(line)
        if i < len(changed) - 1:
            print("-" * 50)

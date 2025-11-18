import os
import hashlib
import zlib


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
    objectContent = objectContent.split(b"\x00")
    header = objectContent[0]
    objectType, size = header.decode().split(" ")
    size = int(size)
    data = objectContent[1]
    assert (
        len(data) == size
    ), f"Data is the wrong size. Expected {size}, got {len(data)}"
    return (objectType, data)

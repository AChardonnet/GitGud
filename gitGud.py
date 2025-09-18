import os
import hashlib


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
            writeFile(path, data)
    return hash

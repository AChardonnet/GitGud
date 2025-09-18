import os


def init(repository):
    """Initialize a new gitGud repository."""
    os.makedirs(repository, exist_ok=True)
    os.makedirs(os.path.join(repository, ".gitGud"))
    os.makedirs(os.path.join(repository, ".gitGud", "objects"))
    print(f"Initialized empty gitGud repository in {repository}")

import tempfile
from git import Repo

def clone_repo(url):
    path = tempfile.mkdtemp()
    Repo.clone_from(url, path)
    return path

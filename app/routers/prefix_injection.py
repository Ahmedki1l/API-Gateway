import os
import sys

from dotenv import dotenv_values

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_ENV = {**dotenv_values(os.path.join(_REPO_ROOT, ".env")), **os.environ}

PREFIX = _ENV.get("PREFIX")

def get_prefix():
    return ('/' + PREFIX + '/') if PREFIX else ''
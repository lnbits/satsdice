from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer

db = Database("ext_satsdice")

satsdice_ext: APIRouter = APIRouter(prefix="/satsdice", tags=["satsdice"])

satsdice_static_files = [
    {
        "path": "/satsdice/static",
        "name": "satsdice_static",
    }
]


def satsdice_renderer():
    return template_renderer(["satsdice/templates"])


from .lnurl import *  # noqa: F401,F403
from .views import *  # noqa: F401,F403
from .views_api import *  # noqa: F401,F403

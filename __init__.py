from fastapi import APIRouter

from .crud import db
from .views import satsdice_generic_router
from .views_api import satsdice_api_router
from .views_lnurl import satsdice_lnurl_router

satsdice_ext: APIRouter = APIRouter(prefix="/satsdice", tags=["satsdice"])
satsdice_ext.include_router(satsdice_generic_router)
satsdice_ext.include_router(satsdice_api_router)
satsdice_ext.include_router(satsdice_lnurl_router)

satsdice_static_files = [
    {
        "path": "/satsdice/static",
        "name": "satsdice_static",
    }
]

__all__ = ["db", "satsdice_ext", "satsdice_static_files"]

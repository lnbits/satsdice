import asyncio
from fastapi import APIRouter

from .crud import db
from .views import satsdice_generic_router
from .views_api import satsdice_api_router
from .views_lnurl import satsdice_lnurl_router
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

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

from .tasks import wait_for_paid_invoices

scheduled_tasks: list[asyncio.Task] = []


def satsdice_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def satsdice_start():
    task = create_permanent_unique_task("ext_satsdice", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = ["db", "satsdice_ext", "satsdice_static_files"]

import httpx
from lnbits.core.views.api import api_lnurlscan
from starlette.exceptions import HTTPException
from http import HTTPStatus
from loguru import logger

async def get_pr(ln_address, amount):
    data = await api_lnurlscan(ln_address)
    if data.get("status") == "ERROR":
        return
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=f"{data['callback']}?amount={amount* 1000}")
            if response.status_code != 200:
                return
            return response.json()["pr"]
    except Exception as exc:
        return None
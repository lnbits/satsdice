import random
from http import HTTPStatus
from io import BytesIO

import pyqrcode
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from lnbits.core.crud import get_standalone_payment
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse

from .crud import (
    create_satsdice_withdraw,
    get_satsdice_pay,
    get_satsdice_payment,
    get_satsdice_withdraw,
    update_satsdice_payment,
    get_coinflip,
    get_coinflip_settings_page,
)
from .models import CreateSatsDiceWithdraw

templates = Jinja2Templates(directory="templates")
satsdice_generic_router: APIRouter = APIRouter()


def satsdice_renderer():
    return template_renderer(["satsdice/templates"])


@satsdice_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return satsdice_renderer().TemplateResponse(
        "satsdice/index.html", {"request": request, "user": user.dict()}
    )


@satsdice_generic_router.get("/{link_id}", response_class=HTMLResponse)
async def display(request: Request, link_id: str):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="satsdice link does not exist."
        )

    return satsdice_renderer().TemplateResponse(
        "satsdice/display.html",
        {
            "request": request,
            "chance": link.chance,
            "multiplier": link.multiplier,
            "lnurl": link.lnurl(request),
            "unique": True,
        },
    )


@satsdice_generic_router.get(
    "/win/{link_id}/{payment_hash}",
    name="satsdice.displaywin",
    response_class=HTMLResponse,
)
async def displaywin(request: Request, link_id: str, payment_hash: str):
    satsdicelink = await get_satsdice_pay(link_id)
    if not satsdicelink:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="satsdice link does not exist."
        )
    withdraw_link = await get_satsdice_withdraw(payment_hash)
    payment = await get_satsdice_payment(payment_hash)
    if not payment or payment.lost:
        return satsdice_renderer().TemplateResponse(
            "satsdice/error.html",
            {"request": request, "link": satsdicelink.id, "paid": False, "lost": True},
        )
    if withdraw_link:
        return satsdice_renderer().TemplateResponse(
            "satsdice/displaywin.html",
            {
                "request": request,
                "value": withdraw_link.value,
                "chance": satsdicelink.chance,
                "multiplier": satsdicelink.multiplier,
                "lnurl": withdraw_link.lnurl(request),
                "paid": False,
                "lost": False,
            },
        )
    rand = random.randint(0, 100)
    chance = satsdicelink.chance
    core_payment = await get_standalone_payment(payment_hash, incoming=True)
    status = (await core_payment.check_status()).success if core_payment else False
    if not rand < chance or not status:
        await update_satsdice_payment(payment_hash, lost=1)
        return satsdice_renderer().TemplateResponse(
            "satsdice/error.html",
            {"request": request, "link": satsdicelink.id, "paid": False, "lost": True},
        )
    await update_satsdice_payment(payment_hash, paid=1)
    paylink = await get_satsdice_payment(payment_hash)
    if not paylink:
        return satsdice_renderer().TemplateResponse(
            "satsdice/error.html",
            {"request": request, "link": satsdicelink.id, "paid": False, "lost": True},
        )

    data = CreateSatsDiceWithdraw(
        satsdice_pay=satsdicelink.id,
        value=int(paylink.value * satsdicelink.multiplier),
        payment_hash=payment_hash,
        used=0,
    )

    withdraw_link = await create_satsdice_withdraw(data)
    return satsdice_renderer().TemplateResponse(
        "satsdice/displaywin.html",
        {
            "request": request,
            "value": withdraw_link.value,
            "chance": satsdicelink.chance,
            "multiplier": satsdicelink.multiplier,
            "lnurl": withdraw_link.lnurl(request),
            "paid": False,
            "lost": False,
        },
    )


@satsdice_generic_router.get("/img/{link_id}", response_class=HTMLResponse)
async def img(link_id):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="satsdice link does not exist."
        )

    qr = pyqrcode.create(link.lnurl)
    stream = BytesIO()
    qr.svg(stream, scale=3)
    return (
        stream.getvalue(),
        200,
        {
            "Content-Type": "image/svg+xml",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@satsdice_generic_router.get("/coinflip/{coinflip_page_id}", response_class=HTMLResponse)
async def display_coinflip(request: Request, coinflip_page_id: str):
    coinflip = await get_coinflip_settings_page(coinflip_page_id)
    if not coinflip:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Coinflip game does not exist."
        )
    return satsdice_renderer().TemplateResponse(
        "satsdice/coinflip.html",
        {
            "request": request,
            "coinflipHaircut": coinflip.haircut,
            "coinflipMaxPlayers": coinflip.max_players,
            "coinflipMaxBet": coinflip.max_bet,
        },
    )

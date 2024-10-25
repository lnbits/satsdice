import random
from http import HTTPStatus
from io import BytesIO

import pyqrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.crud import get_payment
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from loguru import logger

from .crud import (
    create_satsdice_withdraw,
    get_coinflip,
    get_coinflip_settings,
    get_satsdice_pay,
    get_satsdice_payment,
    get_satsdice_withdraw,
    update_satsdice_payment,
)
from .models import CreateSatsDiceWithdraw

satsdice_generic_router: APIRouter = APIRouter()


def satsdice_renderer():
    return template_renderer(["satsdice/templates"])


@satsdice_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return satsdice_renderer().TemplateResponse(
        "satsdice/index.html", {"request": request, "user": user.json()}
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
    core_payment = await get_payment(payment_hash)
    if not rand < chance or not core_payment.success:
        payment.lost = True
        await update_satsdice_payment(payment)
        return satsdice_renderer().TemplateResponse(
            "satsdice/error.html",
            {"request": request, "link": satsdicelink.id, "paid": False, "lost": True},
        )
    payment.paid = True
    await update_satsdice_payment(payment)

    data = CreateSatsDiceWithdraw(
        satsdice_pay=satsdicelink.id,
        value=int(payment.value * satsdicelink.multiplier),
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


@satsdice_generic_router.get(
    "/coinflip/{coinflip_settings_id}/{game}", response_class=HTMLResponse
)
async def display_coinflip(request: Request, coinflip_settings_id: str, game: str):
    coinflip_settings = await get_coinflip_settings(coinflip_settings_id)
    logger.debug(coinflip_settings)
    if not coinflip_settings:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Coinflip game does not exist."
        )
    winner = None
    if game:
        coinflip = await get_coinflip(game)
        if not coinflip:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Coinflip game does not exist."
            )
        if coinflip.completed:
            winner = coinflip.players
    return satsdice_renderer().TemplateResponse(
        "satsdice/coinflip.html",
        {
            "request": request,
            "coinflipHaircut": coinflip_settings.haircut,
            "coinflipMaxPlayers": coinflip_settings.max_players,
            "coinflipMaxBet": coinflip_settings.max_bet,
            "coinflipPageId": coinflip_settings.id,
            "coinflipGameId": game,
            "coinflipWinner": winner,
        },
    )

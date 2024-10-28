from http import HTTPStatus

from fastapi import APIRouter, Depends, Query, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import require_admin_key, require_invoice_key
from lnurl.exceptions import InvalidUrl as LnurlInvalidUrl
from loguru import logger
from starlette.exceptions import HTTPException

from .crud import (
    create_coinflip,
    create_coinflip_settings,
    create_satsdice_pay,
    delete_satsdice_pay,
    get_coinflip,
    get_coinflip_settings,
    get_coinflip_settings_wallet,
    get_satsdice_pay,
    get_satsdice_pays,
    get_withdraw_hash_checkw,
    update_coinflip_settings,
    update_satsdice_pay,
)
from .helpers import get_pr
from .models import (
    Coinflip,
    CoinflipSettings,
    CreateCoinflipSettings,
    CreateSatsDiceLink,
    JoinCoinflipGame,
)

satsdice_api_router = APIRouter()


@satsdice_api_router.get("/api/v1/links")
async def api_links(
    request: Request,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        if user:
            wallet_ids = user.wallet_ids

    try:
        links = await get_satsdice_pays(wallet_ids)

        return [{**link.dict(), **{"lnurl": link.lnurl(request)}} for link in links]
    except LnurlInvalidUrl as exc:
        raise HTTPException(
            status_code=HTTPStatus.UPGRADE_REQUIRED,
            detail="""
            LNURLs need to be delivered over a
            publically accessible `https` domain or Tor.
            """,
        ) from exc


@satsdice_api_router.get("/api/v1/links/{link_id}")
async def api_link_retrieve(
    link_id: str, wallet: WalletTypeInfo = Depends(require_invoice_key)
):
    link = await get_satsdice_pay(link_id)

    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )

    if link.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your pay link."
        )

    return {**link.dict(), **{"lnurl": link.lnurl}}


@satsdice_api_router.post("/api/v1/links", status_code=HTTPStatus.CREATED)
async def api_create_satsdice_link(
    data: CreateSatsDiceLink,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    if data.min_bet > data.max_bet:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Bad request")

    if data.wallet and data.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Come on, seriously, this isn't your satsdice!",
        )

    data.wallet = data.wallet or wallet.wallet.id
    link = await create_satsdice_pay(data=data)
    return {**link.dict(), **{"lnurl": link.lnurl}}


@satsdice_api_router.put("/api/v1/links/{link_id}", status_code=HTTPStatus.OK)
async def api_update_satsdice_link(
    link_id: str,
    data: CreateSatsDiceLink,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Satsdice does not exist"
        )

    if link.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Come on, seriously, this isn't your satsdice!",
        )

    if data.min_bet > data.max_bet:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Bad request")

    data.wallet = data.wallet or wallet.wallet.id
    for k, v in data.dict().items():
        setattr(link, k, v)
    await update_satsdice_pay(link)
    return {**link.dict(), **{"lnurl": link.lnurl}}


@satsdice_api_router.delete("/api/v1/links/{link_id}")
async def api_link_delete(
    link_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )

    if link.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your pay link."
        )

    await delete_satsdice_pay(link_id)


@satsdice_api_router.get(
    "/api/v1/withdraws/{the_hash}/{lnurl_id}",
    dependencies=[Depends(require_invoice_key)],
)
async def api_withdraw_hash_retrieve(
    the_hash: str,
    lnurl_id: str,
):
    hash_check = await get_withdraw_hash_checkw(the_hash, lnurl_id)
    return hash_check


################
### Coinflip ###
################


@satsdice_api_router.get("/api/v1/coinflip/settings", status_code=HTTPStatus.OK)
async def api_get_coinflip_settings(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(key_info.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="unable to chnage settings"
        )
    settings = await get_coinflip_settings(user.id)
    if not settings:
        settings = await create_coinflip_settings(
            key_info.wallet.id,
            CreateCoinflipSettings(),
        )
    return settings


@satsdice_api_router.post("/api/v1/coinflip/settings", status_code=HTTPStatus.CREATED)
async def api_create_coinflip_settings(
    coinflip_settings: CreateCoinflipSettings,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> CoinflipSettings:
    user = await get_user(key_info.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="unable to change settings"
        )
    return await create_coinflip_settings(key_info.wallet.id, user.id, coinflip_settings)


@satsdice_api_router.put(
    "/api/v1/coinflip/settings/{settings_id}", status_code=HTTPStatus.CREATED
)
async def api_update_coinflip_settings(
    settings_id: str,
    coinflip_settings: CreateCoinflipSettings,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> CoinflipSettings:
    user = await get_user(key_info.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="unable to change settings"
        )
    _settings = await get_coinflip_settings(settings_id)
    if not _settings:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Settings not found"
        )

    for k, v in coinflip_settings.dict().items():
        setattr(_settings, k, v)

    await update_coinflip_settings(_settings)
    return _settings


@satsdice_api_router.post("/api/v1/coinflip", status_code=HTTPStatus.OK)
async def api_create_coinflip(
    data: Coinflip, key_info: WalletTypeInfo = Depends(require_invoice_key)
):
    coinflip_settings = await get_coinflip_settings_wallet(key_info.wallet.id)
    if not coinflip_settings:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Couldnt load settings"
        )
    if coinflip_settings.max_bet < data.buy_in:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Buy in to high")
    if coinflip_settings.max_players < data.number_of_players:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Number of plaers is too high"
        )
    if coinflip_settings.id != data.settings_id:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Wrong user")
    logger.debug("coinflip_settings")
    coinflip = await create_coinflip(data)
    return coinflip.id


@satsdice_api_router.post("/api/v1/coinflip/join/{game_id}", status_code=HTTPStatus.OK)
async def api_join_coinflip(data: JoinCoinflipGame):
    coinflip_settings = await get_coinflip_settings(data.settings_id)
    coinflip_game = await get_coinflip(data.game_id)
    if not coinflip_game:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="No game found")
    if not coinflip_settings:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Coinflip settings missing"
        )
    if coinflip_game.completed:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="This game is already full"
        )
    if not coinflip_settings.enabled:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="This game is disabled"
        )
    pay_req = await get_pr(data.ln_address, coinflip_game.buy_in)
    if not pay_req:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="lnaddress check failed"
        )
    payment = await create_invoice(
        wallet_id=coinflip_settings.wallet_id,
        amount=coinflip_game.buy_in,
        memo=f"Coinflip {coinflip_game.name} for {data.ln_address}",
        extra={
            "tag": "satsdice_coinflip",
            "ln_address": data.ln_address,
            "game_id": data.game_id,
        },
    )
    return {"payment_hash": payment.payment_hash, "payment_request": payment.bolt11}


@satsdice_api_router.get("/api/v1/coinflip/coinflip/{coinflip_id}", status_code=HTTPStatus.OK)
async def api_get_coinflip(coinflip_id: str):
    return await get_coinflip(coinflip_id)

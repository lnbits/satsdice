from http import HTTPStatus

from fastapi import APIRouter, Depends, Query, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import get_key_type, require_admin_key
from lnurl.exceptions import InvalidUrl as LnurlInvalidUrl
from starlette.exceptions import HTTPException
from loguru import logger

from .crud import (
    create_satsdice_pay,
    delete_satsdice_pay,
    get_satsdice_pay,
    get_satsdice_pays,
    get_withdraw_hash_checkw,
    update_satsdice_pay,
    create_coinflip,
    get_coinflip_settings, 
    set_coinflip_settings,
)
from .models import (
    Coinflip,
    CoinflipSettings,
    CreateSatsDiceLink,
)

satsdice_api_router = APIRouter()


@satsdice_api_router.get("/api/v1/links")
async def api_links(
    request: Request,
    wallet: WalletTypeInfo = Depends(get_key_type),
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
    link_id: str, wallet: WalletTypeInfo = Depends(get_key_type)
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

    link = await create_satsdice_pay(wallet_id=wallet.wallet.id, data=data)
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

    data.wallet = wallet.wallet.id
    updated_link = await update_satsdice_pay(link_id, **data.dict())
    return {**updated_link.dict(), **{"lnurl": updated_link.lnurl}}


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

    return "", HTTPStatus.NO_CONTENT


@satsdice_api_router.get(
    "/api/v1/withdraws/{the_hash}/{lnurl_id}", dependencies=[Depends(get_key_type)]
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
async def api_get_coinflip_settings(wallet: WalletTypeInfo = Depends(get_key_type)):
    user = await get_user(wallet.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="unable to chnage settings"
        )
    return await get_coinflip_settings(user.id)

@satsdice_api_router.post("/api/v1/coinflip/settings", status_code=HTTPStatus.CREATED)
async def api_set_coinflip_settings(
    settings: CoinflipSettings, 
    wallet: WalletTypeInfo = Depends(require_admin_key)):

    user = await get_user(wallet.wallet.user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="unable to chnage settings"
        )
    settings.id = user.id
    settings = await set_coinflip_settings(settings)
    return settings

@satsdice_api_router.post("/api/v1/coinflip", status_code=HTTPStatus.OK)
async def api_create_coinflip(
    data: Coinflip):
    return await create_coinflip(data)

@satsdice_api_router.get("/api/v1/coinflip/{coinflip_id}", status_code=HTTPStatus.OK)
async def api_get_coinflip(coinflip_id: str):
    return await get_coinflip(coinflip_id)
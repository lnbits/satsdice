from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import require_admin_key, require_invoice_key

from .crud import (
    create_satsdice_pay,
    delete_satsdice_pay,
    get_satsdice_pay,
    get_satsdice_pays,
    get_withdraw_hash_checkw,
    update_satsdice_pay,
)
from .models import CreateSatsDiceLink, SatsdiceLink

satsdice_api_router = APIRouter()


@satsdice_api_router.get("/api/v1/links")
async def api_links(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
) -> list[SatsdiceLink]:
    wallet_ids = [key_info.wallet.id]
    if all_wallets:
        user = await get_user(key_info.wallet.user)
        if user:
            wallet_ids = user.wallet_ids
    return await get_satsdice_pays(wallet_ids)


@satsdice_api_router.get("/api/v1/links/{link_id}")
async def api_link_retrieve(
    link_id: str, wallet: WalletTypeInfo = Depends(require_invoice_key)
) -> SatsdiceLink:
    link = await get_satsdice_pay(link_id)

    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )

    if link.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your pay link."
        )

    return link


@satsdice_api_router.post("/api/v1/links", status_code=HTTPStatus.CREATED)
async def api_create_satsdice_link(
    data: CreateSatsDiceLink,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> SatsdiceLink:
    if data.min_bet > data.max_bet:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Bad request")

    if data.wallet and data.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Come on, seriously, this isn't your satsdice!",
        )

    data.wallet = data.wallet or wallet.wallet.id
    link = await create_satsdice_pay(data=data)
    return link


@satsdice_api_router.put("/api/v1/links/{link_id}", status_code=HTTPStatus.OK)
async def api_update_satsdice_link(
    link_id: str,
    data: CreateSatsDiceLink,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> SatsdiceLink:
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
    link = await update_satsdice_pay(link)
    return link


@satsdice_api_router.delete("/api/v1/links/{link_id}")
async def api_link_delete(
    link_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> None:
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

import math
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query, Request
from lnbits.core.services import (
    create_invoice,
    pay_invoice,
)

from .crud import (
    create_satsdice_payment,
    get_satsdice_pay,
    get_satsdice_withdraw_by_hash,
    update_satsdice_withdraw,
)
from .models import CreateSatsDicePayment

satsdice_lnurl_router = APIRouter()


@satsdice_lnurl_router.get(
    "/api/v1/lnurlp/{link_id}",
    name="satsdice.lnurlp_response",
)
async def api_lnurlp_response(req: Request, link_id: str):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNURL-pay not found."
        )
    return {
        "tag": "payRequest",
        "callback": str(req.url_for("satsdice.api_lnurlp_callback", link_id=link.id)),
        "metadata": link.lnurlpay_metadata,
        "minSendable": math.ceil(link.min_bet * 1) * 1000,
        "maxSendable": round(link.max_bet * 1) * 1000,
    }


@satsdice_lnurl_router.get(
    "/api/v1/lnurlp/cb/{link_id}",
    name="satsdice.api_lnurlp_callback",
)
async def api_lnurlp_callback(req: Request, link_id: str, amount: str = Query(None)):
    link = await get_satsdice_pay(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNURL-pay not found."
        )

    min_bet = link.min_bet * 1000
    max_bet = link.max_bet * 1000

    amount_received = int(amount or 0)
    if amount_received < min_bet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"Amount {amount_received} is smaller than minimum {min_bet}.",
        )
    elif amount_received > max_bet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"Amount {amount_received} is greater than maximum {max_bet}.",
        )

    payment = await create_invoice(
        wallet_id=link.wallet,
        amount=int(amount_received / 1000),
        memo="Satsdice bet",
        unhashed_description=link.lnurlpay_metadata.encode(),
        extra={"tag": "satsdice", "link": link.id, "comment": "comment"},
    )

    success_action = link.success_action(payment_hash=payment.payment_hash, req=req)

    data = CreateSatsDicePayment(
        satsdice_pay=link.id,
        value=int(amount_received / 1000),
        payment_hash=payment.payment_hash,
    )

    await create_satsdice_payment(data)

    return {
        "pr": payment.bolt11,
        "successAction": success_action,
        "routes": [],
    }


@satsdice_lnurl_router.get(
    "/api/v1/lnurlw/{unique_hash}",
    name="satsdice.lnurlw_response",
)
async def api_lnurlw_response(req: Request, unique_hash: str):
    link = await get_satsdice_withdraw_by_hash(unique_hash)

    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNURL-satsdice not found."
        )
    if link.used:
        raise HTTPException(status_code=HTTPStatus.OK, detail="satsdice is spent.")
    url = str(req.url_for("satsdice.api_lnurlw_callback", unique_hash=link.unique_hash))
    return {
        "tag": "withdrawRequest",
        "callback": url,
        "k1": link.k1,
        "minWithdrawable": link.value * 1000,
        "maxWithdrawable": link.value * 1000,
        "defaultDescription": "Satsdice winnings!",
    }


@satsdice_lnurl_router.get(
    "/api/v1/lnurlw/cb/{unique_hash}",
    status_code=HTTPStatus.OK,
    name="satsdice.api_lnurlw_callback",
)
async def api_lnurlw_callback(
    unique_hash: str,
    pr: str = Query(None),
):

    link = await get_satsdice_withdraw_by_hash(unique_hash)
    if not link:
        return {"status": "ERROR", "reason": "no withdraw"}
    if link.used:
        return {"status": "ERROR", "reason": "spent"}
    paylink = await get_satsdice_pay(link.satsdice_pay)

    if not paylink:
        return {"status": "ERROR", "reason": "no paylink found"}

    link.used = True
    await update_satsdice_withdraw(link)

    try:
        await pay_invoice(
            wallet_id=paylink.wallet,
            payment_request=pr,
            max_sat=link.value,
        )
    except Exception as exc:
        # If the payment failed, we need to reset the withdraw to unused
        link.used = False
        await update_satsdice_withdraw(link)
        return {"status": "ERROR", "reason": str(exc)}

    return {"status": "OK"}

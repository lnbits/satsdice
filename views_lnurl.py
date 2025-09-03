import json
import math
from http import HTTPStatus

from fastapi import APIRouter, Query, Request
from lnbits.core.services import (
    create_invoice,
    pay_invoice,
)
from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayMetadata,
    LnurlPayResponse,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
    Max144Str,
    MilliSatoshi,
    UrlAction,
)
from pydantic import parse_obj_as

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
async def api_lnurlp_response(
    req: Request, link_id: str
) -> LnurlPayResponse | LnurlErrorResponse:
    link = await get_satsdice_pay(link_id)
    if not link:
        return LnurlErrorResponse(reason="LNURL-pay not found.")
    callback_url = str(req.url_for("satsdice.api_lnurlp_callback", link_id=link.id))
    _plain = [
        "text/plain",
        f"{link.title} (Chance: {link.chance}%, Multiplier: {link.multiplier})",
    ]
    return LnurlPayResponse(
        callback=parse_obj_as(CallbackUrl, callback_url),
        metadata=LnurlPayMetadata(json.dumps([_plain])),
        minSendable=MilliSatoshi(math.ceil(link.min_bet * 1) * 1000),
        maxSendable=MilliSatoshi(round(link.max_bet * 1) * 1000),
    )


@satsdice_lnurl_router.get(
    "/api/v1/lnurlp/cb/{link_id}",
    name="satsdice.api_lnurlp_callback",
)
async def api_lnurlp_callback(
    req: Request, link_id: str, amount: str = Query(None)
) -> LnurlErrorResponse | LnurlPayActionResponse:
    link = await get_satsdice_pay(link_id)
    if not link:
        return LnurlErrorResponse(reason="LNURL-pay not found.")

    min_bet = link.min_bet * 1000
    max_bet = link.max_bet * 1000

    amount_received = int(amount or 0)
    if amount_received < min_bet:
        return LnurlErrorResponse(
            reason=f"Amount {amount_received} is smaller than minimum {min_bet}."
        )
    elif amount_received > max_bet:
        return LnurlErrorResponse(
            reason=f"Amount {amount_received} is greater than maximum {max_bet}."
        )

    _plain = [
        "text/plain",
        f"{link.title} (Chance: {link.chance}%, Multiplier: {link.multiplier})",
    ]
    _metadata = LnurlPayMetadata(json.dumps([_plain]))
    payment = await create_invoice(
        wallet_id=link.wallet,
        amount=int(amount_received / 1000),
        memo="Satsdice bet",
        unhashed_description=_metadata.encode(),
        extra={"tag": "satsdice", "link": link.id, "comment": "comment"},
    )

    data = CreateSatsDicePayment(
        satsdice_pay=link.id,
        value=int(amount_received / 1000),
        payment_hash=payment.payment_hash,
    )

    await create_satsdice_payment(data)

    url = str(
        req.url_for(
            "satsdice.displaywin", link_id=link.id, payment_hash=payment.payment_hash
        )
    )
    msg = parse_obj_as(Max144Str, "Check the attached link")
    success_action = UrlAction(url=parse_obj_as(CallbackUrl, url), description=msg)
    return LnurlPayActionResponse(
        pr=parse_obj_as(LightningInvoice, payment.bolt11),
        successAction=success_action,
        disposable=link.disposable,
    )


@satsdice_lnurl_router.get(
    "/api/v1/lnurlw/{unique_hash}",
    name="satsdice.lnurlw_response",
)
async def api_lnurlw_response(
    req: Request, unique_hash: str
) -> LnurlWithdrawResponse | LnurlErrorResponse:
    link = await get_satsdice_withdraw_by_hash(unique_hash)

    if not link:
        return LnurlErrorResponse(reason="LNURL-satsdice not found.")

    if link.used:
        return LnurlErrorResponse(reason="Withdraw already used.")

    url = str(req.url_for("satsdice.api_lnurlw_callback", unique_hash=link.unique_hash))
    return LnurlWithdrawResponse(
        callback=parse_obj_as(CallbackUrl, url),
        k1=link.k1,
        minWithdrawable=MilliSatoshi(link.value * 1000),
        maxWithdrawable=MilliSatoshi(link.value * 1000),
        defaultDescription="Satsdice winnings!",
    )


@satsdice_lnurl_router.get(
    "/api/v1/lnurlw/cb/{unique_hash}",
    status_code=HTTPStatus.OK,
    name="satsdice.api_lnurlw_callback",
)
async def api_lnurlw_callback(
    unique_hash: str,
    pr: str = Query(None),
) -> LnurlErrorResponse | LnurlSuccessResponse:
    link = await get_satsdice_withdraw_by_hash(unique_hash)
    if not link:
        return LnurlErrorResponse(reason="Withdraw not found.")
    if link.used:
        return LnurlErrorResponse(reason="Withdraw already used.")
    paylink = await get_satsdice_pay(link.satsdice_pay)

    if not paylink:
        return LnurlErrorResponse(reason="No paylink found.")

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
        return LnurlErrorResponse(reason=str(exc))

    return LnurlSuccessResponse()

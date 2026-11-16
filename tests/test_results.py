import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from lnbits.db import Database
from lnbits.settings import settings

from .. import crud, migrations, views, views_lnurl
from ..models import CreateSatsDiceLink, CreateSatsDicePayment, CreateSatsDiceWithdraw


@pytest_asyncio.fixture
async def link(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lnbits_data_folder", str(tmp_path))
    database = Database("ext_satsdice")
    monkeypatch.setattr(crud, "db", database)
    async with database.connect() as conn:
        for name in sorted(vars(migrations)):
            if name.startswith("m00"):
                await getattr(migrations, name)(conn)
    monkeypatch.setattr(views, "satsdice_renderer", Mock())
    yield await crud.create_satsdice_pay(
        CreateSatsDiceLink(
            wallet="wallet",
            title="Dice",
            base_url="https://example.com",
            min_bet=10,
            max_bet=100,
            multiplier=2,
            chance=45,
            haircut=1,
            disposable=True,
        )
    )
    await database.engine.dispose()


@pytest.fixture
def request_scope():
    return Request({"type": "http", "path": "/"})


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_withdraw", [False, True])
async def test_result_requires_matching_link(link, request_scope, existing_withdraw):
    await crud.create_satsdice_payment(
        CreateSatsDicePayment(
            satsdice_pay="other-link", value=100, payment_hash="payment"
        )
    )
    if existing_withdraw:
        await crud.create_satsdice_withdraw(
            CreateSatsDiceWithdraw(
                satsdice_pay="other-link", value=200, payment_hash="payment", used=0
            )
        )

    with pytest.raises(HTTPException) as error:
        await views.displaywin(request_scope, link.id, "payment")

    assert error.value.status_code == 404
    payment = await crud.get_satsdice_payment("payment")
    assert payment and not payment.paid and not payment.lost


@pytest.mark.asyncio
@pytest.mark.parametrize("roll,settled", [(0, True), (100, True), (0, False)])
async def test_concurrent_results_are_processed_once(
    link, request_scope, monkeypatch, roll, settled
):
    await crud.create_satsdice_payment(
        CreateSatsDicePayment(satsdice_pay=link.id, value=100, payment_hash="payment")
    )
    ready = asyncio.Event()
    remaining = 8

    async def get_payment(payment_hash):
        nonlocal remaining
        remaining -= 1
        if remaining == 0:
            ready.set()
        await ready.wait()
        return SimpleNamespace(success=settled)

    monkeypatch.setattr(views, "get_payment", get_payment)
    monkeypatch.setattr(views.random, "randint", lambda start, end: roll)
    results = await asyncio.gather(
        *(views.displaywin(request_scope, link.id, "payment") for _ in range(8)),
        return_exceptions=True,
    )
    conflicts = [result for result in results if isinstance(result, HTTPException)]
    assert len(conflicts) == 7
    assert all(result.status_code == 409 for result in conflicts)
    assert sum(isinstance(result, Exception) for result in results) == 7
    payment = await crud.get_satsdice_payment("payment")
    won = roll < link.chance and settled
    assert payment and payment.paid == won and payment.lost != won
    withdraw = await crud.get_satsdice_withdraw("payment")
    assert (withdraw is not None) == won
    if withdraw:
        assert withdraw.satsdice_pay == link.id and withdraw.value == 200

    # Refreshing a resolved result reuses the stored outcome.
    monkeypatch.setattr(views, "get_payment", AsyncMock(side_effect=AssertionError))
    await views.displaywin(request_scope, link.id, "payment")


@pytest.mark.asyncio
async def test_concurrent_withdrawals_pay_once(link, monkeypatch):
    withdraw = await crud.create_satsdice_withdraw(
        CreateSatsDiceWithdraw(
            satsdice_pay=link.id, value=200, payment_hash="payment", used=0
        )
    )
    pay_invoice = AsyncMock()
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay_invoice)

    results = await asyncio.gather(
        *(
            views_lnurl.api_lnurlw_callback(withdraw.unique_hash, f"invoice-{index}")
            for index in range(8)
        )
    )

    assert sum(result.ok for result in results) == 1
    pay_invoice.assert_awaited_once()
    assert pay_invoice.call_args.kwargs["wallet_id"] == link.wallet
    assert pay_invoice.call_args.kwargs["max_sat"] == withdraw.value
    repeated = await views_lnurl.api_lnurlw_callback(
        withdraw.unique_hash, "new-invoice"
    )
    assert not repeated.ok
    pay_invoice.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_withdrawal_can_retry(link, monkeypatch):
    withdraw = await crud.create_satsdice_withdraw(
        CreateSatsDiceWithdraw(
            satsdice_pay=link.id, value=200, payment_hash="payment", used=0
        )
    )
    pay_invoice = AsyncMock(side_effect=[ValueError("Invalid invoice"), None])
    monkeypatch.setattr(views_lnurl, "pay_invoice", pay_invoice)

    failed = await views_lnurl.api_lnurlw_callback(withdraw.unique_hash, "invalid")
    retried = await views_lnurl.api_lnurlw_callback(withdraw.unique_hash, "valid")

    assert not failed.ok and retried.ok
    stored = await crud.get_satsdice_withdraw("payment")
    assert stored and stored.used == 1

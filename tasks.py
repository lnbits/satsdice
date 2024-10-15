import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from lnbits.core.views.api import pay_invoice
from loguru import logger
from .crud import (
    get_coinflip,
    get_coinflip_settings_page,
    set_coinflip_settings,
    update_coinflip,
)
import random
from lnbits.core.views.api import api_lnurlscan
from lnbits.core.crud import get_wallet
import bolt11
import httpx


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") == "satsdice_coinflip":
        ln_address = payment.extra["ln_address"]
        game_id = payment.extra["game_id"]
        # fetch details
        coinflip = await get_coinflip(game_id)
        if not coinflip:
            return
        coinflip_settings = await get_coinflip_settings_page(coinflip.page_id)
        if not coinflip_settings:
            return
        # Check they are not trying to scam the system.
        if (payment.amount / 1000) != coinflip.buy_in:
            return
        # If the game is full set as completed and refund the player.
        if len(coinflip.players) > coinflip_settings.max_players:
            coinflip.completed = True
            await update_coinflip(coinflip)

            # Calculate the haircut amount
            haircut_amount = coinflip.buy_in * (coinflip_settings.haircut / 100)
            # Calculate the winnings minus haircut
            max_sat = int(coinflip.buy_in - haircut_amount)
            pr = await get_pr(ln_address, max_sat)
            if not pr:
                return
            await pay_invoice(
                wallet_id=coinflip_settings.wallet_id,
                payment_request=pr,
                max_sat=max_sat,
                description="Refund. Coinflip game was full.",
            )
            await websocket_updater(payment.payment_hash, "refund")
            return

        # Add the player to the game.
        coinflip.players = f"{coinflip.players},{ln_address}"
        await update_coinflip(coinflip)

        # if player is the last one, pay their ln_address the winnings and set as completed.
        if len(coinflip.players) == coinflip_settings.max_players:
            winner = random.choice(coinflip.players)
            coinflip.completed = True
            coinflip.players = winner
            await update_coinflip(coinflip)

            # Calculate the total amount of winnings
            total_amount = coinflip.buy_in * len(coinflip.players)
            # Calculate the haircut amount
            haircut_amount = total_amount * (coinflip_settings.haircut / 100)
            # Calculate the winnings minus haircut
            max_sat = int(total_amount - haircut_amount)
            pr = await get_pr(winner, max_sat)
            if not pr:
                return
            await pay_invoice(
                wallet_id=coinflip_settings.wallet_id,
                payment_request=pr,
                max_sat=max_sat,
                description="You flipping won the coinflip!",
            )
            await websocket_updater(payment.payment_hash, "won")
            return
        await websocket_updater(payment.payment_hash, "paid")
        return


async def get_pr(ln_address, amount):
    data = await api_lnurlscan(ln_address)
    if data.get("status") == "ERROR":
        return
    async with httpx.AsyncClient() as client:
        response = await client.get(url=f"{data['callback']}?amount={amount* 1000}")
        if response.status_code != 200:
            return
        return response.json()["pr"]

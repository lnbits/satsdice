import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from lnbits.core.views.api import pay_invoice

from .crud import get_coinflip, get_coinflip_settings_page, set_coinflip_settings, update_coinflip
import random

async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") == "satsdice_switch":
        ln_address = await payment.extra["ln_address"]
        game_id = await payment.extra["game_id"]

        # fetch details
        coinflip = await get_coinflip(game_id)
        coinflip_settings = get_coinflip_settings_page(coinflip.page_id)

        # Check they are not trying to scam the system.
        if payment['amount'] != coinflip.buy_in:
            return
        
        # If the game is full set as completed and refund the player.
        if len(coinflip.players) > coinflip_settings.max_players:
            coinflip_settings.completed = True
            await set_coinflip_settings(coinflip_settings)
            await pay_invoice(
                wallet_id=coinflip_settings.wallet_id,
                payment_request=ln_address,
                max_sat=coinflip.buy_in / 100 * (100 - coinflip_settings.haircut),
                description="Refund. Coinflip game was full.",
            )
            websocket_updater(
                payment["payment_hash"],
                "refund"
            )
            return
        
        # Add the player to the game.
        coinflip.players = f"{coinflip.players},{ln_address}"
        await update_coinflip(coinflip)

        # if player is the last one, pay their ln_address the winnings and set as completed.
        if len(coinflip.players) == coinflip_settings.max_players:
            coinflip_settings.completed = True
            await set_coinflip_settings(coinflip_settings)
            await pay_invoice(
                wallet_id=coinflip_settings.wallet_id,
                payment_request=random.choice(coinflip.players),
                max_sat=(coinflip.buy_in * len(coinflip.players)) / 100 * (100 - coinflip_settings.haircut),
                description="You won the coinflip.",
            )
            websocket_updater(
                payment["payment_hash"],
                "won"
            )
            return
        websocket_updater(
            payment["payment_hash"],
            "paid"
        )
        return
 

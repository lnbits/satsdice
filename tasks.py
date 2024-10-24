import asyncio
import random

from lnbits.core.models import Payment
from lnbits.core.services import pay_invoice, websocket_updater
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_coinflip,
    get_coinflip_settings,
    update_coinflip,
)
from .helpers import get_pr


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_satsdice")

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") == "satsdice_coinflip":
        ln_address = payment.extra["ln_address"]
        game_id = payment.extra["game_id"]
        # fetch details
        coinflip = await get_coinflip(game_id)
        if not coinflip or not coinflip.settings_id:
            return
        coinflip_settings = await get_coinflip_settings(coinflip.settings_id)
        if not coinflip_settings:
            return
        # Check they are not trying to scam the system.
        if (payment.amount / 1000) != coinflip.buy_in:
            return
        # If the game is full set as completed and refund the player.
        coinflip_players = coinflip.players.split(",")
        if len(coinflip_players) + 1 > coinflip.number_of_players:
            coinflip.completed = True
            await update_coinflip(coinflip)

            # Calculate the haircut amount
            haircut_amount = coinflip.buy_in * (coinflip_settings.haircut / 100)
            # Calculate the refund amount
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
        if coinflip.players == "":
            coinflip.players = ln_address
        else:
            coinflip.players = f"{coinflip.players},{ln_address}"
        await update_coinflip(coinflip)

        # If last to join flip, calculate winner and pay them.
        coinflip_players = coinflip.players.split(",")
        if len(coinflip_players) == coinflip.number_of_players:
            coinflip.completed = True
            winner = random.choice(coinflip_players)
            coinflip.players = winner
            await update_coinflip(coinflip)
            # Calculate the total amount of winnings
            total_amount = coinflip.buy_in * len(coinflip_players)
            # Calculate the haircut amount
            haircut_amount = total_amount * (coinflip_settings.haircut / 100)
            # Calculate the winnings minus haircut
            max_sat = int(total_amount - haircut_amount)
            pr = await get_pr(winner, max_sat)
            if not pr:
                return
            if winner == ln_address:
                await websocket_updater(payment.payment_hash, f"won,{winner}")
                await pay_invoice(
                    wallet_id=coinflip_settings.wallet_id,
                    payment_request=pr,
                    max_sat=max_sat,
                    description="You flipping won the coinflip!",
                )
            if winner != ln_address:
                await websocket_updater(payment.payment_hash, f"lost,{winner}")
            return

        await websocket_updater(payment.payment_hash, "paid")

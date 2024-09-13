from datetime import datetime
from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash
from loguru import logger

from .models import (
    Coinflip,
    CoinflipSettings,
    CreateSatsDiceLink,
    CreateSatsDicePayment,
    CreateSatsDiceWithdraw,
    SatsdiceLink,
    SatsdicePayment,
    SatsdiceWithdraw,
)

db = Database("ext_satsdice")


async def create_satsdice_pay(wallet_id: str, data: CreateSatsDiceLink) -> SatsdiceLink:
    satsdice = SatsdiceLink(
        id=urlsafe_short_hash(),
        wallet=wallet_id,
        open_time=int(datetime.now().timestamp()),
        **data.dict(),
    )
    await db.execute(insert_query("satsdice.satsdice_pay", satsdice), satsdice.dict())
    return satsdice


async def get_satsdice_pay(link_id: str) -> Optional[SatsdiceLink]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_pay WHERE id = :id", {"id": link_id}
    )
    return SatsdiceLink(**row) if row else None


async def get_satsdice_pays(wallet_ids: Union[str, list[str]]) -> list[SatsdiceLink]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    rows = await db.fetchall(
        f"SELECT * FROM satsdice.satsdice_pay WHERE wallet IN ({q})"
    )
    return [SatsdiceLink(**row) for row in rows]


async def update_satsdice_pay(link: SatsdiceLink) -> SatsdiceLink:
    await db.execute(
        update_query(
            "satsdice.satsdice_pay",
            link,
        ),
        link.dict(),
    )
    return link


async def delete_satsdice_pay(link_id: str) -> None:
    await db.execute(
        "DELETE FROM satsdice.satsdice_pay WHERE id = :id", {"id": link_id}
    )


async def create_satsdice_payment(data: CreateSatsDicePayment) -> SatsdicePayment:
    payment = SatsdicePayment(**data.dict())
    await db.execute(
        update_query("satsdice.satsdice_payment", payment),
        payment.dict(),
    )
    return payment


async def get_satsdice_payment(payment_hash: str) -> Optional[SatsdicePayment]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_payment WHERE payment_hash = :payment_hash",
        {"payment_hash": payment_hash},
    )
    return SatsdicePayment(**row) if row else None


async def update_satsdice_payment(payment: SatsdicePayment) -> SatsdicePayment:
    await db.execute(
        update_query(
            "satsdice.satsdice_payment",
            payment,
            "WHERE payment_hash = :payment_hash",
        ),
        payment.dict(),
    )
    return payment


async def create_satsdice_withdraw(data: CreateSatsDiceWithdraw) -> SatsdiceWithdraw:
    withdraw = SatsdiceWithdraw(
        unique_hash=urlsafe_short_hash(),
        k1=urlsafe_short_hash(),
        open_time=int(datetime.now().timestamp()),
        id=data.payment_hash,
        satsdice_pay=data.satsdice_pay,
        value=data.value,
        used=data.used,
    )
    await db.execute(
        insert_query("satsdice.satsdice_withdraw", withdraw),
        withdraw.dict(),
    )
    return withdraw


async def get_satsdice_withdraw(withdraw_id: str) -> Optional[SatsdiceWithdraw]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE id = :id", {"id": withdraw_id}
    )
    return SatsdiceWithdraw(**row) if row else None


async def get_satsdice_withdraw_by_hash(unique_hash: str) -> Optional[SatsdiceWithdraw]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE unique_hash = :unique_hash",
        {"unique_hash": unique_hash},
    )
    return SatsdiceWithdraw(**row) if row else None


async def get_satsdice_withdraws(
    wallet_ids: Union[str, list[str]]
) -> list[SatsdiceWithdraw]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    rows = await db.fetchall(
        f"SELECT * FROM satsdice.satsdice_withdraw WHERE wallet IN ({q})"
    )

    return [SatsdiceWithdraw(**row) for row in rows]


async def update_satsdice_withdraw(withdraw: SatsdiceWithdraw) -> SatsdiceWithdraw:
    await db.execute(
        update_query("satsdice.satsdice_withdraw", withdraw),
        withdraw.dict(),
    )
    return withdraw


async def delete_satsdice_withdraw(withdraw_id: str) -> None:
    await db.execute(
        "DELETE FROM satsdice.satsdice_withdraw WHERE id = :id", {"id": withdraw_id}
    )


async def create_withdraw_hash_check(the_hash: str, lnurl_id: str):
    await db.execute(
        """
        INSERT INTO satsdice.hash_checkw (id, lnurl_id)
        VALUES (:id, :lnurl_id)
        """,
        {"id": the_hash, "lnurl_id": lnurl_id},
    )
    hash_check = await get_withdraw_hash_checkw(the_hash, lnurl_id)
    return hash_check


async def get_withdraw_hash_checkw(the_hash: str, lnurl_id: str):
    rowid = await db.fetchone(
        "SELECT * FROM satsdice.hash_checkw WHERE id = :hash", {"hash": the_hash}
    )
    rowlnurl = await db.fetchone(
        "SELECT * FROM satsdice.hash_checkw WHERE lnurl_id = :lnurl_id",
        {"lnurl_id": lnurl_id},
    )
    if not rowlnurl or not rowid:
        await create_withdraw_hash_check(the_hash, lnurl_id)
        return {"lnurl": True, "hash": False}
    else:
        return {"lnurl": True, "hash": True}


################
### Coinflip ###
################

# Coinflip Settings


async def set_coinflip_settings(settings: CoinflipSettings) -> None:
    fetch_settings = await get_coinflip_settings(settings.id)
    if fetch_settings:
        await db.execute(
            """
            UPDATE satsdice.settings
            SET max_players = ?, max_bet = ?, enabled = ?, haircut = ?, wallet_id = ?
            WHERE id = ?
            """,
            (
                settings.max_players,
                settings.max_bet,
                settings.enabled,
                settings.haircut,
                settings.wallet_id,
                settings.id,
            ),
        )
    else:
        page_id = urlsafe_short_hash()
        await db.execute(
            """
            INSERT INTO satsdice.settings (
                id, page_id, max_players, max_bet, enabled, haircut, wallet_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                settings.id,
                page_id,
                settings.max_players,
                settings.max_bet,
                settings.enabled,
                settings.haircut,
                settings.wallet_id,
            ),
        )
    return await get_coinflip_settings(settings.id)


async def get_coinflip_settings(
    coinflip_settings_id: str,
) -> Optional[CoinflipSettings]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.settings WHERE id = ?", (coinflip_settings_id,)
    )
    if row:
        return CoinflipSettings(**row) if row else None
    else:
        return None


async def get_coinflip_settings_page(
    coinflip_page_id: str,
) -> Optional[CoinflipSettings]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.settings WHERE page_id = ?", (coinflip_page_id,)
    )
    logger.debug(coinflip_page_id)
    if row:
        return CoinflipSettings(**row) if row else None
    else:
        return None


# Coinflips


async def create_coinflip(data: Coinflip) -> Coinflip:
    coinflip_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO satsdice.coinflip (
            id, name, number_of_players, buy_in, players, page_id, completed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            coinflip_id,
            data.name,
            data.number_of_players,
            data.buy_in,
            "",
            data.page_id,
            False,
        ),
    )
    return await get_coinflip(coinflip_id)


async def update_coinflip(coinflip: Coinflip) -> Coinflip:
    await db.execute(
        """
        UPDATE satsdice.coinflip
        SET players = ?, completed = ?
        WHERE id = ?
        """,
        (coinflip.players, coinflip.completed, coinflip.id),
    )
    return await get_coinflip(coinflip.id)


async def get_coinflip(coinflip_id: str) -> Optional[Coinflip]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.coinflip WHERE id = ?", (coinflip_id,)
    )
    return Coinflip(**row) if row else None


async def get_latest_coinflip(page_id: str) -> Optional[Coinflip]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.coinflip WHERE page_id = ? ORDER BY created_at DESC",
        (page_id,),
    )
    return Coinflip(**row) if row else None

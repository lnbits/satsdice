from datetime import datetime
from typing import List, Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    CreateSatsDiceLink,
    CreateSatsDicePayment,
    CreateSatsDiceWithdraw,
    SatsdiceLink,
    SatsdicePayment,
    SatsdiceWithdraw,
    CreateCoinflip,
    Coinflip,
    CoinflipParticipant,
    CoinflipSettings,
)

db = Database("ext_satsdice")


async def create_satsdice_pay(wallet_id: str, data: CreateSatsDiceLink) -> SatsdiceLink:
    satsdice_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO satsdice.satsdice_pay (
            id,
            wallet,
            title,
            base_url,
            min_bet,
            max_bet,
            amount,
            served_meta,
            served_pr,
            multiplier,
            chance,
            haircut,
            open_time
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?)
        """,
        (
            satsdice_id,
            wallet_id,
            data.title,
            data.base_url,
            data.min_bet,
            data.max_bet,
            data.multiplier,
            data.chance,
            data.haircut,
            int(datetime.now().timestamp()),
        ),
    )
    link = await get_satsdice_pay(satsdice_id)
    assert link, "Newly created link couldn't be retrieved"
    return link


async def get_satsdice_pay(link_id: str) -> Optional[SatsdiceLink]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_pay WHERE id = ?", (link_id,)
    )
    return SatsdiceLink(**row) if row else None


async def get_satsdice_pays(wallet_ids: Union[str, List[str]]) -> List[SatsdiceLink]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"""
        SELECT * FROM satsdice.satsdice_pay WHERE wallet IN ({q})
        ORDER BY id
        """,
        (*wallet_ids,),
    )
    return [SatsdiceLink(**row) for row in rows]


async def update_satsdice_pay(link_id: str, **kwargs) -> SatsdiceLink:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE satsdice.satsdice_pay SET {q} WHERE id = ?",
        (*kwargs.values(), link_id),
    )
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_pay WHERE id = ?", (link_id,)
    )
    return SatsdiceLink(**row)


async def increment_satsdice_pay(link_id: str, **kwargs) -> Optional[SatsdiceLink]:
    q = ", ".join([f"{field[0]} = {field[0]} + ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE satsdice.satsdice_pay SET {q} WHERE id = ?",
        (*kwargs.values(), link_id),
    )
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_pay WHERE id = ?", (link_id,)
    )
    return SatsdiceLink(**row) if row else None


async def delete_satsdice_pay(link_id: str) -> None:
    await db.execute("DELETE FROM satsdice.satsdice_pay WHERE id = ?", (link_id,))


##################SATSDICE PAYMENT LINKS


async def create_satsdice_payment(data: CreateSatsDicePayment) -> SatsdicePayment:
    await db.execute(
        """
        INSERT INTO satsdice.satsdice_payment (
            payment_hash,
            satsdice_pay,
            value,
            paid,
            lost
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.payment_hash,
            data.satsdice_pay,
            data.value,
            False,
            False,
        ),
    )
    payment = await get_satsdice_payment(data.payment_hash)
    assert payment, "Newly created withdraw couldn't be retrieved"
    return payment


async def get_satsdice_payment(payment_hash: str) -> Optional[SatsdicePayment]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_payment WHERE payment_hash = ?",
        (payment_hash,),
    )
    return SatsdicePayment(**row) if row else None


async def update_satsdice_payment(payment_hash: str, **kwargs) -> SatsdicePayment:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])

    await db.execute(
        f"UPDATE satsdice.satsdice_payment SET {q} WHERE payment_hash = ?",
        (bool(*kwargs.values()), payment_hash),
    )
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_payment WHERE payment_hash = ?",
        (payment_hash,),
    )
    return SatsdicePayment(**row)


##################SATSDICE WITHDRAW LINKS


async def create_satsdice_withdraw(data: CreateSatsDiceWithdraw) -> SatsdiceWithdraw:
    await db.execute(
        """
        INSERT INTO satsdice.satsdice_withdraw (
            id,
            satsdice_pay,
            value,
            unique_hash,
            k1,
            open_time,
            used
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.payment_hash,
            data.satsdice_pay,
            data.value,
            urlsafe_short_hash(),
            urlsafe_short_hash(),
            int(datetime.now().timestamp()),
            data.used,
        ),
    )
    withdraw = await get_satsdice_withdraw(data.payment_hash, 0)
    assert withdraw, "Newly created withdraw couldn't be retrieved"
    return withdraw


async def get_satsdice_withdraw(withdraw_id: str, num=0) -> Optional[SatsdiceWithdraw]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE id = ?", (withdraw_id,)
    )
    if not row:
        return None

    withdraw = []
    for item in row:
        withdraw.append(item)
    withdraw.append(num)
    return SatsdiceWithdraw(**row)


async def get_satsdice_withdraw_by_hash(
    unique_hash: str, num=0
) -> Optional[SatsdiceWithdraw]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE unique_hash = ?", (unique_hash,)
    )
    if not row:
        return None

    withdraw = []
    for item in row:
        withdraw.append(item)
    withdraw.append(num)
    return SatsdiceWithdraw(**row)


async def get_satsdice_withdraws(
    wallet_ids: Union[str, List[str]]
) -> List[SatsdiceWithdraw]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"SELECT * FROM satsdice.satsdice_withdraw WHERE wallet IN ({q})",
        (*wallet_ids,),
    )

    return [SatsdiceWithdraw(**row) for row in rows]


async def update_satsdice_withdraw(
    withdraw_id: str, **kwargs
) -> Optional[SatsdiceWithdraw]:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE satsdice.satsdice_withdraw SET {q} WHERE id = ?",
        (*kwargs.values(), withdraw_id),
    )
    row = await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE id = ?", (withdraw_id,)
    )
    return SatsdiceWithdraw(**row) if row else None


async def delete_satsdice_withdraw(withdraw_id: str) -> None:
    await db.execute(
        "DELETE FROM satsdice.satsdice_withdraw WHERE id = ?", (withdraw_id,)
    )


async def create_withdraw_hash_check(the_hash: str, lnurl_id: str):
    await db.execute(
        """
        INSERT INTO satsdice.hash_checkw (
            id,
            lnurl_id
        )
        VALUES (?, ?)
        """,
        (the_hash, lnurl_id),
    )
    hash_check = await get_withdraw_hash_checkw(the_hash, lnurl_id)
    return hash_check


async def get_withdraw_hash_checkw(the_hash: str, lnurl_id: str):
    rowid = await db.fetchone(
        "SELECT * FROM satsdice.hash_checkw WHERE id = ?", (the_hash,)
    )
    rowlnurl = await db.fetchone(
        "SELECT * FROM satsdice.hash_checkw WHERE lnurl_id = ?", (lnurl_id,)
    )
    if not rowlnurl or not rowid:
        await create_withdraw_hash_check(the_hash, lnurl_id)
        return {"lnurl": True, "hash": False}
    else:
        return {"lnurl": True, "hash": True}



################
### Coinflip ###
################

async def set_coinflip_settings(settings: CoinflipSettings) -> None:
    if not settings.id:
        settings_id = urlsafe_short_hash()
    else:
        settings_id = settings.id
    await db.execute(
        """
        INSERT INTO satsdice.settings (id, user_id, max_players, max_bet, enabled, haircut)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (settings_id, settings.user_id, settings.max_players, settings.max_bet, settings.enabled, settings.haircut)
    )
    return await get_coinflip_settings(settings_id)


async def create_coinflip(data: CreateCoinflip) -> Coinflip:
    coinflip_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO satsdice.coinflip (
            id, name, number_of_players, buy_in, created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            coinflip_id,
            data.name,
            data.number_of_players,
            data.buy_in,
            int(datetime.now().timestamp()),
        ),
    )
    return await get_coinflip(coinflip_id)

async def add_coinflip_participant(coinflip_id: str, lnaddress: str) -> CoinflipParticipant:
    participant_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO satsdice.coinflip_participants (
            id, coinflip_id, lnaddress, paid
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            participant_id,
            coinflip_id,
            lnaddress,
            False,
        ),
    )
    return await get_coinflip_participant(participant_id)


async def get_coinflip(user_id: str) -> Optional[Coinflip]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.coinflip WHERE user_id = ?", (user_id,)
    )
    return Coinflip(**row) if row else None

async def get_coinflip_participant(participant_id: str) -> Optional[CoinflipParticipant]:
    row = await db.fetchone(
        "SELECT * FROM satsdice.coinflip_participants WHERE id = ?", (participant_id,)
    )
    return CoinflipParticipant(**row) if row else None

async def mark_participant_paid(participant_id: str) -> None:
    await db.execute(
        "UPDATE satsdice.coinflip_participants SET paid = ? WHERE id = ?",
        (True, participant_id),
    )

async def get_coinflip_participants(coinflip_id: str) -> List[CoinflipParticipant]:
    rows = await db.fetchall(
        "SELECT * FROM satsdice.coinflip_participants WHERE coinflip_id = ?", (coinflip_id,)
    )
    return [CoinflipParticipant(**row) for row in rows]

async def get_coinflip_settings(coinflip_settings_id: str) -> CoinflipSettings:
    row = await db.fetchone("SELECT * FROM satsdice.settings WHERE id = ?", (coinflip_settings_id,))
    if row:
        return CoinflipSettings(**row['value'])
    return CoinflipSettings(enabled=False, haircut=0.0, max_bet=0, max_players=0)


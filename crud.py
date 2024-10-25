from datetime import datetime
from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    Coinflip,
    CoinflipSettings,
    CreateCoinflipSettings,
    CreateSatsDiceLink,
    CreateSatsDicePayment,
    CreateSatsDiceWithdraw,
    SatsdiceLink,
    SatsdicePayment,
    SatsdiceWithdraw,
)

db = Database("ext_satsdice")


async def create_satsdice_pay(data: CreateSatsDiceLink) -> SatsdiceLink:
    satsdice = SatsdiceLink(
        id=urlsafe_short_hash(),
        **data.dict(),
    )
    await db.insert("satsdice.satsdice_pay", satsdice)
    return satsdice


async def get_satsdice_pay(link_id: str) -> Optional[SatsdiceLink]:
    return await db.fetchone(
        "SELECT * FROM satsdice.satsdice_pay WHERE id = :id",
        {"id": link_id},
        SatsdiceLink,
    )


async def get_satsdice_pays(wallet_ids: Union[str, list[str]]) -> list[SatsdiceLink]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM satsdice.satsdice_pay WHERE wallet IN ({q})",
        model=SatsdiceLink,
    )


async def update_satsdice_pay(link: SatsdiceLink) -> SatsdiceLink:
    await db.update("satsdice.satsdice_pay", link)
    return link


async def delete_satsdice_pay(link_id: str) -> None:
    await db.execute(
        "DELETE FROM satsdice.satsdice_pay WHERE id = :id", {"id": link_id}
    )


async def create_satsdice_payment(data: CreateSatsDicePayment) -> SatsdicePayment:
    payment = SatsdicePayment(**data.dict())
    await db.insert("satsdice.satsdice_payment", payment)
    return payment


async def get_satsdice_payment(payment_hash: str) -> Optional[SatsdicePayment]:
    return await db.fetchone(
        "SELECT * FROM satsdice.satsdice_payment WHERE payment_hash = :payment_hash",
        {"payment_hash": payment_hash},
        SatsdicePayment,
    )


async def update_satsdice_payment(payment: SatsdicePayment) -> SatsdicePayment:
    await db.update(
        "satsdice.satsdice_payment",
        payment,
        "WHERE payment_hash = :payment_hash",
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
    await db.insert("satsdice.satsdice_withdraw", withdraw)
    return withdraw


async def get_satsdice_withdraw(withdraw_id: str) -> Optional[SatsdiceWithdraw]:
    return await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE id = :id",
        {"id": withdraw_id},
        SatsdiceWithdraw,
    )


async def get_satsdice_withdraw_by_hash(unique_hash: str) -> Optional[SatsdiceWithdraw]:
    return await db.fetchone(
        "SELECT * FROM satsdice.satsdice_withdraw WHERE unique_hash = :unique_hash",
        {"unique_hash": unique_hash},
        SatsdiceWithdraw,
    )


async def get_satsdice_withdraws(
    wallet_ids: Union[str, list[str]]
) -> list[SatsdiceWithdraw]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM satsdice.satsdice_withdraw WHERE wallet IN ({q})",
        model=SatsdiceWithdraw,
    )


async def update_satsdice_withdraw(withdraw: SatsdiceWithdraw) -> SatsdiceWithdraw:
    await db.update("satsdice.satsdice_withdraw", withdraw)
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
    result1 = await db.execute(
        "SELECT * FROM satsdice.hash_checkw WHERE id = :hash", {"hash": the_hash}
    )
    rowid = result1.mappings().first()
    result2 = await db.execute(
        "SELECT * FROM satsdice.hash_checkw WHERE lnurl_id = :lnurl_id",
        {"lnurl_id": lnurl_id},
    )
    rowlnurl = result2.mappings().first()
    if not rowlnurl or not rowid:
        await create_withdraw_hash_check(the_hash, lnurl_id)
        return {"lnurl": True, "hash": False}
    else:
        return {"lnurl": True, "hash": True}


################
### Coinflip ###
################

# Coinflip Settings


async def create_coinflip_settings(
    wallet_id: str, data: CreateCoinflipSettings
) -> CoinflipSettings:
    settings = CoinflipSettings(
        id=urlsafe_short_hash(),
        wallet_id=wallet_id,
        max_players=data.max_players,
        max_bet=data.max_bet,
        enabled=data.enabled,
        haircut=data.haircut,
    )
    await db.insert("satsdice.settings", settings)
    return settings


async def update_coinflip_settings(settings: CoinflipSettings) -> CoinflipSettings:
    await db.update("satsdice.settings", settings)
    return settings


async def get_coinflip_settings(
    coinflip_settings_id: str,
) -> Optional[CoinflipSettings]:
    return await db.fetchone(
        "SELECT * FROM satsdice.settings WHERE id = :id",
        {"id": coinflip_settings_id},
        CoinflipSettings,
    )


async def get_coinflip_settings_page(
    coinflip_page_id: str,
) -> Optional[CoinflipSettings]:
    return await db.fetchone(
        "SELECT * FROM satsdice.settings WHERE page_id = :id",
        {"id": coinflip_page_id},
        CoinflipSettings,
    )


# Coinflips
async def create_coinflip(data: Coinflip) -> Coinflip:
    coinflip_id = urlsafe_short_hash()
    data.id = coinflip_id
    await db.insert("satsdice.coinflip", data)
    return data


async def update_coinflip(coinflip: Coinflip) -> Coinflip:
    await db.update("satsdice.coinflip", coinflip)
    return coinflip


async def get_coinflip(coinflip_id: str) -> Optional[Coinflip]:
    return await db.fetchone(
        "SELECT * FROM satsdice.coinflip WHERE id = :id",
        {"id": coinflip_id},
        Coinflip,
    )


async def get_latest_coinflip(page_id: str) -> Optional[Coinflip]:
    return await db.fetchone(
        "SELECT * FROM satsdice.coinflip WHERE page_id = :id ORDER BY created_at DESC",
        {"page_id": page_id},
        Coinflip,
    )

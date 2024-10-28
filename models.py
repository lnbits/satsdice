import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import Query, Request
from lnurl import Lnurl
from lnurl import encode as lnurl_encode
from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel


class SatsdiceLink(BaseModel):
    id: str
    wallet: str
    title: str
    min_bet: int
    max_bet: int
    multiplier: float
    haircut: float
    chance: float
    base_url: str
    amount: int = 0
    served_meta: int = 0
    served_pr: int = 0
    # TODO: Change to datetime
    open_time: int = int(datetime.now(timezone.utc).timestamp())

    def lnurl(self, req: Request) -> str:
        return lnurl_encode(
            str(req.url_for("satsdice.lnurlp_response", link_id=self.id))
        )

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        return LnurlPayMetadata(
            json.dumps(
                [
                    [
                        "text/plain",
                        (
                            f"{self.title} (Chance: {self.chance}%, "
                            f"Multiplier: {self.multiplier})"
                        ),
                    ]
                ]
            )
        )

    def success_action(self, payment_hash: str, req: Request) -> Optional[dict]:
        url = str(
            req.url_for(
                "satsdice.displaywin", link_id=self.id, payment_hash=payment_hash
            )
        )
        return {"tag": "url", "description": "Check the attached link", "url": url}


class SatsdicePayment(BaseModel):
    payment_hash: str
    satsdice_pay: str
    value: int
    paid: bool = False
    lost: bool = False


class SatsdiceWithdraw(BaseModel):
    id: str
    satsdice_pay: str
    value: int
    unique_hash: str
    k1: str
    open_time: int
    used: int

    def lnurl(self, req: Request) -> Lnurl:
        return lnurl_encode(
            str(req.url_for("satsdice.lnurlw_response", unique_hash=self.unique_hash))
        )

    @property
    def is_spent(self) -> bool:
        return self.used >= 1

    def lnurl_response(self, req: Request):
        url = str(
            req.url_for("satsdice.api_lnurlw_callback", unique_hash=self.unique_hash)
        )
        withdraw_response = {
            "tag": "withdrawRequest",
            "callback": url,
            "k1": self.k1,
            "minWithdrawable": self.value * 1000,
            "maxWithdrawable": self.value * 1000,
            "defaultDescription": "Satsdice winnings!",
        }
        return withdraw_response


class HashCheck(BaseModel):
    id: str
    lnurl_id: str


class CreateSatsDiceLink(BaseModel):
    wallet: str = Query(None)
    title: str = Query(None)
    base_url: str = Query(None)
    min_bet: str = Query(None)
    max_bet: str = Query(None)
    multiplier: float = Query(0)
    chance: float = Query(0)
    haircut: float = Query(0)


class CreateSatsDicePayment(BaseModel):
    satsdice_pay: str = Query(None)
    value: int = Query(0)
    payment_hash: str = Query(None)


class CreateSatsDiceWithdraw(BaseModel):
    payment_hash: str = Query(None)
    satsdice_pay: str = Query(None)
    value: int = Query(0)
    used: int = Query(0)


class CreateSatsDiceWithdraws(BaseModel):
    title: str = Query(None)
    min_satsdiceable: int = Query(0)
    max_satsdiceable: int = Query(0)
    uses: int = Query(0)
    wait_time: str = Query(None)
    is_unique: bool = Query(False)


################
### Coinflip ###
################


class CreateCoinflipSettings(BaseModel):
    max_players: int = 5
    max_bet: int = 100
    enabled: bool = False
    haircut: float = 0.0


class CoinflipSettings(BaseModel):
    id: str
    wallet_id: str
    user_id: str
    max_players: int
    max_bet: int
    enabled: bool
    haircut: float


class Coinflip(BaseModel):
    id: Optional[str] = None
    settings_id: Optional[str] = None
    name: str
    number_of_players: int = 0
    buy_in: int = 0
    players: str = ""
    completed: bool = False
    created_at: datetime = datetime.now(timezone.utc)


class JoinCoinflipGame(BaseModel):
    game_id: str = Query(None)
    settings_id: str = Query(None)
    ln_address: str = Query(None)

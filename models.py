from datetime import datetime, timezone

from fastapi import Query
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

    @property
    def is_spent(self) -> bool:
        return self.used >= 1


#     def lnurl_response(self, req: Request):
#         url = str(
#             req.url_for("satsdice.api_lnurlw_callback", unique_hash=self.unique_hash)
#         )
#         withdraw_response = {
#             "tag": "withdrawRequest",
#             "callback": url,
#             "k1": self.k1,
#             "minWithdrawable": self.value * 1000,
#             "maxWithdrawable": self.value * 1000,
#             "defaultDescription": "Satsdice winnings!",
#         }
#         return withdraw_response


class HashCheck(BaseModel):
    id: str
    lnurl_id: str


class CreateSatsDiceLink(BaseModel):
    wallet: str = Query(None)
    title: str = Query(None)
    base_url: str = Query(None)
    min_bet: int = Query(None)
    max_bet: int = Query(None)
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

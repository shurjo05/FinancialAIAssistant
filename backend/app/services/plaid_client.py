"""Plaid client wrapper (sandbox).

Thin helpers over the Plaid SDK for the connect flow: create a Link token,
exchange the public token for an access token, look up the institution name, and
run incremental /transactions/sync. Sandbox only — fake institutions and the
test login user_good / pass_good; no real bank credentials are ever involved.

Mapping note: Plaid's amount sign (positive = money out) already matches our
convention (positive = expense), so synced rows drop straight into the same
categorize -> persist -> detect pipeline as CSV rows.
"""

import datetime

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.plaid")

_ENVIRONMENTS = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


def _client() -> plaid_api.PlaidApi:
    host = _ENVIRONMENTS.get(settings.plaid_env, plaid.Environment.Sandbox)
    config = plaid.Configuration(
        host=host,
        api_key={"clientId": settings.plaid_client_id, "secret": settings.plaid_secret},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(config))


def create_link_token(user_id: int) -> str:
    """Create a Link token that scopes the widget to this user + transactions."""
    req = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        client_name="JoMoney",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    return _client().link_token_create(req).link_token


def exchange_public_token(public_token: str) -> tuple[str, str]:
    """Exchange the Link public_token for a permanent (item_id, access_token)."""
    resp = _client().item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    return resp.item_id, resp.access_token


def get_institution_name(access_token: str) -> str | None:
    """Best-effort institution name for display (None on any failure)."""
    try:
        client = _client()
        item = client.item_get(ItemGetRequest(access_token=access_token)).item
        if not item.institution_id:
            return None
        inst = client.institutions_get_by_id(
            InstitutionsGetByIdRequest(
                institution_id=item.institution_id, country_codes=[CountryCode("US")]
            )
        )
        return inst.institution.name
    except Exception:
        logger.warning("could not resolve institution name")
        return None


def _enum_str(value) -> str | None:
    """Plaid SDK enums (AccountType / AccountSubtype) → plain strings."""
    if value is None:
        return None
    return str(getattr(value, "value", value))


def get_accounts(access_token: str) -> list[dict]:
    """The item's accounts with their latest balances (/accounts/get).

    Uses the cached balances Plaid returns for free with /accounts/get rather than
    the real-time /accounts/balance/get (billed per call in production) — plenty
    for a dashboard that refreshes on every sync.
    """
    resp = _client().accounts_get(AccountsGetRequest(access_token=access_token))
    out = []
    for a in resp.accounts:
        bal = a.balances
        out.append({
            "external_id": a.account_id,
            "name": getattr(a, "official_name", None) or a.name,
            "mask": getattr(a, "mask", None),
            "type": _enum_str(a.type) or "other",
            "subtype": _enum_str(getattr(a, "subtype", None)),
            "current_balance": getattr(bal, "current", None),
            "available_balance": getattr(bal, "available", None),
            "currency": getattr(bal, "iso_currency_code", None) or "USD",
        })
    return out


def _to_row(txn) -> dict:
    """Map one Plaid transaction to our internal row dict."""
    amount = float(txn.amount)  # positive = money out, matches our convention
    name = txn.name or ""
    date = txn.date if isinstance(txn.date, datetime.date) else datetime.date.fromisoformat(str(txn.date))
    return {
        "date": date,
        "description": name,
        "merchant_normalized": getattr(txn, "merchant_name", None) or name,
        "amount": amount,
        "transaction_type": "debit" if amount >= 0 else "credit",
    }


def sync_transactions(access_token: str, cursor: str | None) -> tuple[list[dict], str]:
    """Pull new transactions since `cursor`. Returns (row dicts, next cursor)."""
    client = _client()
    added = []
    cur = cursor
    while True:
        kwargs = {"access_token": access_token}
        if cur:
            kwargs["cursor"] = cur
        resp = client.transactions_sync(TransactionsSyncRequest(**kwargs))
        added.extend(resp.added)
        cur = resp.next_cursor
        if not resp.has_more:
            break
    return [_to_row(t) for t in added], cur

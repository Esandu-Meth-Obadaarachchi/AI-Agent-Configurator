"""Orders API: GET https://api.example.com/orders/{order_id}"""

from __future__ import annotations

import os

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

BASE_URL = "https://api.example.com"
PATH = "/orders/{order_id}"


class GetorderArgs(BaseModel):
    order_id: str = Field(description="The order id, e.g. ORD-1234")


@tool("get_order", args_schema=GetorderArgs)
async def get_order(order_id: str) -> str:
    "Look up an order by its id: status, amount and refund eligibility."
    url = BASE_URL + PATH.format(order_id=order_id)
    headers = {"Accept": "application/json"}
    token = os.environ.get("API_TOKEN")
    if token:
        headers["Authorization"] = token if " " in token else f"Bearer {token}"
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.request(
            "GET",
            url,
            headers=headers,
            params={},
        )
    return f"HTTP {res.status_code}\n{res.text[:4000]}"

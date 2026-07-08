import os
import base64
import requests

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"

PREMIUM_PRICE_USD = "5.00"


def get_access_token() -> str:
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    response = requests.post(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_order(custom_id: str, return_url: str, cancel_url: str) -> dict:
    access_token = get_access_token()
    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "custom_id": custom_id,
                "amount": {"currency_code": "USD", "value": PREMIUM_PRICE_USD},
                "description": "AskOverlay Premium",
            }],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "user_action": "PAY_NOW",
            },
        },
    )
    response.raise_for_status()
    order = response.json()
    approve_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
    return {"order_id": order["id"], "approve_url": approve_url}

def capture_order(order_id: str) -> dict:
    access_token = get_access_token()
    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()
import asyncio

import json

import example_utils

from hyperliquid.utils import constants

PURR = "PURR/USDC"
OTHER_COIN = "@8"
OTHER_COIN_NAME = "KORILA/USDC"


async def main():
    address, info, exchange = await example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)

    # Get the user state and print out position information
    spot_user_state = await info.spot_user_state(address)
    if len(spot_user_state["balances"]) > 0:
        print("spot balances:")
        for balance in spot_user_state["balances"]:
            print(json.dumps(balance, indent=2))
    else:
        print("no available token balances")

    # Place an order that should rest by setting the price very low
    order_result = await exchange.order(PURR, True, 24, 0.5, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Query the order status by oid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            order_status = await info.query_order_by_oid(address, status["resting"]["oid"])
            print("Order status by oid:", order_status)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = await exchange.cancel(PURR, status["resting"]["oid"])
            print(cancel_result)

    # For other spot assets other than PURR/USDC use @{index} e.g. on testnet @8 is KORILA/USDC
    order_result = await exchange.order(OTHER_COIN, True, 1, 12, {"limit": {"tif": "Gtc"}})
    print(order_result)
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            # The sdk now also support using spot names, although be careful as they might not always be unique
            cancel_result = await exchange.cancel(OTHER_COIN_NAME, status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    asyncio.run(main())

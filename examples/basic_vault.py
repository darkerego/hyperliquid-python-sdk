import asyncio

import example_utils

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Change this address to a vault that you lead or a subaccount that you own
    vault = "0x1719884eb866cb12b2287399b15f7db5e7d775ea"

    # Place an order that should rest by setting the price very low
    exchange = await Exchange.create(exchange.wallet, exchange.base_url, vault_address=vault)
    order_result = await exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = await exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    asyncio.run(main())

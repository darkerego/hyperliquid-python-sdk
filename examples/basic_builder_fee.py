import asyncio

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Only the main wallet has permission to approve a builder fee")

    # approve setting a builder fee
    approve_result = await exchange.approve_builder_fee("0x8c967E73E7B15087c42A10D344cFf4c96D877f1D", "0.001%")
    print(approve_result)

    # place an order with builder set, this will cause an additional fee to be added to the order which is sent to the builder
    order_result = await exchange.market_open(
        "ETH", True, 0.05, None, 0.01, builder={"b": "0x8c967E73E7B15087c42A10D344cFf4c96D877f1D", "f": 1}
    )
    print(order_result)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    open_orders = await info.open_orders(address)
    for open_order in open_orders:
        print(f"cancelling order {open_order}")
        await exchange.cancel(open_order["coin"], open_order["oid"])


if __name__ == "__main__":
    asyncio.run(main())

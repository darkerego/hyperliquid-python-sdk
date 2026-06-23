import asyncio

import example_utils

from hyperliquid.utils import constants


# This example shows how to switch an account to use big blocks on the EVM
async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    print(await exchange.use_big_blocks(True))
    print(await exchange.use_big_blocks(False))


if __name__ == "__main__":
    asyncio.run(main())

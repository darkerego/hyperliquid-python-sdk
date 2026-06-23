import asyncio

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Transfer 1.23 USDC from perp wallet to spot wallet
    transfer_result = await exchange.usd_class_transfer(1.23, False)
    print(transfer_result)

    # Transfer 1.23 USDC from spot wallet to perp wallet
    transfer_result = await exchange.usd_class_transfer(1.23, True)
    print(transfer_result)


if __name__ == "__main__":
    asyncio.run(main())

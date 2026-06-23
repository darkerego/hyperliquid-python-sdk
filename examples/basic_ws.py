import asyncio

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, _ = await example_utils.setup(constants.TESTNET_API_URL)
    # An example showing how to subscribe to the different subscription types and prints the returned messages
    # Some subscriptions do not return snapshots, so you will not receive a message until something happens
    await info.subscribe({"type": "allMids"}, print)
    await info.subscribe({"type": "l2Book", "coin": "ETH"}, print)
    await info.subscribe({"type": "trades", "coin": "PURR/USDC"}, print)
    await info.subscribe({"type": "userEvents", "user": address}, print)
    await info.subscribe({"type": "userFills", "user": address}, print)
    await info.subscribe({"type": "candle", "coin": "ETH", "interval": "1m"}, print)
    await info.subscribe({"type": "orderUpdates", "user": address}, print)
    await info.subscribe({"type": "userFundings", "user": address}, print)
    await info.subscribe({"type": "userNonFundingLedgerUpdates", "user": address}, print)
    await info.subscribe({"type": "webData2", "user": address}, print)
    await info.subscribe({"type": "bbo", "coin": "ETH"}, print)
    await info.subscribe({"type": "activeAssetCtx", "coin": "BTC"}, print)  # Perp
    await info.subscribe({"type": "activeAssetCtx", "coin": "@1"}, print)  # Spot
    await info.subscribe({"type": "activeAssetData", "user": address, "coin": "BTC"}, print)  # Perp only
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

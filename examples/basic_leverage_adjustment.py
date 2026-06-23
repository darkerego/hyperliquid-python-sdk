import asyncio

import json

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Get the user state and print out leverage information for ETH
    user_state = await info.user_state(address)
    for asset_position in user_state["assetPositions"]:
        if asset_position["position"]["coin"] == "ETH":
            print("Current leverage for ETH:", json.dumps(asset_position["position"]["leverage"], indent=2))

    # Set the ETH leverage to 21x (cross margin)
    print(await exchange.update_leverage(21, "ETH"))

    # Set the ETH leverage to 22x (isolated margin)
    print(await exchange.update_leverage(21, "ETH", False))

    # Add 1 dollar of extra margin to the ETH position
    print(await exchange.update_isolated_margin(1, "ETH"))

    # Get the user state and print out the final leverage information after our changes
    user_state = await info.user_state(address)
    for asset_position in user_state["assetPositions"]:
        if asset_position["position"]["coin"] == "ETH":
            print("Current leverage for ETH:", json.dumps(asset_position["position"]["leverage"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())

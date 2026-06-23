import asyncio

import json

import example_utils

from hyperliquid.utils import constants


async def main():
    address, info, exchange = await example_utils.setup(base_url=constants.MAINNET_API_URL, skip_ws=True)

    # Get the user staking summary and print information
    user_staking_summary = await info.user_staking_summary(address)
    print("Staking summary:")
    print(json.dumps(user_staking_summary, indent=2))

    # Get the user staking delegations and print information
    user_stakes = await info.user_staking_delegations(address)
    print("Staking breakdown:")
    print(json.dumps(user_stakes, indent=2))

    # Get the user staking reward history and print information
    user_staking_rewards = await info.user_staking_rewards(address)
    print("Most recent staking rewards:")
    print(json.dumps(user_staking_rewards[:5], indent=2))


if __name__ == "__main__":
    asyncio.run(main())

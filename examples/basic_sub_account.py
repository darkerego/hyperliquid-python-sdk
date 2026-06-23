import asyncio

import example_utils

from hyperliquid.utils import constants


# This example shows how to create, query, and transfer funds to a subaccount.
# To trade as a subaccount set vault_address to the subaccount's address. See basic_vault.py for an example.
async def main():
    address, info, exchange = await example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    name = "example123"
    print(await exchange.create_sub_account(name))

    sub_accounts = await info.query_sub_accounts(address)
    sub_account_user = None
    for sub_account in sub_accounts:
        if sub_account["name"] == name:
            sub_account_user = sub_account["subAccountUser"]

    # Transfer 1 USD to the subaccount
    print(await exchange.sub_account_transfer(sub_account_user, True, 1_000_000))
    # Transfer 1.23 HYPE to the subaccount (the token string assumes testnet, the address needs to be changed for mainnet)
    print(await exchange.sub_account_spot_transfer(sub_account_user, True, "HYPE:0x7317beb7cceed72ef0b346074cc8e7ab", 1.23))


if __name__ == "__main__":
    asyncio.run(main())

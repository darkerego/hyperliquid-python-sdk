import asyncio

from hyperliquid.api import API
from hyperliquid.utils.types import (
    Any,
    Callable,
    Cloid,
    List,
    Meta,
    Optional,
    SpotMeta,
    SpotMetaAndAssetCtxs,
    Subscription,
    cast,
)
from hyperliquid.websocket_manager import WebsocketManager


class Info(API):
    def __init__(
        self,
        base_url: Optional[str] = None,
        skip_ws: Optional[bool] = False,
        meta: Optional[Meta] = None,
        spot_meta: Optional[SpotMeta] = None,
        perp_dexs: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        session=None,
    ):
        super().__init__(base_url, timeout, session=session)
        self.skip_ws = bool(skip_ws)
        self.ws_manager: Optional[WebsocketManager] = None
        self._provided_meta = meta
        self._provided_spot_meta = spot_meta
        self._requested_perp_dexs = perp_dexs
        self._initialized = False
        self._init_lock = asyncio.Lock()

        self.coin_to_asset = {}
        self.name_to_coin = {}
        self.asset_to_sz_decimals = {}

    @classmethod
    async def create(cls, *args, **kwargs) -> "Info":
        client = cls(*args, **kwargs)
        await client.initialize()
        return client

    async def initialize(self) -> "Info":
        if self._initialized:
            return self

        async with self._init_lock:
            if self._initialized:
                return self

            if not self.skip_ws:
                self.ws_manager = WebsocketManager(self.base_url)
                await self.ws_manager.start()

            spot_meta = self._provided_spot_meta
            if spot_meta is None:
                spot_meta = cast(SpotMeta, await self.post("/info", {"type": "spotMeta"}))

            self.coin_to_asset = {}
            self.name_to_coin = {}
            self.asset_to_sz_decimals = {}

            token_by_index = {token["index"]: token for token in spot_meta["tokens"]}

            for spot_info in spot_meta["universe"]:
                asset = spot_info["index"] + 10000
                self.coin_to_asset[spot_info["name"]] = asset
                self.name_to_coin[spot_info["name"]] = spot_info["name"]
                base, quote = spot_info["tokens"]
                base_info = token_by_index[base]
                quote_info = token_by_index[quote]
                self.asset_to_sz_decimals[asset] = base_info["szDecimals"]
                name = f'{base_info["name"]}/{quote_info["name"]}'
                if name not in self.name_to_coin:
                    self.name_to_coin[name] = spot_info["name"]

            perp_dex_to_offset = {"": 0}
            perp_dexs = self._requested_perp_dexs
            if perp_dexs is None:
                perp_dexs = [""]
            else:
                perp_dex_entries = await self.perp_dexs()
                for i, perp_dex in enumerate(perp_dex_entries[1:]):
                    perp_dex_to_offset[perp_dex["name"]] = 110000 + i * 10000

            for perp_dex in perp_dexs:
                offset = perp_dex_to_offset[perp_dex]
                if perp_dex == "" and self._provided_meta is not None:
                    self.set_perp_meta(self._provided_meta, 0)
                else:
                    fresh_meta = await self.meta(dex=perp_dex)
                    self.set_perp_meta(fresh_meta, offset)

            self._initialized = True

        return self

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def aclose(self) -> None:
        if self.ws_manager is not None:
            await self.ws_manager.stop()
            self.ws_manager = None
        await super().aclose()

    def set_perp_meta(self, meta: Meta, offset: int) -> Any:
        for asset, asset_info in enumerate(meta["universe"]):
            asset += offset
            self.coin_to_asset[asset_info["name"]] = asset
            self.name_to_coin[asset_info["name"]] = asset_info["name"]
            self.asset_to_sz_decimals[asset] = asset_info["szDecimals"]

    async def disconnect_websocket(self) -> None:
        if self.ws_manager is None:
            raise RuntimeError("Cannot call disconnect_websocket since skip_ws was used")
        await self.ws_manager.stop()
        self.ws_manager = None

    async def user_state(self, address: str, dex: str = "") -> Any:
        return await self.post("/info", {"type": "clearinghouseState", "user": address, "dex": dex})

    async def spot_user_state(self, address: str) -> Any:
        return await self.post("/info", {"type": "spotClearinghouseState", "user": address})

    async def open_orders(self, address: str, dex: str = "") -> Any:
        return await self.post("/info", {"type": "openOrders", "user": address, "dex": dex})

    async def frontend_open_orders(self, address: str, dex: str = "") -> Any:
        return await self.post("/info", {"type": "frontendOpenOrders", "user": address, "dex": dex})

    async def all_mids(self, dex: str = "") -> Any:
        return await self.post("/info", {"type": "allMids", "dex": dex})

    async def user_fills(self, address: str) -> Any:
        return await self.post("/info", {"type": "userFills", "user": address})

    async def user_fills_by_time(
        self, address: str, start_time: int, end_time: Optional[int] = None, aggregate_by_time: Optional[bool] = False
    ) -> Any:
        return await self.post(
            "/info",
            {
                "type": "userFillsByTime",
                "user": address,
                "startTime": start_time,
                "endTime": end_time,
                "aggregateByTime": aggregate_by_time,
            },
        )

    async def meta(self, dex: str = "") -> Meta:
        return cast(Meta, await self.post("/info", {"type": "meta", "dex": dex}))

    async def meta_and_asset_ctxs(self) -> Any:
        return await self.post("/info", {"type": "metaAndAssetCtxs"})

    async def perp_dexs(self) -> Any:
        return await self.post("/info", {"type": "perpDexs"})

    async def spot_meta(self) -> SpotMeta:
        return cast(SpotMeta, await self.post("/info", {"type": "spotMeta"}))

    async def spot_meta_and_asset_ctxs(self) -> SpotMetaAndAssetCtxs:
        return cast(SpotMetaAndAssetCtxs, await self.post("/info", {"type": "spotMetaAndAssetCtxs"}))

    async def funding_history(self, name: str, startTime: int, endTime: Optional[int] = None) -> Any:
        await self._ensure_initialized()
        coin = self.name_to_coin[name]
        if endTime is not None:
            return await self.post(
                "/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime, "endTime": endTime}
            )
        return await self.post("/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime})

    async def user_funding_history(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        if endTime is not None:
            return await self.post(
                "/info", {"type": "userFunding", "user": user, "startTime": startTime, "endTime": endTime}
            )
        return await self.post("/info", {"type": "userFunding", "user": user, "startTime": startTime})

    async def l2_snapshot(self, name: str) -> Any:
        await self._ensure_initialized()
        return await self.post("/info", {"type": "l2Book", "coin": self.name_to_coin[name]})

    async def candles_snapshot(self, name: str, interval: str, startTime: int, endTime: int) -> Any:
        await self._ensure_initialized()
        req = {"coin": self.name_to_coin[name], "interval": interval, "startTime": startTime, "endTime": endTime}
        return await self.post("/info", {"type": "candleSnapshot", "req": req})

    async def user_fees(self, address: str) -> Any:
        return await self.post("/info", {"type": "userFees", "user": address})

    async def user_staking_summary(self, address: str) -> Any:
        return await self.post("/info", {"type": "delegatorSummary", "user": address})

    async def user_staking_delegations(self, address: str) -> Any:
        return await self.post("/info", {"type": "delegations", "user": address})

    async def user_staking_rewards(self, address: str) -> Any:
        return await self.post("/info", {"type": "delegatorRewards", "user": address})

    async def delegator_history(self, user: str) -> Any:
        return await self.post("/info", {"type": "delegatorHistory", "user": user})

    async def query_order_by_oid(self, user: str, oid: int) -> Any:
        return await self.post("/info", {"type": "orderStatus", "user": user, "oid": oid})

    async def query_order_by_cloid(self, user: str, cloid: Cloid) -> Any:
        return await self.post("/info", {"type": "orderStatus", "user": user, "oid": cloid.to_raw()})

    async def query_referral_state(self, user: str) -> Any:
        return await self.post("/info", {"type": "referral", "user": user})

    async def query_sub_accounts(self, user: str) -> Any:
        return await self.post("/info", {"type": "subAccounts", "user": user})

    async def query_user_to_multi_sig_signers(self, multi_sig_user: str) -> Any:
        return await self.post("/info", {"type": "userToMultiSigSigners", "user": multi_sig_user})

    async def query_perp_deploy_auction_status(self) -> Any:
        return await self.post("/info", {"type": "perpDeployAuctionStatus"})

    async def query_user_dex_abstraction_state(self, user: str) -> Any:
        return await self.post("/info", {"type": "userDexAbstraction", "user": user})

    async def query_user_abstraction_state(self, user: str) -> Any:
        return await self.post("/info", {"type": "userAbstraction", "user": user})

    async def historical_orders(self, user: str) -> Any:
        return await self.post("/info", {"type": "historicalOrders", "user": user})

    async def user_non_funding_ledger_updates(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        return await self.post(
            "/info",
            {"type": "userNonFundingLedgerUpdates", "user": user, "startTime": startTime, "endTime": endTime},
        )

    async def portfolio(self, user: str) -> Any:
        return await self.post("/info", {"type": "portfolio", "user": user})

    async def user_twap_slice_fills(self, user: str) -> Any:
        return await self.post("/info", {"type": "userTwapSliceFills", "user": user})

    async def user_vault_equities(self, user: str) -> Any:
        return await self.post("/info", {"type": "userVaultEquities", "user": user})

    async def user_role(self, user: str) -> Any:
        return await self.post("/info", {"type": "userRole", "user": user})

    async def user_rate_limit(self, user: str) -> Any:
        return await self.post("/info", {"type": "userRateLimit", "user": user})

    async def query_spot_deploy_auction_status(self, user: str) -> Any:
        return await self.post("/info", {"type": "spotDeployState", "user": user})

    async def extra_agents(self, user: str) -> Any:
        return await self.post("/info", {"type": "extraAgents", "user": user})

    def _remap_coin_subscription(self, subscription: Subscription) -> None:
        if subscription["type"] in {"l2Book", "trades", "candle", "bbo", "activeAssetCtx"}:
            subscription["coin"] = self.name_to_coin[subscription["coin"]]

    async def subscribe(self, subscription: Subscription, callback: Callable[[Any], None]) -> int:
        await self._ensure_initialized()
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call subscribe since skip_ws was used")
        return await self.ws_manager.subscribe(subscription, callback)

    async def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        await self._ensure_initialized()
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call unsubscribe since skip_ws was used")
        return await self.ws_manager.unsubscribe(subscription, subscription_id)

    async def name_to_asset(self, name: str) -> int:
        await self._ensure_initialized()
        return self.coin_to_asset[self.name_to_coin[name]]

import asyncio
import inspect
import json
import logging
from collections import defaultdict

import websockets

from hyperliquid.utils.types import Any, Callable, Dict, List, NamedTuple, Optional, Subscription, Tuple, WsMsg

ActiveSubscription = NamedTuple("ActiveSubscription", [("callback", Callable[[Any], None]), ("subscription_id", int)])


def subscription_to_identifier(subscription: Subscription) -> str:
    if subscription["type"] == "allMids":
        return "allMids"
    elif subscription["type"] == "l2Book":
        return f'l2Book:{subscription["coin"].lower()}'
    elif subscription["type"] == "trades":
        return f'trades:{subscription["coin"].lower()}'
    elif subscription["type"] == "userEvents":
        return "userEvents"
    elif subscription["type"] == "userFills":
        return f'userFills:{subscription["user"].lower()}'
    elif subscription["type"] == "candle":
        return f'candle:{subscription["coin"].lower()},{subscription["interval"]}'
    elif subscription["type"] == "orderUpdates":
        return "orderUpdates"
    elif subscription["type"] == "userFundings":
        return f'userFundings:{subscription["user"].lower()}'
    elif subscription["type"] == "userNonFundingLedgerUpdates":
        return f'userNonFundingLedgerUpdates:{subscription["user"].lower()}'
    elif subscription["type"] == "webData2":
        return f'webData2:{subscription["user"].lower()}'
    elif subscription["type"] == "bbo":
        return f'bbo:{subscription["coin"].lower()}'
    elif subscription["type"] == "activeAssetCtx":
        return f'activeAssetCtx:{subscription["coin"].lower()}'
    elif subscription["type"] == "activeAssetData":
        return f'activeAssetData:{subscription["coin"].lower()},{subscription["user"].lower()}'
    raise ValueError(f"Unsupported subscription type: {subscription['type']}")


def ws_msg_to_identifier(ws_msg: WsMsg) -> Optional[str]:
    if ws_msg["channel"] == "pong":
        return "pong"
    elif ws_msg["channel"] == "allMids":
        return "allMids"
    elif ws_msg["channel"] == "l2Book":
        return f'l2Book:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "trades":
        trades = ws_msg["data"]
        if len(trades) == 0:
            return None
        return f'trades:{trades[0]["coin"].lower()}'
    elif ws_msg["channel"] == "user":
        return "userEvents"
    elif ws_msg["channel"] == "userFills":
        return f'userFills:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "candle":
        return f'candle:{ws_msg["data"]["s"].lower()},{ws_msg["data"]["i"]}'
    elif ws_msg["channel"] == "orderUpdates":
        return "orderUpdates"
    elif ws_msg["channel"] == "userFundings":
        return f'userFundings:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "userNonFundingLedgerUpdates":
        return f'userNonFundingLedgerUpdates:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "webData2":
        return f'webData2:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "bbo":
        return f'bbo:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "activeAssetCtx" or ws_msg["channel"] == "activeSpotAssetCtx":
        return f'activeAssetCtx:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "activeAssetData":
        return f'activeAssetData:{ws_msg["data"]["coin"].lower()},{ws_msg["data"]["user"].lower()}'
    return None


class WebsocketManager:
    def __init__(self, base_url: str):
        self.subscription_id_counter = 0
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        self.ws_url = "ws" + base_url[len("http") :] + "/ws"
        self.ws = None
        self._runner_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._ready_event = asyncio.Event()
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._runner_task is not None and not self._runner_task.done():
            return
        self._stop_event.clear()
        self._runner_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self.ws is not None:
            await self.ws.close()
        if self._runner_task is not None:
            await self._runner_task
        self._ready_event.clear()

    async def _run(self) -> None:
        try:
            async with websockets.connect(self.ws_url, ping_interval=None) as websocket:
                self.ws = websocket
                self._ready_event.set()
                for subscription, active_subscription in list(self.queued_subscriptions):
                    await self.subscribe(subscription, active_subscription.callback, active_subscription.subscription_id)
                self.queued_subscriptions.clear()
                self._ping_task = asyncio.create_task(self._send_ping())
                await self._consume_messages()
        finally:
            self.ws = None
            self._ready_event.clear()
            if self._ping_task is not None:
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
                self._ping_task = None

    async def _send_ping(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(50)
                if self.ws is None:
                    break
                logging.debug("Websocket sending ping")
                await self.ws.send(json.dumps({"method": "ping"}))
        except asyncio.CancelledError:
            raise
        finally:
            logging.debug("Websocket ping sender stopped")

    async def _consume_messages(self) -> None:
        assert self.ws is not None
        async for message in self.ws:
            if message == "Websocket connection established.":
                logging.debug(message)
                continue
            logging.debug("on_message %s", message)
            ws_msg: WsMsg = json.loads(message)
            identifier = ws_msg_to_identifier(ws_msg)
            if identifier == "pong":
                logging.debug("Websocket received pong")
                continue
            if identifier is None:
                logging.debug("Websocket not handling empty message")
                continue
            active_subscriptions = self.active_subscriptions[identifier]
            if len(active_subscriptions) == 0:
                print("Websocket message from an unexpected subscription:", message, identifier)
                continue
            for active_subscription in active_subscriptions:
                result = active_subscription.callback(ws_msg)
                if inspect.isawaitable(result):
                    asyncio.create_task(result)

    async def subscribe(
        self, subscription: Subscription, callback: Callable[[Any], None], subscription_id: Optional[int] = None
    ) -> int:
        if subscription_id is None:
            self.subscription_id_counter += 1
            subscription_id = self.subscription_id_counter
        if not self._ready_event.is_set():
            logging.debug("enqueueing subscription")
            self.queued_subscriptions.append((subscription, ActiveSubscription(callback, subscription_id)))
            return subscription_id

        logging.debug("subscribing")
        identifier = subscription_to_identifier(subscription)
        if identifier == "userEvents" or identifier == "orderUpdates":
            # TODO: ideally the userEvent and orderUpdates messages would include the user so that we can multiplex
            if len(self.active_subscriptions[identifier]) != 0:
                raise NotImplementedError(f"Cannot subscribe to {identifier} multiple times")

        self.active_subscriptions[identifier].append(ActiveSubscription(callback, subscription_id))
        assert self.ws is not None
        await self.ws.send(json.dumps({"method": "subscribe", "subscription": subscription}))
        return subscription_id

    async def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        if not self._ready_event.is_set():
            raise NotImplementedError("Can't unsubscribe before websocket connected")

        identifier = subscription_to_identifier(subscription)
        active_subscriptions = self.active_subscriptions[identifier]
        new_active_subscriptions = [x for x in active_subscriptions if x.subscription_id != subscription_id]
        if len(new_active_subscriptions) == 0:
            assert self.ws is not None
            await self.ws.send(json.dumps({"method": "unsubscribe", "subscription": subscription}))
        self.active_subscriptions[identifier] = new_active_subscriptions
        return len(active_subscriptions) != len(new_active_subscriptions)

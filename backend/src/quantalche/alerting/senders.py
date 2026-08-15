from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger("quantalche.alerting")


class AlertSender(ABC):
    """One delivery channel (architecture.md Layer 9: "Telegram/Discord
    bot, webhook, or email"). A sender's job is just "deliver this text
    somewhere" -- formatting lives in dispatcher.py, not here, so adding a
    channel never means duplicating message logic.

    Failures are logged and swallowed, never raised -- a broken alert
    channel must not take down signal processing (api/state.py calls
    senders synchronously inline with process_bar). NOT source-stated --
    standard alerting-system practice, not a trading rule.
    """

    name: str

    @abstractmethod
    def send(self, message: str) -> None:
        raise NotImplementedError


class WebhookAlertSender(AlertSender):
    """Generic webhook: POSTs {"text": message} to a configured URL.
    The simplest, most universally-integrable channel -- works with
    Zapier/IFTTT/n8n/a custom endpoint/anything that accepts JSON.
    """

    name = "webhook"

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        self.url = url
        self.timeout = timeout

    def send(self, message: str) -> None:
        try:
            httpx.post(self.url, json={"text": message}, timeout=self.timeout)
        except httpx.HTTPError as exc:
            logger.warning("Webhook alert failed: %s", exc)


class DiscordAlertSender(AlertSender):
    """Discord incoming webhook -- https://discord.com/developers/docs/resources/webhook
    Payload shape ({"content": ...}) is Discord-specific, everything else
    about the mechanism is identical to WebhookAlertSender.
    """

    name = "discord"

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, message: str) -> None:
        try:
            httpx.post(self.webhook_url, json={"content": message}, timeout=self.timeout)
        except httpx.HTTPError as exc:
            logger.warning("Discord alert failed: %s", exc)


class TelegramAlertSender(AlertSender):
    """Telegram Bot API sendMessage --
    https://core.telegram.org/bots/api#sendmessage

    NOT live-tested against a real Telegram bot/chat -- this project has
    no Telegram credentials to test with. Implemented directly from the
    Bot API spec and exercised against a local mock server matching that
    spec's request/response shape (see rule-mapping.md), not the real
    api.telegram.org. Flagged explicitly rather than silently claimed as
    verified.
    """

    name = "telegram"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        timeout: float = 10.0,
        base_url: str = "https://api.telegram.org",
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    def send(self, message: str) -> None:
        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={"chat_id": self.chat_id, "text": message},
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Telegram alert rejected (HTTP %s): %s",
                    response.status_code,
                    response.text,
                )
        except httpx.HTTPError as exc:
            logger.warning("Telegram alert failed: %s", exc)

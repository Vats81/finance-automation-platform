import logging

import httpx

from app.shared.application.ports import IWhatsAppSender

logger = logging.getLogger(__name__)

_TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"


class ConsoleWhatsAppSender(IWhatsAppSender):
    """Dev fallback: logs the message instead of sending it — same
    swap-by-settings idea as ConsoleEmailSender.
    """

    async def send(self, *, to: str, message: str) -> None:
        logger.info("=== WHATSAPP (console sender) ===\nTo: %s\n\n%s", to, message)


class TwilioWhatsAppSender(IWhatsAppSender):
    """Plain REST calls via httpx — no Twilio SDK dependency needed. Sends
    text only; see IWhatsAppSender's docstring for why media isn't
    supported yet.
    """

    def __init__(self, *, account_sid: str, auth_token: str, from_number: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    async def send(self, *, to: str, message: str) -> None:
        url = _TWILIO_MESSAGES_URL.format(account_sid=self._account_sid)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(self._account_sid, self._auth_token),
                data={
                    "From": f"whatsapp:{self._from_number}",
                    "To": f"whatsapp:{to}",
                    "Body": message,
                },
            )
            response.raise_for_status()

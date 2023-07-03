from sp.spm import SPMessages

from vkbottle import BaseMiddleware
from vkbottle.bot import Message


class SpMiddleware(BaseMiddleware[Message]):
    async def pre(self):
        self.send({"sp": SPMessages(str(self.event.peer_id))})

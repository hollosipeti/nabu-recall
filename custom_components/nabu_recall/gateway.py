"""Private HAOS application HTTP bridge."""
import aiohttp

class Bridge:
    def __init__(self, session, url, token):
        self.session = session
        self.base = url.rstrip("/")
        self.headers = {"X-Recall-Token": token}

    async def post(self, path, payload, timeout=5):
        async with self.session.post(
            self.base + "/bridge/" + path,
            json=payload, headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=False,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def ping(self):
        return (await self.post("ping", {})).get("ok") is True

    async def recall(self, query):
        return (await self.post("recall", {"query": query}, timeout=20)).get("context", "")

    async def log(self, user, assistant, conversation_id):
        return await self.post(
            "turn", {"user": user, "assistant": assistant, "conversation_id": conversation_id})

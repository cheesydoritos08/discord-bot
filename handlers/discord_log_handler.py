import logging
import aiohttp
import asyncio


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url, level=logging.INFO):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.session = None
        self.log_queue = asyncio.Queue()
        self.worker_task = None
        self._shutdown_event = asyncio.Event()

    def emit(self, record):
        if record.levelno < self.level:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(asyncio.create_task, self.log_queue.put(record))
            if not self.worker_task or self.worker_task.done():
                self.worker_task = asyncio.create_task(self._log_worker())
        except RuntimeError:
            # fallback if no loop is running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_log_sync(record))
            loop.close()

    async def _log_worker(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

        while not self._shutdown_event.is_set() or not self.log_queue.empty():
            try:
                record = await self.log_queue.get()
                await self._send_log(record)
                await asyncio.sleep(2)  # throttle to avoid 429
            except Exception as e:
                print(f'[log_worker exception] {e}')

    async def _send_log(self, record):
        message = self.format(record)
        if len(message) > 1990:
            message = message[:1990] + '...'
        data = {'content': f'```{message}```'}

        try:
            async with self.session.post(self.webhook_url, json=data) as resp:
                if resp.status != 204:
                    print(f'[webhook log error] {resp.status}')
                    print(await resp.text())
        except Exception as e:
            print(f'[webhook exception] {e}')

    async def _send_log_sync(self, record):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        await self._send_log(record)

    async def close(self):
        self._shutdown_event.set()
        if self.worker_task:
            await self.worker_task
        if self.session and not self.session.closed:
            await self.session.close()
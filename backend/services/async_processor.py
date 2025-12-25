# services/async_processor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_multiple_videos(urls):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = [
            loop.run_in_executor(executor, process_video, url)
            for url in urls
        ]
        return await asyncio.gather(*tasks)

import aiohttp
import asyncio
from datetime import datetime
from typing import Dict

class URLStatus:
    def __init__(self):
        self.status_cache = {}
        self.down_since = {}
    
    async def check_url(self, url: str, timeout: int = 30) -> Dict:
        try:
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    is_up = 200 <= response.status < 400
                    return {
                        'status': 'up' if is_up else 'down',
                        'status_code': response.status,
                        'response_time': round(response_time, 2),
                        'timestamp': datetime.now().isoformat(),
                        'error': None
                    }
        except asyncio.TimeoutError:
            return {
                'status': 'down',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': 'Timeout'
            }
        except Exception as e:
            return {
                'status': 'down',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)[:50]
            }
    
    def get_last_status(self, user_id: int, url: str) -> Dict:
        cache_key = f"{user_id}:{url}"
        return self.status_cache.get(cache_key, {'status': 'unknown'})
    
    def update_status(self, user_id: int, url: str, status: Dict):
        cache_key = f"{user_id}:{url}"
        old_status = self.status_cache.get(cache_key, {})
        if status['status'] == 'down' and old_status.get('status') != 'down':
            self.down_since[f"{user_id}:{url}"] = datetime.now()
        elif status['status'] == 'up':
            self.down_since.pop(f"{user_id}:{url}", None)
        self.status_cache[cache_key] = status
        return old_status.get('status')
    
    def get_downtime(self, user_id: int, url: str) -> str:
        key = f"{user_id}:{url}"
        if key in self.down_since:
            elapsed = datetime.now() - self.down_since[key]
            minutes = int(elapsed.total_seconds() / 60)
            seconds = int(elapsed.total_seconds() % 60)
            return f"{minutes}m {seconds}s"
        return "N/A"

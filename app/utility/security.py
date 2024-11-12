from functools import wraps
import random
import time


def constant_time_with_random_delay(min_delay: float, max_delay: float):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time

            random_delay = random.uniform(min_delay, max_delay)
            remaining_time = random_delay + elapsed_time

            time.sleep(remaining_time + random_delay)

            return result

        return wrapper

    return decorator

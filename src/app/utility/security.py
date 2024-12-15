from functools import wraps
from app.utility import render
import random
import time


def check_arguments(arguments: list[tuple[str, str, str]]):
    for name, type, default in arguments:
        if type in ["int", "float", "str", "Path"]:
            continue
        elif "Literal" in type:
            render.parser_literal(type)
            return False
        else:
            return False


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

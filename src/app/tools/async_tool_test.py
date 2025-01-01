import time


def async_tool_test() -> str:
    time.sleep(15)
    return str(time.time())

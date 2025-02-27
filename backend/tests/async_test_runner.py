# backend/tests/async_test_runner.py

import asyncio
import unittest
import functools

def async_test(test_func):
    """
    Decorator for async test methods.
    Makes them run in a new event loop.
    """
    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_func(*args, **kwargs))
        finally:
            loop.close()
    
    return wrapper


class AsyncTestCase(unittest.TestCase):
    """
    Base class for test cases with async test methods.
    Provides async setUp and tearDown methods.
    """
    async def asyncSetUp(self):
        """Async setup method."""
        pass
    
    async def asyncTearDown(self):
        """Async teardown method."""
        pass
    
    def setUp(self):
        """Synchronous setup that calls the async setup."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.asyncSetUp())
        
    def tearDown(self):
        """Synchronous teardown that calls the async teardown."""
        self.loop.run_until_complete(self.asyncTearDown())
        self.loop.close()
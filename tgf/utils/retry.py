"""
Retry Utilities for TGF

Async retry decorator with exponential backoff and jitter.
"""

import asyncio
import random
import functools
from typing import Callable, Type, Tuple, Optional, Any
from tgf.utils.logger import get_logger


def retry_async(
    max_retries: int = 5,
    min_delay: float = 5.0,
    max_delay: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    logger_name: str = "tgf"
):
    """
    Async retry decorator with random delay between attempts.
    
    Args:
        max_retries: Maximum number of retry attempts
        min_delay: Minimum delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry (exception, attempt)
        logger_name: Logger name for logging retries
    
    Usage:
        @retry_async(max_retries=5, min_delay=5, max_delay=10)
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(logger_name)
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = random.uniform(min_delay, max_delay)
                        logger.warning(
                            f"Attempt {attempt}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed. Last error: {e}"
                        )
            
            # All retries exhausted, raise last exception
            raise last_exception
        
        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry logic with state tracking"""
    
    def __init__(
        self,
        max_retries: int = 5,
        min_delay: float = 5.0,
        max_delay: float = 10.0,
        logger_name: str = "tgf"
    ):
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.logger = get_logger(logger_name)
        self.attempt = 0
        self.last_error: Optional[Exception] = None
    
    def __iter__(self):
        return self
    
    def __next__(self) -> int:
        self.attempt += 1
        if self.attempt > self.max_retries:
            raise StopIteration
        return self.attempt
    
    async def handle_error(self, error: Exception) -> bool:
        """
        Handle an error and determine if retry should occur.
        
        Returns:
            True if should retry, False if max retries exceeded
        """
        self.last_error = error
        
        if self.attempt < self.max_retries:
            delay = random.uniform(self.min_delay, self.max_delay)
            self.logger.warning(
                f"Attempt {self.attempt}/{self.max_retries} failed: {error}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
            return True
        else:
            self.logger.error(
                f"All {self.max_retries} attempts failed. Last error: {error}"
            )
            return False
    
    def success(self) -> None:
        """Mark operation as successful to stop iteration"""
        self.attempt = self.max_retries + 1

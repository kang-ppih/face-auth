"""
TimeoutManager class for managing Lambda and AD connection timeouts

This module provides timeout management for:
- Lambda function execution (15 second limit)
- Active Directory connections (10 second limit)
- Remaining time tracking for early termination logic

Requirements: 4.2, 4.3
"""

import time
from typing import Optional


class TimeoutManager:
    """
    Manages timeouts for Lambda execution and AD connections.
    
    Tracks elapsed time from initialization and provides methods to check
    if operations are within their timeout limits.
    
    Constants:
        AD_TIMEOUT: Maximum time allowed for AD operations (10 seconds)
        LAMBDA_TIMEOUT: Maximum time allowed for Lambda execution (15 seconds)
    """
    
    AD_TIMEOUT = 10  # seconds
    LAMBDA_TIMEOUT = 15  # seconds
    
    def __init__(self, start_time: Optional[float] = None):
        """
        Initialize the timeout manager.
        
        Args:
            start_time: Optional start time in seconds since epoch.
                       If not provided, uses current time.
        """
        self.start_time = start_time if start_time is not None else time.time()
    
    def check_ad_timeout(self) -> bool:
        """
        Check if AD connection is within timeout limit.
        
        Returns:
            bool: True if within AD timeout limit (< 10 seconds), False otherwise
        """
        elapsed = time.time() - self.start_time
        return elapsed < self.AD_TIMEOUT
    
    def check_lambda_timeout(self) -> bool:
        """
        Check if Lambda execution is within timeout limit.
        
        Returns:
            bool: True if within Lambda timeout limit (< 15 seconds), False otherwise
        """
        elapsed = time.time() - self.start_time
        return elapsed < self.LAMBDA_TIMEOUT
    
    def get_remaining_time(self) -> float:
        """
        Get remaining time before Lambda timeout.
        
        Returns:
            float: Remaining time in seconds (0 if timeout exceeded)
        """
        elapsed = time.time() - self.start_time
        return max(0, self.LAMBDA_TIMEOUT - elapsed)
    
    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since initialization.
        
        Returns:
            float: Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def get_remaining_ad_time(self) -> float:
        """
        Get remaining time before AD timeout.
        
        Returns:
            float: Remaining time in seconds (0 if timeout exceeded)
        """
        elapsed = time.time() - self.start_time
        return max(0, self.AD_TIMEOUT - elapsed)
    
    def should_continue(self, buffer_seconds: float = 1.0) -> bool:
        """
        Check if there's enough time remaining to continue processing.
        
        This method provides early termination logic by checking if there's
        sufficient time remaining (with a safety buffer) to continue operations.
        
        Args:
            buffer_seconds: Safety buffer in seconds (default: 1.0)
        
        Returns:
            bool: True if there's enough time to continue, False otherwise
        """
        remaining = self.get_remaining_time()
        return remaining > buffer_seconds
    
    def reset(self):
        """
        Reset the timeout manager to current time.
        
        Useful for testing or when starting a new operation phase.
        """
        self.start_time = time.time()

"""
Unit tests for TimeoutManager class

Tests cover:
- Lambda 15 second timeout management
- AD 10 second timeout management
- Remaining time tracking
- Early termination logic
- Elapsed time calculation
- Edge cases (boundary values, timeout exceeded)

Requirements: 4.2, 4.3
"""

import pytest
import time
import sys
import os

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.timeout_manager import TimeoutManager


class TestTimeoutManager:
    """Test suite for TimeoutManager class"""
    
    # Test initialization and basic functionality
    
    def test_initialization_with_default_time(self):
        """Test TimeoutManager initializes with current time by default"""
        before = time.time()
        manager = TimeoutManager()
        after = time.time()
        
        assert before <= manager.start_time <= after
    
    def test_initialization_with_custom_time(self):
        """Test TimeoutManager can be initialized with custom start time"""
        custom_time = 1000.0
        manager = TimeoutManager(start_time=custom_time)
        
        assert manager.start_time == custom_time
    
    def test_timeout_constants(self):
        """Test timeout constants are set correctly"""
        assert TimeoutManager.AD_TIMEOUT == 10
        assert TimeoutManager.LAMBDA_TIMEOUT == 15
    
    # Test AD timeout checking (Requirement 4.2)
    
    def test_check_ad_timeout_within_limit(self):
        """Test check_ad_timeout returns True when within 10 second limit"""
        # Start time 5 seconds ago
        start_time = time.time() - 5.0
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_ad_timeout() is True
    
    def test_check_ad_timeout_at_boundary(self):
        """Test check_ad_timeout at exactly 10 seconds"""
        # Start time exactly 10 seconds ago
        start_time = time.time() - 10.0
        manager = TimeoutManager(start_time=start_time)
        
        # Should return False as elapsed >= AD_TIMEOUT
        assert manager.check_ad_timeout() is False
    
    def test_check_ad_timeout_exceeded(self):
        """Test check_ad_timeout returns False when 10 second limit exceeded"""
        # Start time 12 seconds ago
        start_time = time.time() - 12.0
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_ad_timeout() is False
    
    def test_check_ad_timeout_just_under_limit(self):
        """Test check_ad_timeout just under 10 second limit"""
        # Start time 9.9 seconds ago
        start_time = time.time() - 9.9
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_ad_timeout() is True
    
    # Test Lambda timeout checking (Requirement 4.3)
    
    def test_check_lambda_timeout_within_limit(self):
        """Test check_lambda_timeout returns True when within 15 second limit"""
        # Start time 10 seconds ago
        start_time = time.time() - 10.0
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_lambda_timeout() is True
    
    def test_check_lambda_timeout_at_boundary(self):
        """Test check_lambda_timeout at exactly 15 seconds"""
        # Start time exactly 15 seconds ago
        start_time = time.time() - 15.0
        manager = TimeoutManager(start_time=start_time)
        
        # Should return False as elapsed >= LAMBDA_TIMEOUT
        assert manager.check_lambda_timeout() is False
    
    def test_check_lambda_timeout_exceeded(self):
        """Test check_lambda_timeout returns False when 15 second limit exceeded"""
        # Start time 20 seconds ago
        start_time = time.time() - 20.0
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_lambda_timeout() is False
    
    def test_check_lambda_timeout_just_under_limit(self):
        """Test check_lambda_timeout just under 15 second limit"""
        # Start time 14.9 seconds ago
        start_time = time.time() - 14.9
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.check_lambda_timeout() is True
    
    # Test remaining time tracking
    
    def test_get_remaining_time_full(self):
        """Test get_remaining_time returns full time at start"""
        manager = TimeoutManager()
        remaining = manager.get_remaining_time()
        
        # Should be close to 15 seconds (allowing small time passage)
        assert 14.9 <= remaining <= 15.0
    
    def test_get_remaining_time_partial(self):
        """Test get_remaining_time returns correct partial time"""
        # Start time 5 seconds ago
        start_time = time.time() - 5.0
        manager = TimeoutManager(start_time=start_time)
        remaining = manager.get_remaining_time()
        
        # Should be approximately 10 seconds remaining
        assert 9.9 <= remaining <= 10.1
    
    def test_get_remaining_time_zero_when_exceeded(self):
        """Test get_remaining_time returns 0 when timeout exceeded"""
        # Start time 20 seconds ago
        start_time = time.time() - 20.0
        manager = TimeoutManager(start_time=start_time)
        remaining = manager.get_remaining_time()
        
        assert remaining == 0
    
    def test_get_remaining_time_at_boundary(self):
        """Test get_remaining_time at exactly timeout boundary"""
        # Start time exactly 15 seconds ago
        start_time = time.time() - 15.0
        manager = TimeoutManager(start_time=start_time)
        remaining = manager.get_remaining_time()
        
        # Should be 0 or very close to 0
        assert remaining <= 0.1
    
    # Test elapsed time calculation
    
    def test_get_elapsed_time_at_start(self):
        """Test get_elapsed_time returns near zero at start"""
        manager = TimeoutManager()
        elapsed = manager.get_elapsed_time()
        
        # Should be very small (just the time to execute the method)
        assert 0 <= elapsed <= 0.1
    
    def test_get_elapsed_time_after_delay(self):
        """Test get_elapsed_time returns correct elapsed time"""
        # Start time 7 seconds ago
        start_time = time.time() - 7.0
        manager = TimeoutManager(start_time=start_time)
        elapsed = manager.get_elapsed_time()
        
        # Should be approximately 7 seconds
        assert 6.9 <= elapsed <= 7.1
    
    # Test AD remaining time
    
    def test_get_remaining_ad_time_full(self):
        """Test get_remaining_ad_time returns full time at start"""
        manager = TimeoutManager()
        remaining = manager.get_remaining_ad_time()
        
        # Should be close to 10 seconds
        assert 9.9 <= remaining <= 10.0
    
    def test_get_remaining_ad_time_partial(self):
        """Test get_remaining_ad_time returns correct partial time"""
        # Start time 3 seconds ago
        start_time = time.time() - 3.0
        manager = TimeoutManager(start_time=start_time)
        remaining = manager.get_remaining_ad_time()
        
        # Should be approximately 7 seconds remaining
        assert 6.9 <= remaining <= 7.1
    
    def test_get_remaining_ad_time_zero_when_exceeded(self):
        """Test get_remaining_ad_time returns 0 when AD timeout exceeded"""
        # Start time 12 seconds ago
        start_time = time.time() - 12.0
        manager = TimeoutManager(start_time=start_time)
        remaining = manager.get_remaining_ad_time()
        
        assert remaining == 0
    
    # Test early termination logic
    
    def test_should_continue_with_sufficient_time(self):
        """Test should_continue returns True when sufficient time remains"""
        # Start time 5 seconds ago, 10 seconds remaining
        start_time = time.time() - 5.0
        manager = TimeoutManager(start_time=start_time)
        
        # With default 1 second buffer, should return True
        assert manager.should_continue() is True
    
    def test_should_continue_with_insufficient_time(self):
        """Test should_continue returns False when insufficient time remains"""
        # Start time 14.5 seconds ago, 0.5 seconds remaining
        start_time = time.time() - 14.5
        manager = TimeoutManager(start_time=start_time)
        
        # With default 1 second buffer, should return False
        assert manager.should_continue() is False
    
    def test_should_continue_with_custom_buffer(self):
        """Test should_continue with custom buffer value"""
        # Start time 12 seconds ago, 3 seconds remaining
        start_time = time.time() - 12.0
        manager = TimeoutManager(start_time=start_time)
        
        # With 2 second buffer, should return True
        assert manager.should_continue(buffer_seconds=2.0) is True
        
        # With 4 second buffer, should return False
        assert manager.should_continue(buffer_seconds=4.0) is False
    
    def test_should_continue_at_boundary(self):
        """Test should_continue at exactly buffer boundary"""
        # Start time 14 seconds ago, 1 second remaining
        start_time = time.time() - 14.0
        manager = TimeoutManager(start_time=start_time)
        
        # With 1 second buffer, should return False (not > buffer)
        assert manager.should_continue(buffer_seconds=1.0) is False
    
    def test_should_continue_when_timeout_exceeded(self):
        """Test should_continue returns False when timeout exceeded"""
        # Start time 20 seconds ago
        start_time = time.time() - 20.0
        manager = TimeoutManager(start_time=start_time)
        
        assert manager.should_continue() is False
    
    # Test reset functionality
    
    def test_reset_updates_start_time(self):
        """Test reset updates start_time to current time"""
        # Start with old time
        old_time = time.time() - 10.0
        manager = TimeoutManager(start_time=old_time)
        
        assert manager.start_time == old_time
        
        # Reset
        before_reset = time.time()
        manager.reset()
        after_reset = time.time()
        
        # Start time should be updated to current time
        assert before_reset <= manager.start_time <= after_reset
        assert manager.start_time != old_time
    
    def test_reset_restores_full_timeout(self):
        """Test reset restores full timeout period"""
        # Start with time almost expired
        manager = TimeoutManager(start_time=time.time() - 14.0)
        
        # Should have little time remaining
        assert manager.get_remaining_time() < 2.0
        
        # Reset
        manager.reset()
        
        # Should have full time remaining
        remaining = manager.get_remaining_time()
        assert 14.9 <= remaining <= 15.0
    
    # Test real-time behavior
    
    def test_timeout_progresses_over_time(self):
        """Test that timeout checks reflect actual time passage"""
        manager = TimeoutManager()
        
        # Initially should be within timeout
        assert manager.check_lambda_timeout() is True
        
        initial_remaining = manager.get_remaining_time()
        
        # Wait a small amount of time
        time.sleep(0.1)
        
        # Remaining time should have decreased
        new_remaining = manager.get_remaining_time()
        assert new_remaining < initial_remaining
        
        # Should still be within timeout
        assert manager.check_lambda_timeout() is True
    
    # Test edge cases
    
    def test_zero_start_time(self):
        """Test TimeoutManager with start_time of 0 (epoch)"""
        manager = TimeoutManager(start_time=0)
        
        # Should be way past timeout
        assert manager.check_lambda_timeout() is False
        assert manager.check_ad_timeout() is False
        assert manager.get_remaining_time() == 0
    
    def test_future_start_time(self):
        """Test TimeoutManager with future start_time"""
        # Start time 5 seconds in the future
        future_time = time.time() + 5.0
        manager = TimeoutManager(start_time=future_time)
        
        # Should have more than 15 seconds remaining
        remaining = manager.get_remaining_time()
        assert remaining > 15.0
        
        # Should be within timeout
        assert manager.check_lambda_timeout() is True
    
    def test_multiple_timeout_checks(self):
        """Test multiple consecutive timeout checks"""
        manager = TimeoutManager()
        
        # Multiple checks should all work correctly
        for _ in range(5):
            assert manager.check_lambda_timeout() is True
            assert manager.check_ad_timeout() is True
            remaining = manager.get_remaining_time()
            assert remaining > 0
    
    # Integration test scenarios
    
    def test_ad_timeout_before_lambda_timeout(self):
        """Test that AD timeout occurs before Lambda timeout"""
        # Start time 11 seconds ago
        start_time = time.time() - 11.0
        manager = TimeoutManager(start_time=start_time)
        
        # AD should be timed out
        assert manager.check_ad_timeout() is False
        
        # But Lambda should still be within timeout
        assert manager.check_lambda_timeout() is True
    
    def test_typical_enrollment_flow_timing(self):
        """Test timeout manager in typical enrollment flow scenario"""
        manager = TimeoutManager()
        
        # Simulate OCR processing (2 seconds)
        time.sleep(0.05)  # Simulated delay
        assert manager.should_continue() is True
        
        # Check if we have time for AD verification (needs 10 seconds)
        assert manager.check_ad_timeout() is True
        
        # Simulate AD verification (3 seconds)
        time.sleep(0.05)  # Simulated delay
        assert manager.should_continue() is True
        
        # Check if we have time for face capture
        assert manager.check_lambda_timeout() is True
        remaining = manager.get_remaining_time()
        assert remaining > 5.0  # Should have plenty of time left
    
    def test_timeout_manager_with_buffer_for_cleanup(self):
        """Test using buffer to ensure time for cleanup operations"""
        # Start time 13 seconds ago, 2 seconds remaining
        start_time = time.time() - 13.0
        manager = TimeoutManager(start_time=start_time)
        
        # With 3 second buffer for cleanup, should not continue
        assert manager.should_continue(buffer_seconds=3.0) is False
        
        # But still within actual Lambda timeout
        assert manager.check_lambda_timeout() is True
        
        # This allows for graceful shutdown before hard timeout

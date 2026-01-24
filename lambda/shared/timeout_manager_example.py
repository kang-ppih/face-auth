"""
Example usage of TimeoutManager class

This module demonstrates how to use TimeoutManager in Lambda functions
to manage timeouts for AD connections and overall Lambda execution.
"""

import time
from timeout_manager import TimeoutManager


def example_enrollment_handler(event, context):
    """
    Example enrollment Lambda handler with timeout management.
    
    This demonstrates how to use TimeoutManager to:
    1. Track overall Lambda execution time (15s limit)
    2. Ensure AD operations complete within 10s
    3. Use early termination logic to prevent timeout errors
    """
    # Initialize timeout manager at the start of Lambda execution
    timeout_manager = TimeoutManager()
    
    try:
        # Step 1: OCR Processing (typically 1-2 seconds)
        print("Starting OCR processing...")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            return {
                'statusCode': 408,
                'body': 'Request timeout - insufficient time for processing'
            }
        
        # Simulate OCR processing
        time.sleep(0.5)
        print(f"OCR complete. Elapsed: {timeout_manager.get_elapsed_time():.2f}s")
        
        # Step 2: AD Verification (must complete within 10s)
        print("Starting AD verification...")
        if not timeout_manager.check_ad_timeout():
            return {
                'statusCode': 408,
                'body': 'AD verification timeout exceeded'
            }
        
        # Simulate AD verification
        time.sleep(1.0)
        print(f"AD verification complete. Elapsed: {timeout_manager.get_elapsed_time():.2f}s")
        print(f"Remaining AD time: {timeout_manager.get_remaining_ad_time():.2f}s")
        
        # Step 3: Face Capture (typically 2-3 seconds)
        print("Starting face capture...")
        if not timeout_manager.should_continue(buffer_seconds=3.0):
            return {
                'statusCode': 408,
                'body': 'Insufficient time for face capture'
            }
        
        # Simulate face capture
        time.sleep(1.0)
        print(f"Face capture complete. Elapsed: {timeout_manager.get_elapsed_time():.2f}s")
        
        # Step 4: Save to S3 and DynamoDB
        print("Saving enrollment data...")
        if not timeout_manager.should_continue(buffer_seconds=1.0):
            return {
                'statusCode': 408,
                'body': 'Insufficient time to save data'
            }
        
        # Simulate data saving
        time.sleep(0.5)
        print(f"Data saved. Elapsed: {timeout_manager.get_elapsed_time():.2f}s")
        print(f"Remaining Lambda time: {timeout_manager.get_remaining_time():.2f}s")
        
        return {
            'statusCode': 200,
            'body': 'Enrollment successful',
            'executionTime': timeout_manager.get_elapsed_time()
        }
        
    except Exception as e:
        print(f"Error occurred at {timeout_manager.get_elapsed_time():.2f}s: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Internal error: {str(e)}'
        }


def example_ad_connection_with_timeout():
    """
    Example of using TimeoutManager for AD connection operations.
    
    This shows how to pass remaining time to AD connector to ensure
    it respects the 10 second timeout limit.
    """
    timeout_manager = TimeoutManager()
    
    # Check if we have time for AD operation
    if not timeout_manager.check_ad_timeout():
        print("Cannot start AD operation - already past timeout")
        return False
    
    # Get remaining time for AD operation
    remaining_ad_time = timeout_manager.get_remaining_ad_time()
    print(f"Starting AD operation with {remaining_ad_time:.2f}s remaining")
    
    # Pass timeout to AD connector
    # ad_connector.connect(timeout=remaining_ad_time)
    
    # Simulate AD operation
    time.sleep(0.5)
    
    # Verify we're still within timeout
    if timeout_manager.check_ad_timeout():
        print(f"AD operation successful. Time used: {timeout_manager.get_elapsed_time():.2f}s")
        return True
    else:
        print("AD operation exceeded timeout")
        return False


def example_early_termination():
    """
    Example of using early termination logic to prevent timeout errors.
    
    This demonstrates how to check if there's enough time remaining
    before starting expensive operations.
    """
    timeout_manager = TimeoutManager()
    
    operations = [
        ("OCR Processing", 2.0),
        ("AD Verification", 3.0),
        ("Face Capture", 2.0),
        ("Rekognition Matching", 3.0),
        ("Save to S3", 1.0),
        ("Update DynamoDB", 1.0)
    ]
    
    for operation_name, estimated_time in operations:
        # Check if we have enough time (with buffer)
        if not timeout_manager.should_continue(buffer_seconds=estimated_time + 1.0):
            print(f"Skipping {operation_name} - insufficient time remaining")
            print(f"Remaining: {timeout_manager.get_remaining_time():.2f}s")
            return False
        
        print(f"Starting {operation_name} (estimated {estimated_time}s)...")
        time.sleep(estimated_time * 0.1)  # Simulate operation (faster for demo)
        print(f"  Completed. Elapsed: {timeout_manager.get_elapsed_time():.2f}s, "
              f"Remaining: {timeout_manager.get_remaining_time():.2f}s")
    
    return True


def example_timeout_monitoring():
    """
    Example of monitoring timeout status throughout execution.
    
    This shows how to log timeout information for debugging and monitoring.
    """
    timeout_manager = TimeoutManager()
    
    def log_timeout_status(stage: str):
        """Helper to log current timeout status"""
        print(f"\n[{stage}]")
        print(f"  Elapsed time: {timeout_manager.get_elapsed_time():.2f}s")
        print(f"  Remaining Lambda time: {timeout_manager.get_remaining_time():.2f}s")
        print(f"  Remaining AD time: {timeout_manager.get_remaining_ad_time():.2f}s")
        print(f"  Within AD timeout: {timeout_manager.check_ad_timeout()}")
        print(f"  Within Lambda timeout: {timeout_manager.check_lambda_timeout()}")
        print(f"  Should continue (1s buffer): {timeout_manager.should_continue(1.0)}")
    
    log_timeout_status("Start")
    
    # Simulate some processing
    time.sleep(0.5)
    log_timeout_status("After OCR")
    
    time.sleep(1.0)
    log_timeout_status("After AD Verification")
    
    time.sleep(0.5)
    log_timeout_status("After Face Capture")
    
    time.sleep(0.5)
    log_timeout_status("Before Completion")


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Enrollment Handler with Timeout Management")
    print("=" * 60)
    result = example_enrollment_handler({}, None)
    print(f"\nResult: {result}\n")
    
    print("=" * 60)
    print("Example 2: AD Connection with Timeout")
    print("=" * 60)
    success = example_ad_connection_with_timeout()
    print(f"\nSuccess: {success}\n")
    
    print("=" * 60)
    print("Example 3: Early Termination Logic")
    print("=" * 60)
    completed = example_early_termination()
    print(f"\nAll operations completed: {completed}\n")
    
    print("=" * 60)
    print("Example 4: Timeout Monitoring")
    print("=" * 60)
    example_timeout_monitoring()

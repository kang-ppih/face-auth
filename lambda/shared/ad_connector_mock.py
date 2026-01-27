"""
Face-Auth IdP System - Mock Active Directory Connector

This module provides a mock AD connector for testing and development when
actual AD connection is not available. It simulates AD verification using
only the employee_id extracted from the ID card.

⚠️ WARNING: This is for DEVELOPMENT/TESTING ONLY
Do NOT use in production environment!

Requirements: 1.3, 3.4, 4.2
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
import time

from .models import EmployeeInfo, ErrorCodes

logger = logging.getLogger(__name__)


class ADVerificationResult:
    """
    Result of Active Directory verification operation
    
    Attributes:
        success: Whether verification was successful
        reason: Reason code for failure (if applicable)
        employee_data: Employee data from AD (if successful)
        error: Detailed error message (if applicable)
        elapsed_time: Time taken for the operation in seconds
    """
    def __init__(
        self,
        success: bool,
        reason: Optional[str] = None,
        employee_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        elapsed_time: float = 0.0
    ):
        self.success = success
        self.reason = reason
        self.employee_data = employee_data
        self.error = error
        self.elapsed_time = elapsed_time


class MockADConnector:
    """
    Mock Active Directory connector for development/testing
    
    This mock connector:
    - Accepts any employee_id as valid
    - Simulates AD verification without actual LDAP connection
    - Returns mock employee data based on employee_id
    - Simulates realistic response times
    - Useful for testing when AD connection is not available
    
    ⚠️ WARNING: For DEVELOPMENT/TESTING ONLY!
    """
    
    # Mock employee database (for demonstration)
    # In real scenario, this would be replaced with actual AD
    MOCK_EMPLOYEES = {
        "123456": {
            "employee_id": "123456",
            "name": "山田太郎",
            "department": "開発部",
            "email": "yamada.taro@company.com",
            "title": "シニアエンジニア",
            "user_account_control": 512  # Normal account (enabled)
        },
        "789012": {
            "employee_id": "789012",
            "name": "佐藤花子",
            "department": "営業部",
            "email": "sato.hanako@company.com",
            "title": "営業マネージャー",
            "user_account_control": 512
        },
        "345678": {
            "employee_id": "345678",
            "name": "鈴木一郎",
            "department": "人事部",
            "email": "suzuki.ichiro@company.com",
            "title": "人事担当",
            "user_account_control": 512
        },
        # Disabled account for testing
        "999999": {
            "employee_id": "999999",
            "name": "無効アカウント",
            "department": "テスト部",
            "email": "disabled@company.com",
            "title": "テストユーザー",
            "user_account_control": 514  # Account disabled (512 + 2)
        }
    }
    
    def __init__(self, server_url: str = "mock://localhost", base_dn: str = "DC=mock,DC=com", timeout: int = 10):
        """
        Initialize Mock AD Connector
        
        Args:
            server_url: Mock server URL (ignored)
            base_dn: Mock base DN (ignored)
            timeout: Simulated timeout in seconds
        """
        self.server_url = server_url
        self.base_dn = base_dn
        self.timeout = timeout
        
        logger.warning("⚠️ Using MOCK AD Connector - FOR DEVELOPMENT/TESTING ONLY!")

    def _is_account_disabled(self, user_account_control: int) -> bool:
        """
        Check if AD account is disabled based on userAccountControl flags
        
        Args:
            user_account_control: userAccountControl attribute value
            
        Returns:
            True if account is disabled, False otherwise
        """
        # ADS_UF_ACCOUNTDISABLE flag is 0x0002 (bit 2)
        ACCOUNT_DISABLED_FLAG = 0x0002
        return bool(user_account_control & ACCOUNT_DISABLED_FLAG)

    def verify_employee(
        self, 
        employee_id: str, 
        extracted_info: EmployeeInfo
    ) -> ADVerificationResult:
        """
        Mock employee verification
        
        This method simulates AD verification by:
        - Accepting any 6-digit employee_id as valid
        - Returning mock employee data
        - Simulating realistic response times
        
        Args:
            employee_id: Employee ID to verify
            extracted_info: Employee information extracted from ID card
            
        Returns:
            ADVerificationResult with success status and mock data
            
        Requirements: 1.3, 1.7, 1.8
        """
        start_time = time.time()
        
        # Simulate network delay (50-200ms)
        import random
        time.sleep(random.uniform(0.05, 0.2))
        
        logger.info(f"[MOCK] Verifying employee: {employee_id}")
        
        # Validate employee_id format (6 digits)
        if not employee_id or len(employee_id) != 6 or not employee_id.isdigit():
            elapsed_time = time.time() - start_time
            logger.warning(f"[MOCK] Invalid employee_id format: {employee_id}")
            return ADVerificationResult(
                success=False,
                reason=ErrorCodes.REGISTRATION_INFO_MISMATCH,
                error="Invalid employee_id format (must be 6 digits)",
                elapsed_time=elapsed_time
            )
        
        # Check if employee exists in mock database
        if employee_id in self.MOCK_EMPLOYEES:
            ad_data = self.MOCK_EMPLOYEES[employee_id].copy()
        else:
            # For any other 6-digit employee_id, create mock data
            ad_data = {
                'employee_id': employee_id,
                'name': extracted_info.name or f"社員{employee_id}",
                'department': extracted_info.department or "未設定",
                'email': f"employee{employee_id}@company.com",
                'title': "社員",
                'user_account_control': 512  # Normal account (enabled)
            }
            logger.info(f"[MOCK] Created mock data for employee: {employee_id}")
        
        # Check if account is disabled
        user_account_control = ad_data['user_account_control']
        if self._is_account_disabled(user_account_control):
            elapsed_time = time.time() - start_time
            logger.warning(f"[MOCK] Account is disabled: {employee_id}")
            return ADVerificationResult(
                success=False,
                reason=ErrorCodes.ACCOUNT_DISABLED,
                error="AD account is disabled",
                elapsed_time=elapsed_time
            )
        
        elapsed_time = time.time() - start_time
        
        logger.info(f"[MOCK] Employee verification successful: {employee_id} in {elapsed_time:.2f}s")
        
        return ADVerificationResult(
            success=True,
            employee_data=ad_data,
            elapsed_time=elapsed_time
        )

    def authenticate_password(
        self, 
        employee_id: str, 
        password: str
    ) -> ADVerificationResult:
        """
        Mock password authentication
        
        This method simulates AD password authentication by:
        - Accepting any non-empty password as valid
        - Checking if employee exists
        - Simulating realistic response times
        
        Args:
            employee_id: Employee ID
            password: Employee password
            
        Returns:
            ADVerificationResult with authentication status
            
        Requirements: 3.4, 4.2
        """
        start_time = time.time()
        
        # Simulate network delay (100-300ms)
        import random
        time.sleep(random.uniform(0.1, 0.3))
        
        logger.info(f"[MOCK] Authenticating employee: {employee_id}")
        
        # Validate employee_id format
        if not employee_id or len(employee_id) != 6 or not employee_id.isdigit():
            elapsed_time = time.time() - start_time
            logger.warning(f"[MOCK] Invalid employee_id format: {employee_id}")
            return ADVerificationResult(
                success=False,
                reason=ErrorCodes.REGISTRATION_INFO_MISMATCH,
                error="Invalid employee_id format",
                elapsed_time=elapsed_time
            )
        
        # Check if password is provided
        if not password or len(password) < 1:
            elapsed_time = time.time() - start_time
            logger.warning(f"[MOCK] Empty password provided for: {employee_id}")
            return ADVerificationResult(
                success=False,
                reason=ErrorCodes.REGISTRATION_INFO_MISMATCH,
                error="Invalid credentials",
                elapsed_time=elapsed_time
            )
        
        # Check if employee exists in mock database
        if employee_id in self.MOCK_EMPLOYEES:
            ad_data = self.MOCK_EMPLOYEES[employee_id]
            
            # Check if account is disabled
            if self._is_account_disabled(ad_data['user_account_control']):
                elapsed_time = time.time() - start_time
                logger.warning(f"[MOCK] Cannot authenticate disabled account: {employee_id}")
                return ADVerificationResult(
                    success=False,
                    reason=ErrorCodes.ACCOUNT_DISABLED,
                    error="AD account is disabled",
                    elapsed_time=elapsed_time
                )
        
        # Mock: Accept any non-empty password as valid
        elapsed_time = time.time() - start_time
        
        logger.info(f"[MOCK] Password authentication successful: {employee_id} in {elapsed_time:.2f}s")
        
        return ADVerificationResult(
            success=True,
            employee_data={'employee_id': employee_id, 'dn': f"CN={employee_id},DC=mock,DC=com"},
            elapsed_time=elapsed_time
        )

    def test_connection(self) -> tuple:
        """
        Mock connection test
        
        Returns:
            Tuple of (success, message)
        """
        logger.info("[MOCK] Testing connection (always succeeds)")
        return True, "[MOCK] Connection successful (mock mode)"


# Factory function to create appropriate AD connector
def create_ad_connector(
    use_mock: bool = None,
    server_url: str = None,
    base_dn: str = None,
    timeout: int = 10
) -> Any:
    """
    Factory function to create AD connector (real or mock)
    
    Args:
        use_mock: If True, use mock connector. If None, check environment variable
        server_url: AD server URL (for real connector)
        base_dn: Base DN (for real connector)
        timeout: Connection timeout in seconds
        
    Returns:
        ADConnector or MockADConnector instance
    """
    import os
    
    # Determine whether to use mock
    if use_mock is None:
        use_mock = os.getenv('USE_MOCK_AD', 'true').lower() == 'true'
    
    if use_mock:
        logger.warning("⚠️ Using MOCK AD Connector - FOR DEVELOPMENT/TESTING ONLY!")
        return MockADConnector(server_url or "mock://localhost", base_dn or "DC=mock,DC=com", timeout)
    else:
        # Import real AD connector
        from .ad_connector import ADConnector
        
        if not server_url:
            server_url = os.getenv('AD_SERVER_URL', 'ldaps://ad.company.com:636')
        if not base_dn:
            base_dn = os.getenv('AD_BASE_DN', 'DC=company,DC=com')
        
        logger.info(f"Using REAL AD Connector: {server_url}")
        return ADConnector(server_url, base_dn, timeout)

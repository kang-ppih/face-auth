"""
Face-Auth IdP System - Active Directory Connector Tests

Unit tests for the ADConnector class.
Tests cover employee verification, password authentication, timeout enforcement,
and error handling.

Requirements: 1.3, 3.4, 4.2
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime
import time

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.ad_connector import ADConnector, ADVerificationResult
from shared.models import EmployeeInfo, ErrorCodes


class TestADConnector:
    """Test cases for ADConnector class"""
    
    def setup_method(self, method):
        """Set up test fixtures"""
        self.server_url = "ldaps://test-ad.company.com"
        self.base_dn = "ou=employees,dc=company,dc=com"
        self.timeout = 10
        
        # Create mock ldap3 module
        mock_ldap3_module = Mock()
        mock_ldap3_module.Server = Mock()
        mock_ldap3_module.Connection = Mock()
        mock_ldap3_module.ALL = Mock()
        mock_ldap3_module.SUBTREE = Mock()
        
        # Create mock exceptions module
        mock_exceptions = Mock()
        mock_exceptions.LDAPException = Exception
        mock_exceptions.LDAPBindError = Exception
        mock_exceptions.LDAPSocketOpenError = Exception
        mock_exceptions.LDAPOperationResult = Mock()
        
        # Patch sys.modules before importing
        self.ldap3_patcher = patch.dict('sys.modules', {
            'ldap3': mock_ldap3_module,
            'ldap3.core': Mock(),
            'ldap3.core.exceptions': mock_exceptions
        })
        self.ldap3_patcher.start()
        
        # Now create the connector - it will use the mocked ldap3
        self.connector = ADConnector(
            server_url=self.server_url,
            base_dn=self.base_dn,
            timeout=self.timeout
        )
    
    def teardown_method(self, method):
        """Clean up after tests"""
        if hasattr(self, 'ldap3_patcher'):
            self.ldap3_patcher.stop()
    
    def test_initialization(self):
        """Test ADConnector initialization"""
        assert self.connector.server_url == self.server_url
        assert self.connector.base_dn == self.base_dn
        assert self.connector.timeout == 10
        assert self.connector.use_ssl is True
    
    def test_initialization_without_ssl(self):
        """Test ADConnector initialization with non-SSL URL"""
        # Create mock ldap3 module
        mock_ldap3_module = Mock()
        mock_ldap3_module.Server = Mock()
        mock_ldap3_module.Connection = Mock()
        mock_ldap3_module.ALL = Mock()
        mock_ldap3_module.SUBTREE = Mock()
        
        # Create mock exceptions module
        mock_exceptions = Mock()
        mock_exceptions.LDAPException = Exception
        mock_exceptions.LDAPBindError = Exception
        mock_exceptions.LDAPSocketOpenError = Exception
        mock_exceptions.LDAPOperationResult = Mock()
        
        with patch.dict('sys.modules', {
            'ldap3': mock_ldap3_module,
            'ldap3.core': Mock(),
            'ldap3.core.exceptions': mock_exceptions
        }):
            connector = ADConnector(
                server_url="ldap://test-ad.company.com",
                base_dn=self.base_dn
            )
            assert connector.use_ssl is False
    
    def test_is_account_disabled_flag_set(self):
        """Test account disabled detection when flag is set"""
        # userAccountControl with ACCOUNTDISABLE flag (0x0002)
        disabled_uac = 0x0202  # 514 in decimal (normal account + disabled)
        assert self.connector._is_account_disabled(disabled_uac) is True
    
    def test_is_account_disabled_flag_not_set(self):
        """Test account disabled detection when flag is not set"""
        # userAccountControl without ACCOUNTDISABLE flag
        enabled_uac = 0x0200  # 512 in decimal (normal account, enabled)
        assert self.connector._is_account_disabled(enabled_uac) is False
    
    def test_verify_employee_success(self):
        """Test successful employee verification"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # Mock AD entry
        mock_entry = Mock()
        mock_entry.employeeID.value = "123456"
        mock_entry.displayName.value = "김철수"
        mock_entry.cn.value = "김철수"
        mock_entry.department.value = "개발팀"
        mock_entry.userAccountControl.value = 512  # Enabled account
        mock_entry.mail.value = "kim@company.com"
        mock_entry.title.value = "개발자"
        
        mock_conn.search.return_value = True
        mock_conn.entries = [mock_entry]
        
        # Create employee info
        employee_info = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("123456", employee_info)
        
        # Assertions
        assert result.success is True
        assert result.employee_data is not None
        assert result.employee_data['employee_id'] == "123456"
        assert result.employee_data['name'] == "김철수"
        assert result.employee_data['department'] == "개발팀"
        assert result.elapsed_time < self.timeout
        
        # Verify LDAP operations
        mock_conn.search.assert_called_once()
        mock_conn.unbind.assert_called_once()
    
    def test_verify_employee_not_found(self):
        """Test employee verification when employee not found in AD"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # No entries found
        mock_conn.search.return_value = False
        mock_conn.entries = []
        
        employee_info = EmployeeInfo(
            employee_id="999999",
            name="존재하지않음",
            department="없음",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("999999", employee_info)
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.REGISTRATION_INFO_MISMATCH
        assert "not found" in result.error.lower()
    
    def test_verify_employee_account_disabled(self):
        """Test employee verification when AD account is disabled"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # Mock disabled AD entry
        mock_entry = Mock()
        mock_entry.employeeID.value = "123456"
        mock_entry.displayName.value = "김철수"
        mock_entry.cn.value = "김철수"
        mock_entry.department.value = "개발팀"
        mock_entry.userAccountControl.value = 514  # Disabled account (512 + 2)
        mock_entry.mail.value = "kim@company.com"
        mock_entry.title.value = "개발자"
        
        mock_conn.search.return_value = True
        mock_conn.entries = [mock_entry]
        
        employee_info = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("123456", employee_info)
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.ACCOUNT_DISABLED
        assert "disabled" in result.error.lower()
    
    def test_verify_employee_id_mismatch(self):
        """Test employee verification when employee ID doesn't match"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # Mock AD entry with different employee ID
        mock_entry = Mock()
        mock_entry.employeeID.value = "654321"  # Different ID
        mock_entry.displayName.value = "김철수"
        mock_entry.cn.value = "김철수"
        mock_entry.department.value = "개발팀"
        mock_entry.userAccountControl.value = 512
        mock_entry.mail.value = "kim@company.com"
        mock_entry.title.value = "개발자"
        
        mock_conn.search.return_value = True
        mock_conn.entries = [mock_entry]
        
        employee_info = EmployeeInfo(
            employee_id="123456",  # Different from AD
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("123456", employee_info)
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.REGISTRATION_INFO_MISMATCH
        assert "mismatch" in result.error.lower()
    
    def test_verify_employee_timeout(self):
        """Test employee verification timeout enforcement"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # Simulate slow search that exceeds timeout
        def slow_search(*args, **kwargs):
            time.sleep(0.1)  # Simulate delay
            return True
        
        mock_conn.search.side_effect = slow_search
        mock_conn.entries = []
        
        # Temporarily reduce timeout for testing
        original_timeout = self.connector.timeout
        self.connector.timeout = 0.05  # 50ms timeout
        
        employee_info = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("123456", employee_info)
        
        # Restore timeout
        self.connector.timeout = original_timeout
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.AD_CONNECTION_ERROR
        assert "timeout" in result.error.lower()
        assert result.elapsed_time >= 0.05
    
    def test_verify_employee_connection_error(self):
        """Test employee verification with connection error"""
        # Setup mocks to raise exception
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Simulate connection error using the connector's exception class
        self.connector.Connection = Mock(side_effect=self.connector.LDAPSocketOpenError("Connection refused"))
        
        employee_info = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        # Verify employee
        result = self.connector.verify_employee("123456", employee_info)
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.AD_CONNECTION_ERROR
        assert "connect" in result.error.lower()
    
    def test_authenticate_password_success(self):
        """Test successful password authentication"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Mock search connection
        mock_search_conn = Mock()
        mock_entry = Mock()
        mock_entry.distinguishedName.value = "cn=123456,ou=employees,dc=company,dc=com"
        mock_entry.userAccountControl.value = 512  # Enabled
        mock_search_conn.search.return_value = True
        mock_search_conn.entries = [mock_entry]
        
        # Mock auth connection
        mock_auth_conn = Mock()
        mock_auth_conn.bind.return_value = True
        
        # Return different connections for search and auth
        self.connector.Connection = Mock(side_effect=[mock_search_conn, mock_auth_conn])
        
        # Authenticate
        result = self.connector.authenticate_password("123456", "correct_password")
        
        # Assertions
        assert result.success is True
        assert result.employee_data is not None
        assert result.employee_data['employee_id'] == "123456"
        assert result.elapsed_time < self.timeout
        
        # Verify operations
        mock_search_conn.search.assert_called_once()
        mock_search_conn.unbind.assert_called_once()
        mock_auth_conn.bind.assert_called_once()
        mock_auth_conn.unbind.assert_called_once()
    
    def test_authenticate_password_invalid_credentials(self):
        """Test password authentication with invalid credentials"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Mock search connection
        mock_search_conn = Mock()
        mock_entry = Mock()
        mock_entry.distinguishedName.value = "cn=123456,ou=employees,dc=company,dc=com"
        mock_entry.userAccountControl.value = 512
        mock_search_conn.search.return_value = True
        mock_search_conn.entries = [mock_entry]
        
        # Mock auth connection with failed bind
        mock_auth_conn = Mock()
        mock_auth_conn.bind.return_value = False
        
        self.connector.Connection = Mock(side_effect=[mock_search_conn, mock_auth_conn])
        
        # Authenticate
        result = self.connector.authenticate_password("123456", "wrong_password")
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.REGISTRATION_INFO_MISMATCH
        assert "credentials" in result.error.lower()
    
    def test_authenticate_password_employee_not_found(self):
        """Test password authentication when employee not found"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Mock search connection with no results
        mock_search_conn = Mock()
        mock_search_conn.search.return_value = False
        mock_search_conn.entries = []
        
        self.connector.Connection = Mock(return_value=mock_search_conn)
        
        # Authenticate
        result = self.connector.authenticate_password("999999", "password")
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.REGISTRATION_INFO_MISMATCH
        assert "not found" in result.error.lower()
    
    def test_authenticate_password_account_disabled(self):
        """Test password authentication with disabled account"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Mock search connection with disabled account
        mock_search_conn = Mock()
        mock_entry = Mock()
        mock_entry.distinguishedName.value = "cn=123456,ou=employees,dc=company,dc=com"
        mock_entry.userAccountControl.value = 514  # Disabled
        mock_search_conn.search.return_value = True
        mock_search_conn.entries = [mock_entry]
        
        self.connector.Connection = Mock(return_value=mock_search_conn)
        
        # Authenticate
        result = self.connector.authenticate_password("123456", "password")
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.ACCOUNT_DISABLED
        assert "disabled" in result.error.lower()
    
    def test_authenticate_password_timeout(self):
        """Test password authentication timeout enforcement"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Mock search connection with slow search
        mock_search_conn = Mock()
        
        def slow_search(*args, **kwargs):
            time.sleep(0.1)
            return True
        
        mock_entry = Mock()
        mock_entry.distinguishedName.value = "cn=123456,ou=employees,dc=company,dc=com"
        mock_entry.userAccountControl.value = 512
        
        mock_search_conn.search.side_effect = slow_search
        mock_search_conn.entries = [mock_entry]
        
        self.connector.Connection = Mock(return_value=mock_search_conn)
        
        # Temporarily reduce timeout
        original_timeout = self.connector.timeout
        self.connector.timeout = 0.05
        
        # Authenticate
        result = self.connector.authenticate_password("123456", "password")
        
        # Restore timeout
        self.connector.timeout = original_timeout
        
        # Assertions
        assert result.success is False
        assert result.reason == ErrorCodes.AD_CONNECTION_ERROR
        assert "timeout" in result.error.lower()
    
    def test_test_connection_success(self):
        """Test successful connection test"""
        # Setup mocks
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        mock_conn = Mock()
        self.connector.Connection = Mock(return_value=mock_conn)
        
        # Test connection
        success, message = self.connector.test_connection()
        
        # Assertions
        assert success is True
        assert "successful" in message.lower()
        mock_conn.unbind.assert_called_once()
    
    def test_test_connection_failure(self):
        """Test connection test failure"""
        # Setup mocks to raise exception
        mock_server = Mock()
        self.connector.Server = Mock(return_value=mock_server)
        
        # Use the connector's exception class
        self.connector.Connection = Mock(side_effect=self.connector.LDAPSocketOpenError("Connection refused"))
        
        # Test connection
        success, message = self.connector.test_connection()
        
        # Assertions
        assert success is False
        assert "failed" in message.lower()


class TestADVerificationResult:
    """Test cases for ADVerificationResult dataclass"""
    
    def test_successful_result(self):
        """Test creation of successful verification result"""
        result = ADVerificationResult(
            success=True,
            employee_data={'employee_id': '123456', 'name': '김철수'},
            elapsed_time=0.5
        )
        
        assert result.success is True
        assert result.reason is None
        assert result.employee_data is not None
        assert result.error is None
        assert result.elapsed_time == 0.5
    
    def test_failed_result(self):
        """Test creation of failed verification result"""
        result = ADVerificationResult(
            success=False,
            reason=ErrorCodes.ACCOUNT_DISABLED,
            error="Account is disabled",
            elapsed_time=0.3
        )
        
        assert result.success is False
        assert result.reason == ErrorCodes.ACCOUNT_DISABLED
        assert result.employee_data is None
        assert result.error == "Account is disabled"
        assert result.elapsed_time == 0.3


class TestADConnectorIntegration:
    """Integration tests for ADConnector (require mock AD server or test environment)"""
    
    @pytest.mark.skip(reason="Requires actual AD server or comprehensive mock")
    def test_full_verification_flow(self):
        """Test complete verification flow with real AD connection"""
        # This would require a test AD server or comprehensive mock
        pass
    
    @pytest.mark.skip(reason="Requires actual AD server or comprehensive mock")
    def test_full_authentication_flow(self):
        """Test complete authentication flow with real AD connection"""
        # This would require a test AD server or comprehensive mock
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

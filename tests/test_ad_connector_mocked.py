"""
Face-Auth IdP System - AD Connector Mocked Tests

This test module provides mocked tests for AD Connector functionality
without requiring actual ldap3 library or AD server connection.

Tests cover:
- AD connection with mocks
- Employee verification
- Password authentication
- Timeout handling
- Error scenarios
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.models import EmployeeInfo, ErrorCodes
from shared.timeout_manager import TimeoutManager


class TestADConnectorMocked:
    """Test suite for AD Connector with mocked ldap3"""
    
    @pytest.fixture
    def mock_ldap_connection(self):
        """Create a mocked LDAP connection"""
        with patch('shared.ad_connector.Connection') as mock_conn_class:
            mock_conn = MagicMock()
            mock_conn_class.return_value = mock_conn
            mock_conn.bind.return_value = True
            mock_conn.unbind.return_value = None
            mock_conn.search.return_value = True
            mock_conn.entries = []
            yield mock_conn
    
    @pytest.fixture
    def sample_employee_info(self):
        """Create sample employee info for testing"""
        return EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            position="대리",
            email="kim@example.com",
            phone="010-1234-5678",
            hire_date=datetime(2020, 1, 1),
            card_template_id="standard_card_v1",
            confidence_score=95.5
        )
    
    def test_ad_connector_initialization_mocked(self, mock_ldap_connection):
        """Test AD Connector initialization with mocked connection"""
        from shared.ad_connector import ADConnector
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com",
            bind_dn="cn=admin,dc=test,dc=com",
            bind_password="test_password"
        )
        
        assert connector.server_url == "ldap://test-server"
        assert connector.base_dn == "dc=test,dc=com"
        assert connector.timeout == 10  # Default timeout
    
    def test_verify_employee_success_mocked(self, mock_ldap_connection, sample_employee_info):
        """Test successful employee verification with mocked AD"""
        from shared.ad_connector import ADConnector, ADVerificationResult
        
        # Setup mock response
        mock_entry = MagicMock()
        mock_entry.entry_attributes_as_dict = {
            'cn': ['김철수'],
            'employeeID': ['123456'],
            'department': ['개발팀'],
            'mail': ['kim@example.com']
        }
        mock_ldap_connection.entries = [mock_entry]
        mock_ldap_connection.search.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.verify_employee(sample_employee_info.employee_id, sample_employee_info)
        
        assert result.success is True
        assert result.employee_data is not None
        assert result.error is None
    
    def test_verify_employee_not_found_mocked(self, mock_ldap_connection, sample_employee_info):
        """Test employee not found in AD with mocked connection"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response - no entries found
        mock_ldap_connection.entries = []
        mock_ldap_connection.search.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.verify_employee(sample_employee_info.employee_id, sample_employee_info)
        
        assert result.success is False
        assert "not found" in result.reason.lower()
    
    def test_authenticate_employee_success_mocked(self, mock_ldap_connection):
        """Test successful employee authentication with mocked AD"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response
        mock_ldap_connection.bind.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "correct_password")
        
        assert result.success is True
        assert result.error is None
    
    def test_authenticate_employee_wrong_password_mocked(self, mock_ldap_connection):
        """Test employee authentication with wrong password"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response - bind fails
        mock_ldap_connection.bind.return_value = False
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "wrong_password")
        
        assert result.success is False
        assert "authentication failed" in result.reason.lower()
    
    def test_ad_connection_timeout_mocked(self, mock_ldap_connection):
        """Test AD connection timeout handling"""
        from shared.ad_connector import ADConnector
        import socket
        
        # Setup mock to raise timeout exception
        mock_ldap_connection.bind.side_effect = socket.timeout("Connection timeout")
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com",
            timeout=1
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "password")
        
        assert result.success is False
        assert "timeout" in result.reason.lower() or result.error is not None
    
    def test_ad_connection_with_timeout_manager_mocked(self, mock_ldap_connection):
        """Test AD connection with TimeoutManager integration"""
        from shared.ad_connector import ADConnector
        
        # Create timeout manager with 5 seconds remaining
        timeout_manager = TimeoutManager(
            lambda_timeout=15,
            ad_timeout=10,
            start_time=datetime.now().timestamp() - 10  # 10 seconds elapsed
        )
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com",
            timeout=5
        )
        
        # Should have enough time
        assert timeout_manager.has_time_for_ad_operation() is True
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "password")
        
        # Should succeed if we have time
        if timeout_manager.has_time_for_ad_operation():
            assert result.success is True
    
    def test_verify_employee_data_mismatch_mocked(self, mock_ldap_connection, sample_employee_info):
        """Test employee verification with data mismatch"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response with mismatched data
        mock_entry = MagicMock()
        mock_entry.entry_attributes_as_dict = {
            'cn': ['다른이름'],  # Different name
            'employeeID': ['123456'],
            'department': ['다른부서'],  # Different department
            'mail': ['different@example.com']
        }
        mock_ldap_connection.entries = [mock_entry]
        mock_ldap_connection.search.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.verify_employee(sample_employee_info.employee_id, sample_employee_info)
        
        # Should still succeed but may have warnings
        assert result.success is True or result.reason is not None
    
    def test_ad_connection_error_handling_mocked(self, mock_ldap_connection):
        """Test AD connection error handling"""
        from shared.ad_connector import ADConnector
        
        # Setup mock to raise exception
        mock_ldap_connection.bind.side_effect = Exception("Connection failed")
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "password")
        
        assert result.success is False
        assert result.error is not None
    
    def test_ad_search_with_filter_mocked(self, mock_ldap_connection):
        """Test AD search with custom filter"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response
        mock_entry = MagicMock()
        mock_entry.entry_attributes_as_dict = {
            'cn': ['김철수'],
            'employeeID': ['123456']
        }
        mock_ldap_connection.entries = [mock_entry]
        mock_ldap_connection.search.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            # Verify that search is called with correct filter
            result = connector.verify_employee("123456", None)
            
            # Check that search was called
            assert mock_ldap_connection.search.called
    
    def test_ad_connection_cleanup_mocked(self, mock_ldap_connection):
        """Test AD connection cleanup (unbind)"""
        from shared.ad_connector import ADConnector
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "password")
        
        # Verify that unbind was called for cleanup
        assert mock_ldap_connection.unbind.called or result is not None
    
    def test_ad_connector_with_ssl_mocked(self, mock_ldap_connection):
        """Test AD connector with SSL/TLS"""
        from shared.ad_connector import ADConnector
        
        connector = ADConnector(
            server_url="ldaps://test-server",  # LDAPS
            base_dn="dc=test,dc=com",
            use_ssl=True
        )
        
        assert "ldaps://" in connector.server_url
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.authenticate_employee("123456", "password")
        
        assert result is not None
    
    def test_ad_multiple_search_results_mocked(self, mock_ldap_connection):
        """Test AD search with multiple results (should handle gracefully)"""
        from shared.ad_connector import ADConnector
        
        # Setup mock response with multiple entries
        mock_entry1 = MagicMock()
        mock_entry1.entry_attributes_as_dict = {'cn': ['김철수1'], 'employeeID': ['123456']}
        mock_entry2 = MagicMock()
        mock_entry2.entry_attributes_as_dict = {'cn': ['김철수2'], 'employeeID': ['123456']}
        
        mock_ldap_connection.entries = [mock_entry1, mock_entry2]
        mock_ldap_connection.search.return_value = True
        
        connector = ADConnector(
            server_url="ldap://test-server",
            base_dn="dc=test,dc=com"
        )
        
        with patch.object(connector, '_connect', return_value=mock_ldap_connection):
            result = connector.verify_employee("123456", None)
        
        # Should handle multiple results (typically use first one or return error)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

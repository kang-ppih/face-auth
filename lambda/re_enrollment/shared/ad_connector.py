"""
Face-Auth IdP System - Active Directory Connector

This module provides Active Directory integration for employee verification and authentication.
The service supports:
- Direct Connect-based secure connection to on-premises AD
- Employee information verification against AD records
- Password authentication for emergency login
- 10-second timeout enforcement for all AD operations
- Account status validation (enabled/disabled)

Requirements: 1.3, 3.4, 4.2
"""

import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
import time

from .models import EmployeeInfo, ErrorResponse, ErrorCodes

logger = logging.getLogger(__name__)


@dataclass
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
    success: bool
    reason: Optional[str] = None
    employee_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0


class ADConnector:
    """
    Active Directory connector for employee verification and authentication
    
    This service handles:
    - Secure LDAPS connection to on-premises AD via Direct Connect
    - Employee information verification against AD records
    - Password-based authentication for emergency login
    - Strict 10-second timeout enforcement
    - Account status validation
    """
    
    def __init__(self, server_url: str, base_dn: str, timeout: int = 10):
        """
        Initialize AD Connector
        
        Args:
            server_url: LDAPS URL for AD server (e.g., 'ldaps://ad.company.com')
            base_dn: Base Distinguished Name for employee searches
            timeout: Connection timeout in seconds (default: 10)
        """
        self.server_url = server_url
        self.base_dn = base_dn
        self.timeout = timeout
        self.use_ssl = server_url.startswith('ldaps://')
        
        # Import ldap3 library (will be included in Lambda layer)
        try:
            from ldap3 import Server, Connection, ALL, SUBTREE
            from ldap3.core.exceptions import (
                LDAPException, 
                LDAPBindError, 
                LDAPSocketOpenError,
                LDAPOperationResult
            )
            self.Server = Server
            self.Connection = Connection
            self.ALL = ALL
            self.SUBTREE = SUBTREE
            self.LDAPException = LDAPException
            self.LDAPBindError = LDAPBindError
            self.LDAPSocketOpenError = LDAPSocketOpenError
            self.LDAPOperationResult = LDAPOperationResult
        except ImportError as e:
            logger.error(f"Failed to import ldap3 library: {e}")
            raise ImportError("ldap3 library is required for AD operations")
    
    def _is_account_disabled(self, user_account_control: int) -> bool:
        """
        Check if AD account is disabled based on userAccountControl flags
        
        Args:
            user_account_control: userAccountControl attribute value from AD
            
        Returns:
            True if account is disabled, False otherwise
        """
        # ADS_UF_ACCOUNTDISABLE flag is 0x0002 (bit 2)
        ACCOUNT_DISABLED_FLAG = 0x0002
        return bool(user_account_control & ACCOUNT_DISABLED_FLAG)

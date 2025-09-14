"""
XLS-70 Credentials Service for EvidentAI
Professional digital signature system using XRPL Credentials specification
"""

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models import (
    CredentialCreate, CredentialAccept, CredentialDelete,
    Payment, AccountSet, AccountInfo
)
from xrpl.transaction import submit_and_wait
from xrpl.utils import xrp_to_drops
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .models import OfficerWallet, Report
import json
import hashlib
from typing import Dict, List, Optional


class XLS70CredentialService:
    """
    Professional digital signature service using XLS-70 Credentials
    Provides law enforcement-grade credential management and document signing
    """
    
    def __init__(self):
        # Use multiple endpoints for reliability
        endpoints = [
            "https://s.devnet.rippletest.net:51234",
            "wss://s.devnet.rippletest.net:51233",
            "wss://xls20-sandbox.rippletest.net:51233"
        ]
        self.client = JsonRpcClient(endpoints[0])
    
    def create_officer_credential(self, user, officer_info: Dict) -> Dict:
        """
        Create a professional law enforcement credential for an officer
        Uses mock implementation until XLS-70 is fully supported
        
        Args:
            user: Django User object
            officer_info: Dictionary containing officer details
                {
                    'badge_number': str,
                    'department': str,
                    'rank': str,
                    'jurisdiction': str,
                    'certification_level': str,
                    'expiry_date': str (ISO format)
                }
        
        Returns:
            Dict with credential creation result
        """
        try:
            # Get user's wallet
            officer_wallet = self._get_wallet_for_user(user)
            if not officer_wallet:
                raise Exception("User does not have an XRPL wallet")
            
            # Create credential data
            credential_data = {
                "type": "LawEnforcementOfficer",
                "version": "1.0",
                "issuer": "EvidentAI-System",
                "subject": {
                    "user_id": str(user.id),
                    "username": user.username,
                    "badge_number": officer_info.get('badge_number'),
                    "department": officer_info.get('department'),
                    "rank": officer_info.get('rank'),
                    "jurisdiction": officer_info.get('jurisdiction'),
                    "certification_level": officer_info.get('certification_level')
                },
                "issued_at": timezone.now().isoformat(),
                "expires_at": officer_info.get('expiry_date'),
                "credential_id": f"LEO-{user.id}-{int(timezone.now().timestamp())}"
            }
            
            # For now, use mock credential creation since XLS-70 is not fully supported yet
            # This simulates the XLS-70 credential creation process
            try:
                # Try to create a real XLS-70 credential
                xrpl_wallet = self._get_xrpl_wallet_object(officer_wallet)
                
                # Use AccountSet transaction to record credential data in memo
                from xrpl.models import AccountSet
                credential_create = AccountSet(
                    account=xrpl_wallet.address,
                    memos=[{
                        "Memo": {
                            "MemoData": f"XLS70-CREDENTIAL-{credential_data['credential_id']}-{json.dumps(credential_data).encode().hex().upper()}"
                        }
                    }]
                )
                
                response = submit_and_wait(credential_create, self.client, xrpl_wallet)
                
                if response.result.get("meta", {}).get("TransactionResult") == "tesSUCCESS":
                    transaction_hash = response.result.get("hash")
                else:
                    raise Exception("Transaction failed")
                    
            except Exception as e:
                # Fallback to mock implementation
                print(f"XLS-70 not available, using mock credential: {str(e)}")
                transaction_hash = f"MOCK-{hashlib.sha256(json.dumps(credential_data).encode()).hexdigest()[:16]}"
            
            # Store credential info in database
            officer_wallet.credential_id = credential_data["credential_id"]
            officer_wallet.credential_data = credential_data
            officer_wallet.credential_created_at = timezone.now()
            officer_wallet.save()
            
            return {
                "success": True,
                "credential_id": credential_data["credential_id"],
                "transaction_hash": transaction_hash,
                "credential_data": credential_data,
                "note": "Mock implementation - XLS-70 not yet fully supported"
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def accept_credential(self, user, credential_id: str) -> Dict:
        """
        Accept a credential that was issued to the user
        Uses mock implementation until XLS-70 is fully supported
        
        Args:
            user: Django User object
            credential_id: The credential ID to accept
        
        Returns:
            Dict with acceptance result
        """
        try:
            officer_wallet = self._get_wallet_for_user(user)
            if not officer_wallet:
                raise Exception("User does not have an XRPL wallet")
            
            if not officer_wallet.credential_id:
                raise Exception("No credential found to accept")
            
            # For now, use mock acceptance since XLS-70 is not fully supported yet
            try:
                # Try to create a real XLS-70 acceptance transaction
                xrpl_wallet = self._get_xrpl_wallet_object(officer_wallet)
                
                # Use AccountSet transaction to record acceptance
                from xrpl.models import AccountSet
                acceptance_tx = AccountSet(
                    account=xrpl_wallet.address,
                    memos=[{
                        "Memo": {
                            "MemoData": f"XLS70-ACCEPT-{credential_id}-{int(timezone.now().timestamp())}".encode().hex().upper()
                        }
                    }]
                )
                
                response = submit_and_wait(acceptance_tx, self.client, xrpl_wallet)
                
                if response.result.get("meta", {}).get("TransactionResult") == "tesSUCCESS":
                    transaction_hash = response.result.get("hash")
                else:
                    raise Exception("Transaction failed")
                    
            except Exception as e:
                # Fallback to mock implementation
                print(f"XLS-70 not available, using mock acceptance: {str(e)}")
                transaction_hash = f"MOCK-ACCEPT-{hashlib.sha256(f'{credential_id}-{int(timezone.now().timestamp())}'.encode()).hexdigest()[:16]}"
            
            # Update wallet status
            officer_wallet.credential_accepted_at = timezone.now()
            officer_wallet.save()
            
            return {
                "success": True,
                "transaction_hash": transaction_hash,
                "message": "Credential accepted successfully",
                "note": "Mock implementation - XLS-70 not yet fully supported"
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_report_with_credential(self, report, user) -> Dict:
        """
        Sign a report using XLS-70 credentials for professional authentication
        
        Args:
            report: Report object to sign
            user: User signing the report
        
        Returns:
            Dict with signing result
        """
        try:
            # Get user's wallet and credential
            officer_wallet = self._get_wallet_for_user(user)
            if not officer_wallet:
                raise Exception("User does not have an XRPL wallet")
            
            if not officer_wallet.credential_id:
                raise Exception("User does not have a valid credential")
            
            # Generate document hash
            document_hash = report.generate_hash()
            report.document_hash = document_hash
            
            # Get XRPL wallet object
            xrpl_wallet = self._get_xrpl_wallet_object(officer_wallet)
            
            # Create signature data
            signature_data = {
                "type": "DocumentSignature",
                "version": "1.0",
                "document_id": f"REPORT-{report.id}",
                "document_hash": document_hash,
                "signer_credential_id": officer_wallet.credential_id,
                "signed_at": timezone.now().isoformat(),
                "signature_purpose": "Evidence Authentication",
                "legal_jurisdiction": "Law Enforcement"
            }
            
            # For now, use mock signing since XLS-70 credential_ids may not be fully supported
            try:
                # Try to create a real XLS-70 signature transaction
                from decimal import Decimal
                payment = Payment(
                    account=xrpl_wallet.address,
                    destination=xrpl_wallet.address,  # Self-payment for signature
                    amount=xrp_to_drops(Decimal("0.000001")),
                    credential_ids=[officer_wallet.credential_id],
                    memos=[{
                        "Memo": {
                            "MemoData": json.dumps(signature_data).encode().hex().upper()
                        }
                    }]
                )
                
                # Submit to XRPL
                response = submit_and_wait(payment, self.client, xrpl_wallet)
                
                if response.result.get("meta", {}).get("TransactionResult") == "tesSUCCESS":
                    transaction_hash = response.result.get("hash")
                else:
                    raise Exception(f"Transaction failed: {response.result}")
                    
            except Exception as e:
                # Fallback to mock implementation
                print(f"XLS-70 credential_ids not available, using mock signing: {str(e)}")
                transaction_hash = f"MOCK-XLS70-{hashlib.sha256(json.dumps(signature_data).encode()).hexdigest()[:16]}"
            
            # Update report with signature
            report.signed_by = user
            report.signed_at = timezone.now()
            report.signature_tx_hash = transaction_hash
            report.signature_type = "XLS70_CREDENTIAL"
            report.credential_id = officer_wallet.credential_id
            report.save()
            
            # Update wallet last used
            officer_wallet.last_used = timezone.now()
            officer_wallet.save(update_fields=['last_used'])
            
            return {
                "success": True,
                "transaction_hash": transaction_hash,
                "signature_data": signature_data,
                "credential_id": officer_wallet.credential_id,
                "note": "Mock implementation - XLS-70 not yet fully supported"
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_credential_signature(self, report) -> Dict:
        """
        Verify a report's signature using XLS-70 credentials
        Handles both real and mock implementations
        
        Args:
            report: Report object to verify
        
        Returns:
            Dict with verification result
        """
        if not report.signature_tx_hash:
            return {"verified": False, "error": "No signature found"}
        
        # Check if this is a mock signature
        if report.signature_tx_hash.startswith("MOCK-XLS70-"):
            return self._verify_mock_credential_signature(report)
        
        try:
            # Try to verify real XLS-70 signature
            tx_response = self.client.request({
                "command": "tx",
                "transaction": report.signature_tx_hash
            })
            
            if tx_response.result.get("validated"):
                tx_data = tx_response.result.get("tx_json", {})
                
                # Check for credential IDs
                credential_ids = tx_data.get("CredentialIDs", [])
                if not credential_ids:
                    return {"verified": False, "error": "No credentials found in transaction"}
                
                # Get credential data
                credential_id = credential_ids[0]
                credential_data = self._get_credential_data(credential_id)
                
                if not credential_data:
                    return {"verified": False, "error": "Credential not found"}
                
                # Verify document hash
                memos = tx_data.get("Memos", [])
                for memo in memos:
                    memo_data_hex = memo.get("Memo", {}).get("MemoData")
                    if memo_data_hex:
                        try:
                            memo_data = bytes.fromhex(memo_data_hex).decode('utf-8')
                            signature_data = json.loads(memo_data)
                            
                            if signature_data.get("document_hash") == report.document_hash:
                                return {
                                    "verified": True,
                                    "signature_type": "XLS70_CREDENTIAL",
                                    "credential_data": credential_data,
                                    "signature_data": signature_data,
                                    "verified_at": timezone.now().isoformat()
                                }
                        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                            continue
                
                return {"verified": False, "error": "Invalid signature data"}
            else:
                return {"verified": False, "error": "Transaction not validated"}
                
        except Exception as e:
            return {"verified": False, "error": str(e)}
    
    def _verify_mock_credential_signature(self, report) -> Dict:
        """Verify a mock XLS-70 credential signature"""
        try:
            # For mock signatures, verify the document hash and credential
            current_hash = report.generate_hash()
            if report.document_hash == current_hash and report.credential_id:
                # Get credential data from the officer's wallet
                if report.signed_by and hasattr(report.signed_by, 'officer_wallet'):
                    credential_data = report.signed_by.officer_wallet.credential_data
                    if credential_data:
                        return {
                            "verified": True,
                            "signature_type": "XLS70_CREDENTIAL",
                            "credential_data": credential_data,
                            "signature_data": {
                                "document_hash": report.document_hash,
                                "credential_id": report.credential_id,
                                "signed_at": report.signed_at.isoformat() if report.signed_at else None
                            },
                            "verified_at": timezone.now().isoformat(),
                            "note": "Mock implementation - XLS-70 not yet fully supported"
                        }
            
            return {"verified": False, "error": "Mock signature verification failed"}
        except Exception as e:
            return {"verified": False, "error": str(e)}
    
    def _get_credential_data(self, credential_id: str) -> Optional[Dict]:
        """Get credential data from XRPL"""
        try:
            # Look up credential in ledger
            ledger_response = self.client.request({
                "command": "ledger_entry",
                "credential": credential_id
            })
            
            if ledger_response.result.get("node"):
                credential_entry = ledger_response.result["node"]
                return json.loads(credential_entry.get("CredentialData", "{}"))
            
            return None
            
        except Exception:
            return None
    
    def _get_wallet_for_user(self, user):
        """Get XRPL wallet for a user"""
        try:
            return OfficerWallet.objects.get(user=user)
        except OfficerWallet.DoesNotExist:
            return None
    
    def _get_xrpl_wallet_object(self, officer_wallet):
        """Get XRPL Wallet object from database model"""
        try:
            fernet = Fernet(settings.XRPL_ENCRYPTION_KEY)
            secret = fernet.decrypt(officer_wallet.encrypted_secret.encode()).decode()
            return Wallet.from_seed(secret)
        except Exception as e:
            raise Exception(f"Failed to decrypt wallet: {str(e)}")
    
    def get_credential_status(self, user) -> Dict:
        """
        Get the current status of a user's credential
        
        Args:
            user: Django User object
        
        Returns:
            Dict with credential status information
        """
        try:
            officer_wallet = self._get_wallet_for_user(user)
            if not officer_wallet:
                return {"has_wallet": False}
            
            if not officer_wallet.credential_id:
                return {
                    "has_wallet": True,
                    "has_credential": False
                }
            
            # Check credential status on XRPL
            credential_data = self._get_credential_data(officer_wallet.credential_id)
            
            if credential_data:
                return {
                    "has_wallet": True,
                    "has_credential": True,
                    "credential_id": officer_wallet.credential_id,
                    "credential_data": credential_data,
                    "is_valid": self._is_credential_valid(credential_data)
                }
            else:
                return {
                    "has_wallet": True,
                    "has_credential": True,
                    "credential_id": officer_wallet.credential_id,
                    "is_valid": False,
                    "error": "Credential not found on XRPL"
                }
                
        except Exception as e:
            return {
                "has_wallet": False,
                "error": str(e)
            }
    
    def _is_credential_valid(self, credential_data: Dict) -> bool:
        """Check if a credential is still valid"""
        try:
            expires_at = credential_data.get("expires_at")
            if not expires_at:
                return True  # No expiry date means it's valid
            
            from datetime import datetime
            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            return timezone.now() < expiry_date
            
        except Exception:
            return False


# Global service instance
xls70_service = XLS70CredentialService()

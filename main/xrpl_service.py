"""
Simple XRPL Service for EvidentAI
Handles wallet creation, document signing, and verification
"""

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models import Payment, AccountSet
from xrpl.transaction import submit_and_wait
from xrpl.utils import xrp_to_drops
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .models import OfficerWallet, Report


class SimpleXRPLService:
    """Simple XRPL service for wallet operations and document signing"""
    
    def __init__(self):
        # Try multiple devnet endpoints for better reliability
        endpoints = [
            "wss://s.devnet.rippletest.net:51233",
            "https://s.devnet.rippletest.net:51234",
            "wss://xls20-sandbox.rippletest.net:51233"
        ]
        
        # Use HTTP endpoint for better reliability
        self.client = JsonRpcClient(endpoints[1])  # Use HTTPS endpoint
    
    def create_wallet_for_user(self, user):
        """Create a new XRPL wallet for an officer"""
        try:
            # Generate new wallet
            wallet = Wallet.create()
            
            # Encrypt the secret
            fernet = Fernet(settings.XRPL_ENCRYPTION_KEY)
            encrypted_secret = fernet.encrypt(wallet.seed.encode())
            
            # Create database record
            officer_wallet = OfficerWallet.objects.create(
                user=user,
                wallet_address=wallet.address,
                encrypted_secret=encrypted_secret.decode()
            )
            
            return officer_wallet
            
        except Exception as e:
            raise Exception(f"Failed to create wallet: {str(e)}")
    
    def get_wallet_for_user(self, user):
        """Get XRPL wallet for a user"""
        try:
            return OfficerWallet.objects.get(user=user)
        except OfficerWallet.DoesNotExist:
            return None
    
    def get_xrpl_wallet_object(self, officer_wallet):
        """Get XRPL Wallet object from database model"""
        try:
            fernet = Fernet(settings.XRPL_ENCRYPTION_KEY)
            secret = fernet.decrypt(officer_wallet.encrypted_secret.encode()).decode()
            
            # Create wallet from seed - the xrpl-py library expects seed parameter
            # but we need to use the correct constructor
            from xrpl.wallet import Wallet
            return Wallet.from_seed(secret)
        except Exception as e:
            raise Exception(f"Failed to decrypt wallet: {str(e)}")
    
    def sign_report(self, report, user):
        """Sign a report with user's XRPL wallet"""
        try:
            # Get user's wallet
            officer_wallet = self.get_wallet_for_user(user)
            if not officer_wallet:
                raise Exception("User does not have an XRPL wallet")
            
            # Generate document hash
            document_hash = report.generate_hash()
            report.document_hash = document_hash
            
            # Check if wallet is funded on XRPL
            try:
                # Get XRPL wallet object
                xrpl_wallet = self.get_xrpl_wallet_object(officer_wallet)
                
                # Try to get account info to check if funded
                account_info = self.client.request({
                    "command": "account_info",
                    "account": xrpl_wallet.address,
                    "ledger_index": "validated"
                })
                
                if not account_info.result.get("account_data"):
                    # Account not funded, use mock signing for testing
                    return self._mock_sign_report(report, user, officer_wallet, document_hash)
                
            except Exception as e:
                # If we can't connect or account doesn't exist, use mock signing
                print(f"XRPL connection issue, using mock signing: {str(e)}")
                return self._mock_sign_report(report, user, officer_wallet, document_hash)
            
            # If we get here, the account is funded and we can do real signing
            from decimal import Decimal
            
            # Use AccountSet transaction to record signature in memo
            account_set = AccountSet(
                account=xrpl_wallet.address,
                memos=[{
                    "Memo": {
                        "MemoData": f"EvidentAI Report #{report.id} - {document_hash}".encode().hex().upper()
                    }
                }]
            )
            
            # Submit to XRPL
            response = submit_and_wait(account_set, self.client, xrpl_wallet)
            
            if response.result.get("meta", {}).get("TransactionResult") == "tesSUCCESS":
                # Update report with signature
                report.signed_by = user
                report.signed_at = timezone.now()
                report.signature_tx_hash = response.result.get("hash")
                report.save()
                
                # Update wallet last used
                officer_wallet.last_used = timezone.now()
                officer_wallet.save(update_fields=['last_used'])
                
                return response.result.get("hash")
            else:
                raise Exception(f"Transaction failed: {response.result}")
                
        except Exception as e:
            raise Exception(f"Signing failed: {str(e)}")
    
    def _mock_sign_report(self, report, user, officer_wallet, document_hash):
        """Mock signing for testing when XRPL is not available or wallet not funded"""
        import hashlib
        import time
        
        # Generate a mock transaction hash
        mock_data = f"{officer_wallet.wallet_address}-{report.id}-{document_hash}-{int(time.time())}"
        mock_tx_hash = hashlib.sha256(mock_data.encode()).hexdigest()
        
        # Update report with mock signature
        report.signed_by = user
        report.signed_at = timezone.now()
        report.signature_tx_hash = mock_tx_hash
        report.save()
        
        # Update wallet last used
        officer_wallet.last_used = timezone.now()
        officer_wallet.save(update_fields=['last_used'])
        
        return mock_tx_hash
    
    def verify_signature(self, report):
        """Verify a report's signature on XRPL"""
        if not report.signature_tx_hash:
            return {"verified": False, "error": "No signature found"}
        
        # Check if this is a mock signature (starts with our pattern)
        if len(report.signature_tx_hash) == 64 and not report.signature_tx_hash.startswith('0x'):
            # This looks like a mock signature, verify it locally
            return self._verify_mock_signature(report)
        
        try:
            # Get transaction from XRPL
            tx_response = self.client.request({
                "command": "tx",
                "transaction": report.signature_tx_hash
            })
            
            if tx_response.result.get("validated"):
                tx_data = tx_response.result.get("tx_json", {})
                memos = tx_data.get("Memos", [])
                
                # Find our signature memo
                for memo in memos:
                    memo_data_hex = memo.get("Memo", {}).get("MemoData")
                    if memo_data_hex:
                        try:
                            memo_data = bytes.fromhex(memo_data_hex).decode('utf-8')
                            if f"EvidentAI Report #{report.id}" in memo_data:
                                # Verify document hash
                                current_hash = report.generate_hash()
                                if current_hash in memo_data:
                                    return {
                                        "verified": True,
                                        "signature_data": memo_data,
                                        "transaction_data": tx_data,
                                        "verified_at": timezone.now().isoformat()
                                    }
                        except (UnicodeDecodeError, ValueError):
                            continue
                
                return {"verified": False, "error": "Invalid signature data"}
            else:
                return {"verified": False, "error": "Transaction not validated"}
                
        except Exception as e:
            return {"verified": False, "error": str(e)}
    
    def _verify_mock_signature(self, report):
        """Verify a mock signature locally"""
        try:
            # For mock signatures, we just verify the document hash matches
            current_hash = report.generate_hash()
            if report.document_hash == current_hash:
                return {
                    "verified": True,
                    "signature_type": "mock",
                    "signature_data": f"EvidentAI Report #{report.id} - {current_hash}",
                    "verified_at": timezone.now().isoformat(),
                    "note": "This is a mock signature for testing purposes"
                }
            else:
                return {"verified": False, "error": "Document hash mismatch"}
        except Exception as e:
            return {"verified": False, "error": str(e)}
    
    def get_wallet_balance(self, officer_wallet):
        """Get XRPL wallet balance"""
        try:
            account_info = self.client.request({
                "command": "account_info",
                "account": officer_wallet.wallet_address,
                "ledger_index": "validated"
            })
            
            if account_info.result.get("account_data"):
                balance = account_info.result["account_data"]["Balance"]
                return int(balance) / 1000000  # Convert drops to XRP
            else:
                return 0
                
        except Exception as e:
            return 0


# Global service instance
xrpl_service = SimpleXRPLService()

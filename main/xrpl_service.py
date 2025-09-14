"""
Simple XRPL Service for EvidentAI
Handles wallet creation, document signing, and verification
"""

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models import Payment
from xrpl.transaction import submit_and_wait
from xrpl.utils import xrp_to_drops
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .models import OfficerWallet, Report


class SimpleXRPLService:
    """Simple XRPL service for wallet operations and document signing"""
    
    def __init__(self):
        self.client = JsonRpcClient("wss://s.devnet.rippletest.net:51233")
    
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
            return Wallet(seed=secret)
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
            
            # Get XRPL wallet object
            xrpl_wallet = self.get_xrpl_wallet_object(officer_wallet)
            
            # Create signature transaction (pay to self with memo)
            payment = Payment(
                account=xrpl_wallet.address,
                destination=xrpl_wallet.address,  # Pay to self
                amount=xrp_to_drops("0.000001"),  # Minimal amount
                memos=[{
                    "Memo": {
                        "MemoData": f"EvidentAI Report #{report.id} - {document_hash}".encode().hex().upper()
                    }
                }]
            )
            
            # Submit to XRPL
            response = submit_and_wait(payment, self.client, xrpl_wallet)
            
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
    
    def verify_signature(self, report):
        """Verify a report's signature on XRPL"""
        if not report.signature_tx_hash:
            return {"verified": False, "error": "No signature found"}
        
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

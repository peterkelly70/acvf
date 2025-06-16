"""
Core cryptographic services for the AVCF system.
"""

import json
import hashlib
import gnupg
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple, Union
from datetime import datetime

from .models import AVCFMetadata, SignedAVCFBlock, SignatureStatus, VerificationResult
from ..infra.exceptions import AVCFCryptoError


class CryptoService:
    """Service for cryptographic operations in the AVCF system."""
    
    def __init__(self, gnupg_home: Optional[Path] = None):
        """
        Initialize the crypto service.
        
        Args:
            gnupg_home: Path to the GnuPG home directory. If None, a temporary directory will be used.
        """
        if gnupg_home is None:
            self._temp_dir = tempfile.TemporaryDirectory()
            gnupg_home = Path(self._temp_dir.name)
        else:
            self._temp_dir = None
            
        self.gpg = gnupg.GPG(gnupghome=str(gnupg_home))
    
    def __del__(self):
        """Clean up temporary directory if one was created."""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def calculate_video_hash(self, video_path: Path) -> str:
        """
        Calculate SHA-256 hash of video content.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            SHA-256 hash of the video content.
            
        Raises:
            AVCFCryptoError: If the video file cannot be read.
        """
        try:
            # In a real implementation, we would extract just the audio/video streams
            # and exclude container metadata to avoid hash invalidation on metadata changes.
            # For now, we'll hash the entire file as a placeholder.
            sha256_hash = hashlib.sha256()
            with open(video_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            raise AVCFCryptoError(f"Failed to calculate video hash: {e}")
    
    def create_metadata(self, 
                       video_path: Path, 
                       author_name: str,
                       pubkey_fingerprint: str,
                       author_email: Optional[str] = None,
                       author_organization: Optional[str] = None,
                       pubkey_url: Optional[str] = None,
                       embedded_pubkey: Optional[str] = None,
                       tags: Optional[list] = None,
                       notes: Optional[str] = None) -> AVCFMetadata:
        """
        Create AVCF metadata for a video.
        
        Args:
            video_path: Path to the video file.
            author_name: Name of the author.
            pubkey_fingerprint: Fingerprint of the author's public key.
            author_email: Email of the author.
            author_organization: Organization of the author.
            pubkey_url: URL to retrieve the author's public key.
            embedded_pubkey: Author's public key embedded directly.
            tags: Optional tags for categorization.
            notes: Optional notes about the content.
            
        Returns:
            AVCF metadata.
        """
        video_hash = self.calculate_video_hash(video_path)
        
        return AVCFMetadata(
            video_hash=video_hash,
            author_name=author_name,
            author_email=author_email,
            author_organization=author_organization,
            pubkey_fingerprint=pubkey_fingerprint,
            pubkey_url=pubkey_url,
            embedded_pubkey=embedded_pubkey,
            timestamp=datetime.utcnow(),
            tool_name="avcf-sign",
            tool_version="0.1.0",
            tags=tags,
            notes=notes
        )
    
    def sign_metadata(self, metadata: AVCFMetadata, key_id: str, passphrase: Optional[str] = None) -> SignedAVCFBlock:
        """
        Sign AVCF metadata with the author's private key.
        
        Args:
            metadata: AVCF metadata to sign.
            key_id: ID or fingerprint of the private key to use for signing.
            passphrase: Passphrase for the private key.
            
        Returns:
            Signed AVCF block.
            
        Raises:
            AVCFCryptoError: If the metadata cannot be signed.
        """
        # Serialize metadata to JSON
        metadata_json = metadata.model_dump_json()
        
        # Sign the serialized metadata
        signature = self.gpg.sign(metadata_json, 
                                 keyid=key_id, 
                                 passphrase=passphrase, 
                                 detach=True, 
                                 clearsign=False)
        
        if not signature:
            raise AVCFCryptoError(f"Failed to sign metadata: {signature.stderr}")
        
        return SignedAVCFBlock(
            metadata=metadata,
            signature=str(signature)
        )
    
    def import_key(self, key_data: str) -> list:
        """
        Import a PGP key.
        
        Args:
            key_data: PGP key data.
            
        Returns:
            List of fingerprints of imported keys.
            
        Raises:
            AVCFCryptoError: If the key cannot be imported.
        """
        result = self.gpg.import_keys(key_data)
        if not result.fingerprints:
            raise AVCFCryptoError(f"Failed to import key: {result.stderr}")
        return result.fingerprints
    
    def verify_signature(self, signed_block: SignedAVCFBlock) -> VerificationResult:
        """
        Verify the signature of a signed AVCF block.
        
        Args:
            signed_block: Signed AVCF block.
            
        Returns:
            Verification result.
        """
        # Extract metadata and signature
        metadata = signed_block.metadata
        signature = signed_block.signature
        
        # Check if we have the public key
        keys = self.gpg.list_keys()
        key_found = False
        for key in keys:
            if metadata.pubkey_fingerprint in key['fingerprint']:
                key_found = True
                break
        
        if not key_found:
            # If we have an embedded public key, import it
            if metadata.embedded_pubkey:
                try:
                    self.import_key(metadata.embedded_pubkey)
                    key_found = True
                except AVCFCryptoError:
                    return VerificationResult(
                        status=SignatureStatus.KEY_NOT_FOUND,
                        metadata=metadata,
                        error_message="Failed to import embedded public key"
                    )
            else:
                return VerificationResult(
                    status=SignatureStatus.KEY_NOT_FOUND,
                    metadata=metadata,
                    error_message="Public key not found and not embedded"
                )
        
        # Serialize metadata to JSON
        metadata_json = metadata.model_dump_json()
        
        # Create a temporary file for the signature
        with tempfile.NamedTemporaryFile(delete=False) as sig_file:
            sig_file.write(signature.encode())
            sig_file_path = sig_file.name
        
        try:
            # Verify the signature
            verified = self.gpg.verify_data(sig_file_path, metadata_json.encode())
            
            if verified:
                return VerificationResult(
                    status=SignatureStatus.VALID,
                    metadata=metadata
                )
            else:
                return VerificationResult(
                    status=SignatureStatus.INVALID,
                    metadata=metadata,
                    error_message="Invalid signature"
                )
        except Exception as e:
            return VerificationResult(
                status=SignatureStatus.ERROR,
                metadata=metadata,
                error_message=f"Error verifying signature: {e}"
            )
        finally:
            # Clean up temporary file
            os.unlink(sig_file_path)
    
    def verify_video_hash(self, video_path: Path, metadata: AVCFMetadata) -> bool:
        """
        Verify that the hash in the metadata matches the video file.
        
        Args:
            video_path: Path to the video file.
            metadata: AVCF metadata.
            
        Returns:
            True if the hash matches, False otherwise.
        """
        calculated_hash = self.calculate_video_hash(video_path)
        return calculated_hash == metadata.video_hash

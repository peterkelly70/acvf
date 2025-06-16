"""
Application services for the AVCF system.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple
import tempfile
import os
import shutil
import requests
from urllib.parse import urlparse

from ..domain.crypto import CryptoService
from ..domain.models import AVCFMetadata, SignedAVCFBlock, VerificationResult, SignatureStatus
from ..infra.container import ContainerFactory, ContainerAdapter
from ..infra.exceptions import AVCFError, AVCFKeyError, AVCFContainerError


class SigningService:
    """Service for signing video files with AVCF metadata."""
    
    def __init__(self, crypto_service: Optional[CryptoService] = None, gnupg_home: Optional[Path] = None):
        """
        Initialize the signing service.
        
        Args:
            crypto_service: Crypto service to use. If None, a new one will be created.
            gnupg_home: Path to the GnuPG home directory. If None, a temporary directory will be used.
        """
        self.crypto_service = crypto_service or CryptoService(gnupg_home)
    
    def sign_video(self, 
                  input_path: Path, 
                  output_path: Path, 
                  key_id: str,
                  author_name: str,
                  author_email: Optional[str] = None,
                  author_organization: Optional[str] = None,
                  pubkey_url: Optional[str] = None,
                  embed_pubkey: bool = False,
                  passphrase: Optional[str] = None,
                  tags: Optional[list] = None,
                  notes: Optional[str] = None) -> Path:
        """
        Sign a video file with AVCF metadata.
        
        Args:
            input_path: Path to the input video file.
            output_path: Path to the output video file.
            key_id: ID or fingerprint of the private key to use for signing.
            author_name: Name of the author.
            author_email: Email of the author.
            author_organization: Organization of the author.
            pubkey_url: URL to retrieve the author's public key.
            embed_pubkey: Whether to embed the public key in the metadata.
            passphrase: Passphrase for the private key.
            tags: Optional tags for categorization.
            notes: Optional notes about the content.
            
        Returns:
            Path to the signed video file.
            
        Raises:
            AVCFError: If the video cannot be signed.
        """
        # Get the public key fingerprint
        keys = self.crypto_service.gpg.list_keys()
        key_found = False
        pubkey_fingerprint = None
        
        for key in keys:
            if key_id in key['keyid'] or key_id in key['fingerprint']:
                pubkey_fingerprint = key['fingerprint']
                key_found = True
                break
        
        if not key_found:
            raise AVCFKeyError(f"Private key not found: {key_id}")
        
        # Get the embedded public key if requested
        embedded_pubkey = None
        if embed_pubkey:
            exported_keys = self.crypto_service.gpg.export_keys([pubkey_fingerprint])
            if not exported_keys:
                raise AVCFKeyError(f"Failed to export public key: {pubkey_fingerprint}")
            embedded_pubkey = exported_keys
        
        # Create the metadata
        metadata = self.crypto_service.create_metadata(
            video_path=input_path,
            author_name=author_name,
            pubkey_fingerprint=pubkey_fingerprint,
            author_email=author_email,
            author_organization=author_organization,
            pubkey_url=pubkey_url,
            embedded_pubkey=embedded_pubkey,
            tags=tags,
            notes=notes
        )
        
        # Sign the metadata
        signed_block = self.crypto_service.sign_metadata(
            metadata=metadata,
            key_id=key_id,
            passphrase=passphrase
        )
        
        # Get the container adapter
        container_adapter = ContainerFactory.create_adapter(input_path)
        
        # Embed the metadata
        container_adapter.embed_metadata(
            input_path=input_path,
            output_path=output_path,
            metadata_block=signed_block
        )
        
        return output_path


class VerificationService:
    """Service for verifying AVCF signatures in video files."""
    
    def __init__(self, crypto_service: Optional[CryptoService] = None, gnupg_home: Optional[Path] = None):
        """
        Initialize the verification service.
        
        Args:
            crypto_service: Crypto service to use. If None, a new one will be created.
            gnupg_home: Path to the GnuPG home directory. If None, a temporary directory will be used.
        """
        self.crypto_service = crypto_service or CryptoService(gnupg_home)
    
    def verify_video(self, video_path: Path, fetch_keys: bool = True) -> VerificationResult:
        """
        Verify the AVCF signature in a video file.
        
        Args:
            video_path: Path to the video file.
            fetch_keys: Whether to fetch missing public keys from URLs.
            
        Returns:
            Verification result.
            
        Raises:
            AVCFError: If the verification fails.
        """
        # Get the container adapter
        container_adapter = ContainerFactory.create_adapter(video_path)
        
        # Extract the metadata
        signed_block = container_adapter.extract_metadata(video_path)
        
        if signed_block is None:
            return VerificationResult(
                status=SignatureStatus.MISSING,
                error_message="No AVCF metadata found in the video file"
            )
        
        # If we should fetch missing keys and we have a URL
        if fetch_keys and signed_block.metadata.pubkey_url and not self._has_key(signed_block.metadata.pubkey_fingerprint):
            try:
                self._fetch_key(signed_block.metadata.pubkey_url)
            except Exception as e:
                # If fetching fails but we have an embedded key, try that instead
                if signed_block.metadata.embedded_pubkey:
                    try:
                        self.crypto_service.import_key(signed_block.metadata.embedded_pubkey)
                    except AVCFError:
                        return VerificationResult(
                            status=SignatureStatus.KEY_NOT_FOUND,
                            metadata=signed_block.metadata,
                            error_message=f"Failed to fetch key from URL and failed to import embedded key: {e}"
                        )
                else:
                    return VerificationResult(
                        status=SignatureStatus.KEY_NOT_FOUND,
                        metadata=signed_block.metadata,
                        error_message=f"Failed to fetch key from URL and no embedded key available: {e}"
                    )
        
        # Verify the signature
        sig_result = self.crypto_service.verify_signature(signed_block)
        
        # If the signature is valid, also verify the video hash
        if sig_result.status == SignatureStatus.VALID:
            hash_valid = self.crypto_service.verify_video_hash(video_path, signed_block.metadata)
            if not hash_valid:
                return VerificationResult(
                    status=SignatureStatus.INVALID,
                    metadata=signed_block.metadata,
                    error_message="Video hash does not match the hash in the metadata"
                )
        
        return sig_result
    
    def _has_key(self, fingerprint: str) -> bool:
        """
        Check if we have a public key with the given fingerprint.
        
        Args:
            fingerprint: Fingerprint of the public key.
            
        Returns:
            True if we have the key, False otherwise.
        """
        keys = self.crypto_service.gpg.list_keys()
        for key in keys:
            if fingerprint in key['fingerprint']:
                return True
        return False
    
    def _fetch_key(self, url: str) -> list:
        """
        Fetch a public key from a URL.
        
        Args:
            url: URL to fetch the key from.
            
        Returns:
            List of fingerprints of imported keys.
            
        Raises:
            AVCFKeyError: If the key cannot be fetched or imported.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            key_data = response.text
            return self.crypto_service.import_key(key_data)
        except requests.exceptions.RequestException as e:
            raise AVCFKeyError(f"Failed to fetch key from URL: {e}")
        except AVCFError as e:
            raise AVCFKeyError(f"Failed to import key from URL: {e}")

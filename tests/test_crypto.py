"""
Unit tests for the AVCF cryptographic services.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from avcf.domain.crypto import CryptoService
from avcf.domain.models import AVCFMetadata, SignedAVCFBlock, SignatureStatus
from avcf.infra.exceptions import AVCFCryptoError


class TestCryptoService(unittest.TestCase):
    """Test cases for AVCF cryptographic services."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for GnuPG home
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gnupg_home = Path(self.temp_dir.name)
        
        # Create a crypto service
        self.crypto_service = CryptoService(self.gnupg_home)
        
        # Create a temporary video file
        self.video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.video_file.write(b'test video content')
        self.video_file.close()
        self.video_path = Path(self.video_file.name)
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary files
        os.unlink(self.video_path)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_calculate_video_hash(self):
        """Test calculating video hash."""
        # Calculate hash
        hash_value = self.crypto_service.calculate_video_hash(self.video_path)
        
        # Check that hash is a valid SHA-256 hash
        self.assertEqual(len(hash_value), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))
        
        # Check that hash is consistent
        hash_value2 = self.crypto_service.calculate_video_hash(self.video_path)
        self.assertEqual(hash_value, hash_value2)
    
    def test_create_metadata(self):
        """Test creating AVCF metadata."""
        # Create metadata
        metadata = self.crypto_service.create_metadata(
            video_path=self.video_path,
            author_name="Test Author",
            pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D"
        )
        
        # Check metadata fields
        self.assertEqual(metadata.author_name, "Test Author")
        self.assertEqual(metadata.pubkey_fingerprint, "D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D")
        self.assertEqual(metadata.tool_name, "avcf-sign")
        self.assertEqual(metadata.tool_version, "0.1.0")
        
        # Check that video hash is present
        self.assertIsNotNone(metadata.video_hash)
        self.assertEqual(len(metadata.video_hash), 64)
    
    @patch('gnupg.GPG')
    def test_sign_metadata(self, mock_gpg_class):
        """Test signing AVCF metadata."""
        # Mock GPG sign method
        mock_gpg = MagicMock()
        mock_gpg_class.return_value = mock_gpg
        mock_signature = MagicMock()
        mock_signature.__str__ = lambda self: "-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        mock_gpg.sign.return_value = mock_signature
        
        # Create a crypto service with mocked GPG
        crypto_service = CryptoService(self.gnupg_home)
        
        # Create metadata
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        # Sign metadata
        signed_block = crypto_service.sign_metadata(
            metadata=metadata,
            key_id="test_key_id"
        )
        
        # Check that sign method was called
        mock_gpg.sign.assert_called_once()
        
        # Check signed block
        self.assertEqual(signed_block.metadata, metadata)
        self.assertEqual(signed_block.signature, "-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----")
    
    @patch('gnupg.GPG')
    def test_sign_metadata_failure(self, mock_gpg_class):
        """Test signing AVCF metadata failure."""
        # Mock GPG sign method to return a falsy value
        mock_gpg = MagicMock()
        mock_gpg_class.return_value = mock_gpg
        mock_gpg.sign.return_value = None
        
        # Create a crypto service with mocked GPG
        crypto_service = CryptoService(self.gnupg_home)
        
        # Create metadata
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        # Try to sign metadata
        with self.assertRaises(AVCFCryptoError):
            crypto_service.sign_metadata(
                metadata=metadata,
                key_id="test_key_id"
            )
    
    @patch('gnupg.GPG')
    def test_verify_signature_valid(self, mock_gpg_class):
        """Test verifying a valid signature."""
        # Mock GPG verify_data method
        mock_gpg = MagicMock()
        mock_gpg_class.return_value = mock_gpg
        mock_gpg.verify_data.return_value = True
        mock_gpg.list_keys.return_value = [{'fingerprint': 'D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D'}]
        
        # Create a crypto service with mocked GPG
        crypto_service = CryptoService(self.gnupg_home)
        
        # Create metadata and signed block
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        signed_block = SignedAVCFBlock(
            metadata=metadata,
            signature="-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        )
        
        # Verify signature
        result = crypto_service.verify_signature(signed_block)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.VALID)
        self.assertEqual(result.metadata, metadata)
        self.assertIsNone(result.error_message)
    
    @patch('gnupg.GPG')
    def test_verify_signature_invalid(self, mock_gpg_class):
        """Test verifying an invalid signature."""
        # Mock GPG verify_data method
        mock_gpg = MagicMock()
        mock_gpg_class.return_value = mock_gpg
        mock_gpg.verify_data.return_value = False
        mock_gpg.list_keys.return_value = [{'fingerprint': 'D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D'}]
        
        # Create a crypto service with mocked GPG
        crypto_service = CryptoService(self.gnupg_home)
        
        # Create metadata and signed block
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        signed_block = SignedAVCFBlock(
            metadata=metadata,
            signature="-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        )
        
        # Verify signature
        result = crypto_service.verify_signature(signed_block)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.INVALID)
        self.assertEqual(result.metadata, metadata)
        self.assertEqual(result.error_message, "Invalid signature")
    
    @patch('gnupg.GPG')
    def test_verify_signature_key_not_found(self, mock_gpg_class):
        """Test verifying a signature with a missing key."""
        # Mock GPG methods
        mock_gpg = MagicMock()
        mock_gpg_class.return_value = mock_gpg
        mock_gpg.list_keys.return_value = [{'fingerprint': 'DIFFERENT_FINGERPRINT'}]
        
        # Create a crypto service with mocked GPG
        crypto_service = CryptoService(self.gnupg_home)
        
        # Create metadata and signed block
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        signed_block = SignedAVCFBlock(
            metadata=metadata,
            signature="-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        )
        
        # Verify signature
        result = crypto_service.verify_signature(signed_block)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.KEY_NOT_FOUND)
        self.assertEqual(result.metadata, metadata)
        self.assertEqual(result.error_message, "Public key not found and not embedded")
    
    def test_verify_video_hash(self):
        """Test verifying video hash."""
        # Calculate hash
        hash_value = self.crypto_service.calculate_video_hash(self.video_path)
        
        # Create metadata with correct hash
        metadata_correct = AVCFMetadata(
            video_hash=hash_value,
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        # Create metadata with incorrect hash
        metadata_incorrect = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        # Verify hashes
        self.assertTrue(self.crypto_service.verify_video_hash(self.video_path, metadata_correct))
        self.assertFalse(self.crypto_service.verify_video_hash(self.video_path, metadata_incorrect))


if __name__ == '__main__':
    unittest.main()

"""
Unit tests for the AVCF application services.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from avcf.app.services import SigningService, VerificationService
from avcf.domain.models import AVCFMetadata, SignedAVCFBlock, SignatureStatus, VerificationResult
from avcf.domain.crypto import CryptoService
from avcf.infra.exceptions import AVCFError, AVCFKeyError


class TestSigningService(unittest.TestCase):
    """Test cases for AVCF signing service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for GnuPG home
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gnupg_home = Path(self.temp_dir.name)
        
        # Create a temporary video file
        self.video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.video_file.write(b'test video content')
        self.video_file.close()
        self.video_path = Path(self.video_file.name)
        
        # Create a temporary output file
        self.output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.output_file.close()
        self.output_path = Path(self.output_file.name)
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary files
        os.unlink(self.video_path)
        os.unlink(self.output_path)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    @patch('avcf.domain.crypto.CryptoService')
    @patch('avcf.infra.container.ContainerFactory.create_adapter')
    def test_sign_video(self, mock_create_adapter, mock_crypto_service_class):
        """Test signing a video."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock GPG key list
        mock_crypto_service.gpg.list_keys.return_value = [
            {'keyid': 'test_key_id', 'fingerprint': 'D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D'}
        ]
        
        # Mock metadata creation
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            tool_name="avcf-sign",
            tool_version="0.1.0"
        )
        mock_crypto_service.create_metadata.return_value = metadata
        
        # Mock signature creation
        signed_block = SignedAVCFBlock(
            metadata=metadata,
            signature="-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        )
        mock_crypto_service.sign_metadata.return_value = signed_block
        
        # Mock container adapter
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter
        
        # Create signing service
        signing_service = SigningService(mock_crypto_service)
        
        # Sign video
        result_path = signing_service.sign_video(
            input_path=self.video_path,
            output_path=self.output_path,
            key_id="test_key_id",
            author_name="Test Author"
        )
        
        # Check that methods were called correctly
        mock_crypto_service.gpg.list_keys.assert_called_once()
        mock_crypto_service.create_metadata.assert_called_once_with(
            video_path=self.video_path,
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            author_email=None,
            author_organization=None,
            pubkey_url=None,
            embedded_pubkey=None,
            tags=None,
            notes=None
        )
        mock_crypto_service.sign_metadata.assert_called_once_with(
            metadata=metadata,
            key_id="test_key_id",
            passphrase=None
        )
        mock_create_adapter.assert_called_once_with(self.video_path)
        mock_adapter.embed_metadata.assert_called_once_with(
            input_path=self.video_path,
            output_path=self.output_path,
            metadata_block=signed_block
        )
        
        # Check result
        self.assertEqual(result_path, self.output_path)
    
    @patch('avcf.domain.crypto.CryptoService')
    def test_sign_video_key_not_found(self, mock_crypto_service_class):
        """Test signing a video with a key that doesn't exist."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock GPG key list (empty)
        mock_crypto_service.gpg.list_keys.return_value = []
        
        # Create signing service
        signing_service = SigningService(mock_crypto_service)
        
        # Try to sign video
        with self.assertRaises(AVCFKeyError):
            signing_service.sign_video(
                input_path=self.video_path,
                output_path=self.output_path,
                key_id="nonexistent_key_id",
                author_name="Test Author"
            )


class TestVerificationService(unittest.TestCase):
    """Test cases for AVCF verification service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for GnuPG home
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gnupg_home = Path(self.temp_dir.name)
        
        # Create a temporary video file
        self.video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.video_file.write(b'test video content')
        self.video_file.close()
        self.video_path = Path(self.video_file.name)
        
        # Create test metadata
        self.metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
            pubkey_url="https://example.com/keys/test.asc",
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        # Create signed block
        self.signed_block = SignedAVCFBlock(
            metadata=self.metadata,
            signature="-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary files
        os.unlink(self.video_path)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    @patch('avcf.domain.crypto.CryptoService')
    @patch('avcf.infra.container.ContainerFactory.create_adapter')
    def test_verify_video_valid(self, mock_create_adapter, mock_crypto_service_class):
        """Test verifying a valid video signature."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock container adapter
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter
        mock_adapter.extract_metadata.return_value = self.signed_block
        
        # Mock signature verification
        mock_crypto_service.verify_signature.return_value = VerificationResult(
            status=SignatureStatus.VALID,
            metadata=self.metadata
        )
        
        # Mock hash verification
        mock_crypto_service.verify_video_hash.return_value = True
        
        # Create verification service
        verification_service = VerificationService(mock_crypto_service)
        
        # Verify video
        result = verification_service.verify_video(self.video_path)
        
        # Check that methods were called correctly
        mock_create_adapter.assert_called_once_with(self.video_path)
        mock_adapter.extract_metadata.assert_called_once_with(self.video_path)
        mock_crypto_service.verify_signature.assert_called_once_with(self.signed_block)
        mock_crypto_service.verify_video_hash.assert_called_once_with(self.video_path, self.metadata)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.VALID)
        self.assertEqual(result.metadata, self.metadata)
        self.assertIsNone(result.error_message)
    
    @patch('avcf.domain.crypto.CryptoService')
    @patch('avcf.infra.container.ContainerFactory.create_adapter')
    def test_verify_video_invalid_hash(self, mock_create_adapter, mock_crypto_service_class):
        """Test verifying a video with an invalid hash."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock container adapter
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter
        mock_adapter.extract_metadata.return_value = self.signed_block
        
        # Mock signature verification
        mock_crypto_service.verify_signature.return_value = VerificationResult(
            status=SignatureStatus.VALID,
            metadata=self.metadata
        )
        
        # Mock hash verification (fails)
        mock_crypto_service.verify_video_hash.return_value = False
        
        # Create verification service
        verification_service = VerificationService(mock_crypto_service)
        
        # Verify video
        result = verification_service.verify_video(self.video_path)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.INVALID)
        self.assertEqual(result.metadata, self.metadata)
        self.assertEqual(result.error_message, "Video hash does not match the hash in the metadata")
    
    @patch('avcf.domain.crypto.CryptoService')
    @patch('avcf.infra.container.ContainerFactory.create_adapter')
    def test_verify_video_missing_metadata(self, mock_create_adapter, mock_crypto_service_class):
        """Test verifying a video with missing metadata."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock container adapter
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter
        mock_adapter.extract_metadata.return_value = None
        
        # Create verification service
        verification_service = VerificationService(mock_crypto_service)
        
        # Verify video
        result = verification_service.verify_video(self.video_path)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.MISSING)
        self.assertIsNone(result.metadata)
        self.assertEqual(result.error_message, "No AVCF metadata found in the video file")
    
    @patch('avcf.domain.crypto.CryptoService')
    @patch('avcf.infra.container.ContainerFactory.create_adapter')
    @patch('avcf.app.services.requests.get')
    def test_verify_video_fetch_key(self, mock_get, mock_create_adapter, mock_crypto_service_class):
        """Test verifying a video and fetching a key."""
        # Mock crypto service
        mock_crypto_service = MagicMock()
        mock_crypto_service_class.return_value = mock_crypto_service
        
        # Mock key check (key not found)
        mock_crypto_service.gpg.list_keys.return_value = []
        
        # Mock container adapter
        mock_adapter = MagicMock()
        mock_create_adapter.return_value = mock_adapter
        mock_adapter.extract_metadata.return_value = self.signed_block
        
        # Mock HTTP request
        mock_response = MagicMock()
        mock_response.text = "-----BEGIN PGP PUBLIC KEY BLOCK-----\nTest Key\n-----END PGP PUBLIC KEY BLOCK-----"
        mock_get.return_value = mock_response
        
        # Mock key import
        mock_crypto_service.import_key.return_value = ["D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D"]
        
        # Mock signature verification
        mock_crypto_service.verify_signature.return_value = VerificationResult(
            status=SignatureStatus.VALID,
            metadata=self.metadata
        )
        
        # Mock hash verification
        mock_crypto_service.verify_video_hash.return_value = True
        
        # Create verification service
        verification_service = VerificationService(mock_crypto_service)
        
        # Verify video
        result = verification_service.verify_video(self.video_path)
        
        # Check that methods were called correctly
        mock_get.assert_called_once_with("https://example.com/keys/test.asc", timeout=10)
        mock_crypto_service.import_key.assert_called_once_with(mock_response.text)
        
        # Check result
        self.assertEqual(result.status, SignatureStatus.VALID)


if __name__ == '__main__':
    unittest.main()

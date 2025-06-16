"""
Unit tests for the AVCF domain models.
"""

import unittest
from datetime import datetime
from pydantic import ValidationError

from avcf.domain.models import AVCFMetadata, SignedAVCFBlock, SignatureStatus, VerificationResult


class TestAVCFModels(unittest.TestCase):
    """Test cases for AVCF domain models."""
    
    def test_avcf_metadata_creation(self):
        """Test creating valid AVCF metadata."""
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
            timestamp=datetime.utcnow(),
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        self.assertEqual(metadata.author_name, "Test Author")
        self.assertEqual(metadata.tool_name, "avcf-test")
        self.assertEqual(metadata.video_hash, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    
    def test_avcf_metadata_validation(self):
        """Test validation of AVCF metadata."""
        # Missing required field
        with self.assertRaises(ValidationError):
            AVCFMetadata(
                author_name="Test Author",
                pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
                timestamp=datetime.utcnow(),
                tool_name="avcf-test",
                tool_version="0.1.0"
            )
    
    def test_signed_avcf_block_creation(self):
        """Test creating a valid signed AVCF block."""
        metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
            timestamp=datetime.utcnow(),
            tool_name="avcf-test",
            tool_version="0.1.0"
        )
        
        signature = "-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----"
        
        signed_block = SignedAVCFBlock(
            metadata=metadata,
            signature=signature
        )
        
        self.assertEqual(signed_block.metadata.author_name, "Test Author")
        self.assertEqual(signed_block.signature, signature)
    
    def test_verification_result_creation(self):
        """Test creating verification results."""
        # Valid result
        valid_result = VerificationResult(
            status=SignatureStatus.VALID,
            metadata=AVCFMetadata(
                video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                author_name="Test Author",
                pubkey_fingerprint="D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
                timestamp=datetime.utcnow(),
                tool_name="avcf-test",
                tool_version="0.1.0"
            )
        )
        
        self.assertEqual(valid_result.status, SignatureStatus.VALID)
        self.assertIsNone(valid_result.error_message)
        
        # Invalid result with error message
        invalid_result = VerificationResult(
            status=SignatureStatus.INVALID,
            error_message="Invalid signature"
        )
        
        self.assertEqual(invalid_result.status, SignatureStatus.INVALID)
        self.assertEqual(invalid_result.error_message, "Invalid signature")
        self.assertIsNone(invalid_result.metadata)


if __name__ == '__main__':
    unittest.main()

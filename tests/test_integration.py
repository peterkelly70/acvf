"""
Integration tests for the AVCF system.
"""

import unittest
import tempfile
import os
import subprocess
import json
from pathlib import Path
import shutil
import gnupg

from avcf.app.services import SigningService, VerificationService
from avcf.domain.models import SignatureStatus


class TestAVCFIntegration(unittest.TestCase):
    """Integration tests for the AVCF system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create a temporary directory for GnuPG home
        cls.gnupg_home = tempfile.mkdtemp()
        
        # Create a GPG instance
        cls.gpg = gnupg.GPG(gnupghome=cls.gnupg_home)
        
        # Generate a test key
        input_data = cls.gpg.gen_key_input(
            name_real="AVCF Test",
            name_email="test@avcf.example",
            passphrase="testpassphrase",
            key_type="RSA",
            key_length=2048
        )
        cls.key = cls.gpg.gen_key(input_data)
        
        # Create a temporary directory for test files
        cls.test_dir = tempfile.mkdtemp()
        
        # Create a test video file
        cls.video_path = Path(cls.test_dir) / "test_video.mp4"
        with open(cls.video_path, "wb") as f:
            # Write a minimal MP4 file header (not a valid MP4, but enough for testing)
            f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
            f.write(b'\x00\x00\x00\x08free\x00\x00\x00\x00')
            f.write(b'\x00\x00\x00\x08mdat\x00\x00\x00\x00')
            # Add some dummy video data
            f.write(b'\x00' * 1024)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Remove temporary directories
        shutil.rmtree(cls.gnupg_home)
        shutil.rmtree(cls.test_dir)
    
    def test_sign_and_verify(self):
        """Test signing and verifying a video."""
        # Create output path
        output_path = Path(self.test_dir) / "signed_video.mp4"
        
        # Create signing service
        signing_service = SigningService(gnupg_home=Path(self.gnupg_home))
        
        # Sign the video
        signing_service.sign_video(
            input_path=self.video_path,
            output_path=output_path,
            key_id=self.key.fingerprint,
            author_name="AVCF Test",
            author_email="test@avcf.example",
            embed_pubkey=True,  # Embed the public key for offline verification
            passphrase="testpassphrase"
        )
        
        # Check that the output file exists
        self.assertTrue(output_path.exists())
        
        # Create verification service
        verification_service = VerificationService(gnupg_home=Path(self.gnupg_home))
        
        # Verify the video
        result = verification_service.verify_video(output_path)
        
        # Check verification result
        self.assertEqual(result.status, SignatureStatus.VALID)
        self.assertEqual(result.metadata.author_name, "AVCF Test")
        self.assertEqual(result.metadata.author_email, "test@avcf.example")
        self.assertIsNotNone(result.metadata.embedded_pubkey)
        
        # Verify video hash
        self.assertIsNone(result.error_message)
    
    def test_tamper_detection(self):
        """Test that tampering with the video is detected."""
        # Create output paths
        signed_path = Path(self.test_dir) / "tamper_test_signed.mp4"
        tampered_path = Path(self.test_dir) / "tampered_video.mp4"
        
        # Create signing service
        signing_service = SigningService(gnupg_home=Path(self.gnupg_home))
        
        # Sign the video
        signing_service.sign_video(
            input_path=self.video_path,
            output_path=signed_path,
            key_id=self.key.fingerprint,
            author_name="AVCF Test",
            embed_pubkey=True,
            passphrase="testpassphrase"
        )
        
        # Create a tampered copy of the video
        shutil.copy(signed_path, tampered_path)
        
        # Tamper with the video content
        with open(tampered_path, "r+b") as f:
            f.seek(100)  # Seek to a position in the video data
            f.write(b'TAMPERED')  # Modify the data
        
        # Create verification service
        verification_service = VerificationService(gnupg_home=Path(self.gnupg_home))
        
        # Verify the tampered video
        result = verification_service.verify_video(tampered_path)
        
        # Check verification result
        self.assertEqual(result.status, SignatureStatus.INVALID)
        self.assertIsNotNone(result.error_message)
        self.assertIn("hash", result.error_message.lower())


if __name__ == '__main__':
    unittest.main()

"""
Unit tests for the AVCF container adapters.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from avcf.domain.models import AVCFMetadata, SignedAVCFBlock
from avcf.infra.container import MP4Adapter, MKVAdapter, WebMAdapter, ContainerFactory
from avcf.infra.exceptions import AVCFContainerError


class TestContainerAdapters(unittest.TestCase):
    """Test cases for AVCF container adapters."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary files
        self.mp4_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.mp4_file.write(b'test mp4 content')
        self.mp4_file.close()
        self.mp4_path = Path(self.mp4_file.name)
        
        self.mkv_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mkv')
        self.mkv_file.write(b'test mkv content')
        self.mkv_file.close()
        self.mkv_path = Path(self.mkv_file.name)
        
        self.webm_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
        self.webm_file.write(b'test webm content')
        self.webm_file.close()
        self.webm_path = Path(self.webm_file.name)
        
        self.output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        self.output_file.close()
        self.output_path = Path(self.output_file.name)
        
        # Create test metadata
        self.metadata = AVCFMetadata(
            video_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            author_name="Test Author",
            pubkey_fingerprint="D4C9D8F2E1A1D8BB2F09768A5FBE8F7B07B4328D",
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
        os.unlink(self.mp4_path)
        os.unlink(self.mkv_path)
        os.unlink(self.webm_path)
        os.unlink(self.output_path)
    
    @patch('ffmpeg.input')
    def test_mp4_adapter_embed_metadata(self, mock_input):
        """Test embedding metadata in MP4 file."""
        # Mock ffmpeg
        mock_output = MagicMock()
        mock_input.return_value.output.return_value = mock_output
        
        # Create adapter
        adapter = MP4Adapter()
        
        # Embed metadata
        adapter.embed_metadata(self.mp4_path, self.output_path, self.signed_block)
        
        # Check that ffmpeg was called correctly
        mock_input.assert_called_once_with(str(self.mp4_path))
        mock_input.return_value.output.assert_called_once()
        mock_output.global_args.assert_called_once_with('-y')
        mock_output.global_args.return_value.run.assert_called_once()
    
    @patch('ffmpeg.probe')
    def test_mp4_adapter_extract_metadata(self, mock_probe):
        """Test extracting metadata from MP4 file."""
        # Mock ffmpeg probe
        metadata_json = json.dumps(self.signed_block.model_dump())
        mock_probe.return_value = {
            'format': {
                'tags': {
                    'avcf_auth': metadata_json
                }
            }
        }
        
        # Create adapter
        adapter = MP4Adapter()
        
        # Extract metadata
        extracted_block = adapter.extract_metadata(self.mp4_path)
        
        # Check that ffmpeg was called correctly
        mock_probe.assert_called_once_with(str(self.mp4_path))
        
        # Check extracted metadata
        self.assertIsNotNone(extracted_block)
        self.assertEqual(extracted_block.metadata.author_name, "Test Author")
        self.assertEqual(extracted_block.metadata.video_hash, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(extracted_block.signature, "-----BEGIN PGP SIGNATURE-----\nTest Signature\n-----END PGP SIGNATURE-----")
    
    @patch('ffmpeg.probe')
    def test_mp4_adapter_extract_metadata_from_stream(self, mock_probe):
        """Test extracting metadata from MP4 file stream tags."""
        # Mock ffmpeg probe
        metadata_json = json.dumps(self.signed_block.model_dump())
        mock_probe.return_value = {
            'streams': [
                {
                    'tags': {
                        'avcf_auth': metadata_json
                    }
                }
            ]
        }
        
        # Create adapter
        adapter = MP4Adapter()
        
        # Extract metadata
        extracted_block = adapter.extract_metadata(self.mp4_path)
        
        # Check that ffmpeg was called correctly
        mock_probe.assert_called_once_with(str(self.mp4_path))
        
        # Check extracted metadata
        self.assertIsNotNone(extracted_block)
        self.assertEqual(extracted_block.metadata.author_name, "Test Author")
    
    @patch('ffmpeg.probe')
    def test_mp4_adapter_extract_metadata_missing(self, mock_probe):
        """Test extracting missing metadata from MP4 file."""
        # Mock ffmpeg probe
        mock_probe.return_value = {
            'format': {
                'tags': {}
            }
        }
        
        # Create adapter
        adapter = MP4Adapter()
        
        # Extract metadata
        extracted_block = adapter.extract_metadata(self.mp4_path)
        
        # Check that ffmpeg was called correctly
        mock_probe.assert_called_once_with(str(self.mp4_path))
        
        # Check that no metadata was extracted
        self.assertIsNone(extracted_block)
    
    @patch('ffmpeg.input')
    def test_mkv_adapter_embed_metadata(self, mock_input):
        """Test embedding metadata in MKV file."""
        # Mock ffmpeg
        mock_output = MagicMock()
        mock_input.return_value.output.return_value = mock_output
        
        # Create adapter
        adapter = MKVAdapter()
        
        # Embed metadata
        adapter.embed_metadata(self.mkv_path, self.output_path, self.signed_block)
        
        # Check that ffmpeg was called correctly
        mock_input.assert_called_once_with(str(self.mkv_path))
        mock_input.return_value.output.assert_called_once()
        mock_output.global_args.assert_called_once_with('-y')
        mock_output.global_args.return_value.run.assert_called_once()
    
    @patch('ffmpeg.probe')
    def test_mkv_adapter_extract_metadata(self, mock_probe):
        """Test extracting metadata from MKV file."""
        # Mock ffmpeg probe
        metadata_json = json.dumps(self.signed_block.model_dump())
        mock_probe.return_value = {
            'format': {
                'tags': {
                    'AVCF_AUTH': metadata_json
                }
            }
        }
        
        # Create adapter
        adapter = MKVAdapter()
        
        # Extract metadata
        extracted_block = adapter.extract_metadata(self.mkv_path)
        
        # Check that ffmpeg was called correctly
        mock_probe.assert_called_once_with(str(self.mkv_path))
        
        # Check extracted metadata
        self.assertIsNotNone(extracted_block)
        self.assertEqual(extracted_block.metadata.author_name, "Test Author")
    
    def test_container_factory(self):
        """Test container factory."""
        # Create adapters for different file types
        mp4_adapter = ContainerFactory.create_adapter(self.mp4_path)
        mkv_adapter = ContainerFactory.create_adapter(self.mkv_path)
        webm_adapter = ContainerFactory.create_adapter(self.webm_path)
        
        # Check adapter types
        self.assertIsInstance(mp4_adapter, MP4Adapter)
        self.assertIsInstance(mkv_adapter, MKVAdapter)
        self.assertIsInstance(webm_adapter, WebMAdapter)
        
        # Check unsupported format
        with self.assertRaises(AVCFContainerError):
            ContainerFactory.create_adapter(Path('test.txt'))


if __name__ == '__main__':
    unittest.main()

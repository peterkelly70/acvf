"""
Container format adapters for the AVCF system.
"""

import json
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional, Union, Dict, Any
from abc import ABC, abstractmethod

import ffmpeg

from ..domain.models import SignedAVCFBlock
from .exceptions import AVCFContainerError


class ContainerAdapter(ABC):
    """Base class for container format adapters."""
    
    @abstractmethod
    def embed_metadata(self, input_path: Path, output_path: Path, metadata_block: SignedAVCFBlock) -> None:
        """
        Embed AVCF metadata into a video file.
        
        Args:
            input_path: Path to the input video file.
            output_path: Path to the output video file.
            metadata_block: Signed AVCF metadata block to embed.
            
        Raises:
            AVCFContainerError: If the metadata cannot be embedded.
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, video_path: Path) -> Optional[SignedAVCFBlock]:
        """
        Extract AVCF metadata from a video file.
        
        Args:
            video_path: Path to the video file.
            
        Returns:
            Extracted AVCF metadata block, or None if no metadata is found.
            
        Raises:
            AVCFContainerError: If the metadata cannot be extracted.
        """
        pass


class MP4Adapter(ContainerAdapter):
    """Adapter for MP4 container format."""
    
    def embed_metadata(self, input_path: Path, output_path: Path, metadata_block: SignedAVCFBlock) -> None:
        """
        Embed AVCF metadata into an MP4 file using the 'udta' atom.
        
        Args:
            input_path: Path to the input MP4 file.
            output_path: Path to the output MP4 file.
            metadata_block: Signed AVCF metadata block to embed.
            
        Raises:
            AVCFContainerError: If the metadata cannot be embedded.
        """
        # Serialize the metadata block to JSON
        metadata_json = json.dumps(metadata_block.model_dump())
        
        # Create a temporary file for the metadata
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as metadata_file:
            metadata_file.write(metadata_json.encode())
            metadata_file_path = metadata_file.name
        
        try:
            # Use ffmpeg to embed the metadata in the 'udta' atom with custom tag 'avcf'
            # This uses the -metadata:s:v key=value syntax to add metadata to the video stream
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(output_path),
                    metadata_file=metadata_file_path,
                    metadata="avcf_auth={}".format(metadata_json.replace('"', '\\"')),
                    c='copy'  # Copy streams without re-encoding
                )
                .global_args('-y')  # Overwrite output file if it exists
                .run(quiet=True, overwrite_output=True)
            )
        except ffmpeg.Error as e:
            raise AVCFContainerError(f"Failed to embed metadata in MP4 file: {e.stderr.decode() if e.stderr else str(e)}")
        finally:
            # Clean up temporary file
            os.unlink(metadata_file_path)
    
    def extract_metadata(self, video_path: Path) -> Optional[SignedAVCFBlock]:
        """
        Extract AVCF metadata from an MP4 file.
        
        Args:
            video_path: Path to the MP4 file.
            
        Returns:
            Extracted AVCF metadata block, or None if no metadata is found.
            
        Raises:
            AVCFContainerError: If the metadata cannot be extracted.
        """
        try:
            # Use ffprobe to extract metadata
            probe = ffmpeg.probe(str(video_path))
            
            # Look for avcf_auth metadata in format tags
            for stream in probe.get('streams', []):
                tags = stream.get('tags', {})
                if 'avcf_auth' in tags:
                    metadata_json = tags['avcf_auth']
                    metadata_dict = json.loads(metadata_json)
                    return SignedAVCFBlock.model_validate(metadata_dict)
            
            # Look for avcf_auth metadata in format tags (top level)
            format_tags = probe.get('format', {}).get('tags', {})
            if 'avcf_auth' in format_tags:
                metadata_json = format_tags['avcf_auth']
                metadata_dict = json.loads(metadata_json)
                return SignedAVCFBlock.model_validate(metadata_dict)
            
            return None
        except ffmpeg.Error as e:
            raise AVCFContainerError(f"Failed to extract metadata from MP4 file: {e.stderr.decode() if e.stderr else str(e)}")
        except json.JSONDecodeError as e:
            raise AVCFContainerError(f"Failed to parse metadata JSON: {e}")
        except Exception as e:
            raise AVCFContainerError(f"Failed to extract metadata: {e}")


class MKVAdapter(ContainerAdapter):
    """Adapter for MKV container format."""
    
    def embed_metadata(self, input_path: Path, output_path: Path, metadata_block: SignedAVCFBlock) -> None:
        """
        Embed AVCF metadata into an MKV file using a custom tag.
        
        Args:
            input_path: Path to the input MKV file.
            output_path: Path to the output MKV file.
            metadata_block: Signed AVCF metadata block to embed.
            
        Raises:
            AVCFContainerError: If the metadata cannot be embedded.
        """
        # Serialize the metadata block to JSON
        metadata_json = json.dumps(metadata_block.model_dump())
        
        try:
            # Use ffmpeg to embed the metadata as a custom tag
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(output_path),
                    metadata="AVCF_AUTH={}".format(metadata_json.replace('"', '\\"')),
                    c='copy'  # Copy streams without re-encoding
                )
                .global_args('-y')  # Overwrite output file if it exists
                .run(quiet=True, overwrite_output=True)
            )
        except ffmpeg.Error as e:
            raise AVCFContainerError(f"Failed to embed metadata in MKV file: {e.stderr.decode() if e.stderr else str(e)}")
    
    def extract_metadata(self, video_path: Path) -> Optional[SignedAVCFBlock]:
        """
        Extract AVCF metadata from an MKV file.
        
        Args:
            video_path: Path to the MKV file.
            
        Returns:
            Extracted AVCF metadata block, or None if no metadata is found.
            
        Raises:
            AVCFContainerError: If the metadata cannot be extracted.
        """
        try:
            # Use ffprobe to extract metadata
            probe = ffmpeg.probe(str(video_path))
            
            # Look for AVCF_AUTH metadata in format tags
            format_tags = probe.get('format', {}).get('tags', {})
            if 'AVCF_AUTH' in format_tags:
                metadata_json = format_tags['AVCF_AUTH']
                metadata_dict = json.loads(metadata_json)
                return SignedAVCFBlock.model_validate(metadata_dict)
            
            return None
        except ffmpeg.Error as e:
            raise AVCFContainerError(f"Failed to extract metadata from MKV file: {e.stderr.decode() if e.stderr else str(e)}")
        except json.JSONDecodeError as e:
            raise AVCFContainerError(f"Failed to parse metadata JSON: {e}")
        except Exception as e:
            raise AVCFContainerError(f"Failed to extract metadata: {e}")


class WebMAdapter(ContainerAdapter):
    """Adapter for WebM container format."""
    
    def embed_metadata(self, input_path: Path, output_path: Path, metadata_block: SignedAVCFBlock) -> None:
        """
        Embed AVCF metadata into a WebM file.
        
        Args:
            input_path: Path to the input WebM file.
            output_path: Path to the output WebM file.
            metadata_block: Signed AVCF metadata block to embed.
            
        Raises:
            AVCFContainerError: If the metadata cannot be embedded.
        """
        # WebM is based on Matroska, so we can use the same approach as MKV
        mkv_adapter = MKVAdapter()
        mkv_adapter.embed_metadata(input_path, output_path, metadata_block)
    
    def extract_metadata(self, video_path: Path) -> Optional[SignedAVCFBlock]:
        """
        Extract AVCF metadata from a WebM file.
        
        Args:
            video_path: Path to the WebM file.
            
        Returns:
            Extracted AVCF metadata block, or None if no metadata is found.
            
        Raises:
            AVCFContainerError: If the metadata cannot be extracted.
        """
        # WebM is based on Matroska, so we can use the same approach as MKV
        mkv_adapter = MKVAdapter()
        return mkv_adapter.extract_metadata(video_path)


class ContainerFactory:
    """Factory for creating container adapters."""
    
    @staticmethod
    def create_adapter(file_path: Path) -> ContainerAdapter:
        """
        Create a container adapter for the given file.
        
        Args:
            file_path: Path to the video file.
            
        Returns:
            Container adapter for the file format.
            
        Raises:
            AVCFContainerError: If the file format is not supported.
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.mp4':
            return MP4Adapter()
        elif suffix == '.mkv':
            return MKVAdapter()
        elif suffix == '.webm':
            return WebMAdapter()
        else:
            raise AVCFContainerError(f"Unsupported container format: {suffix}")

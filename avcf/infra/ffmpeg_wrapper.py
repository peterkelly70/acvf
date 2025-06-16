"""
FFmpeg wrapper for the AVCF system.

This module provides a wrapper around FFmpeg to make it easier to integrate AVCF
with existing video workflows.
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import ffmpeg

from ..app.services import SigningService
from ..domain.models import SignedAVCFBlock
from ..infra.exceptions import AVCFError


class FFmpegWrapper:
    """Wrapper around FFmpeg for AVCF integration."""
    
    def __init__(self, signing_service: Optional[SigningService] = None, gnupg_home: Optional[Path] = None):
        """
        Initialize the FFmpeg wrapper.
        
        Args:
            signing_service: Signing service to use. If None, a new one will be created.
            gnupg_home: Path to the GnuPG home directory. If None, a temporary directory will be used.
        """
        self.signing_service = signing_service or SigningService(gnupg_home)
    
    def process_and_sign(self, 
                        input_path: Path, 
                        output_path: Path, 
                        key_id: str,
                        author_name: str,
                        ffmpeg_args: Optional[Dict[str, Any]] = None,
                        author_email: Optional[str] = None,
                        author_organization: Optional[str] = None,
                        pubkey_url: Optional[str] = None,
                        embed_pubkey: bool = False,
                        passphrase: Optional[str] = None,
                        tags: Optional[list] = None,
                        notes: Optional[str] = None) -> Path:
        """
        Process a video with FFmpeg and sign it with AVCF metadata.
        
        Args:
            input_path: Path to the input video file.
            output_path: Path to the output video file.
            key_id: ID or fingerprint of the private key to use for signing.
            author_name: Name of the author.
            ffmpeg_args: Additional FFmpeg arguments.
            author_email: Email of the author.
            author_organization: Organization of the author.
            pubkey_url: URL to retrieve the author's public key.
            embed_pubkey: Whether to embed the public key in the metadata.
            passphrase: Passphrase for the private key.
            tags: Optional tags for categorization.
            notes: Optional notes about the content.
            
        Returns:
            Path to the processed and signed video file.
            
        Raises:
            AVCFError: If the video cannot be processed or signed.
        """
        # Create a temporary file for the processed video
        with tempfile.NamedTemporaryFile(suffix=output_path.suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Process the video with FFmpeg
            self._process_video_with_ffmpeg(input_path, temp_path, ffmpeg_args)
            
            # Sign the processed video
            self._sign_processed_video(
                temp_path, output_path, key_id, author_name,
                author_email, author_organization, pubkey_url,
                embed_pubkey, passphrase, tags, notes
            )
            
            return output_path
        except ffmpeg.Error as e:
            raise AVCFError(f"Failed to process video with FFmpeg: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            raise AVCFError(f"Failed to process and sign video: {e}")
        finally:
            # Clean up temporary file
            if temp_path.exists():
                os.unlink(temp_path)
                
    def _process_video_with_ffmpeg(self, input_path: Path, output_path: Path, 
                                  ffmpeg_args: Optional[Dict[str, Any]]) -> None:
        """Process a video with FFmpeg using the provided arguments."""
        input_stream = ffmpeg.input(str(input_path))
        output_stream = self._apply_ffmpeg_args(input_stream, ffmpeg_args)
        
        # Set up output arguments
        output_kwargs = {'c': 'copy'}  # Default to copy codec
        if ffmpeg_args and 'output_args' in ffmpeg_args:
            output_kwargs.update(ffmpeg_args['output_args'])
        
        # Run FFmpeg
        output_stream.output(str(output_path), **output_kwargs).run(
            quiet=True, overwrite_output=True)
    
    def _apply_ffmpeg_args(self, stream, ffmpeg_args: Optional[Dict[str, Any]]):
        """Apply FFmpeg arguments to the stream."""
        if not ffmpeg_args:
            return stream
            
        for key, value in ffmpeg_args.items():
            stream = self._apply_ffmpeg_arg(stream, key, value)
        
        return stream
    
    def _apply_ffmpeg_arg(self, stream, key: str, value):
        """Apply a single FFmpeg argument to the stream."""
        if key == 'filters':
            stream = self._apply_filters(stream, value)
        elif key == 'audio_filters':
            stream = self._apply_audio_filters(stream, value)
        elif key == 'video_filters':
            stream = self._apply_video_filters(stream, value)
        elif key == 'output_args':
            # These will be applied directly to the output
            pass
        else:
            stream = self._apply_method(stream, key, value)
        
        return stream
    
    def _apply_filters(self, stream, filters):
        """Apply general filters to the stream."""
        if isinstance(filters, list):
            for filter_arg in filters:
                stream = stream.filter(**filter_arg)
        else:
            stream = stream.filter(**filters)
        return stream
    
    def _apply_audio_filters(self, stream, filters):
        """Apply audio filters to the stream."""
        if isinstance(filters, list):
            for filter_arg in filters:
                stream = stream.filter_audio(**filter_arg)
        else:
            stream = stream.filter_audio(**filters)
        return stream
    
    def _apply_video_filters(self, stream, filters):
        """Apply video filters to the stream."""
        if isinstance(filters, list):
            for filter_arg in filters:
                stream = stream.filter_video(**filter_arg)
        else:
            stream = stream.filter_video(**filters)
        return stream
    
    def _apply_method(self, stream, method_name: str, value):
        """Apply a method to the stream."""
        method = getattr(stream, method_name, None)
        if not method or not callable(method):
            return stream
            
        if isinstance(value, dict):
            return method(**value)
        elif isinstance(value, list):
            return method(*value)
        else:
            return method(value)
    
    def _sign_processed_video(self, input_path: Path, output_path: Path, 
                             key_id: str, author_name: str,
                             author_email: Optional[str] = None,
                             author_organization: Optional[str] = None,
                             pubkey_url: Optional[str] = None,
                             embed_pubkey: bool = False,
                             passphrase: Optional[str] = None,
                             tags: Optional[list] = None,
                             notes: Optional[str] = None) -> None:
        """Sign the processed video with AVCF metadata."""
        self.signing_service.sign_video(
            input_path=input_path,
            output_path=output_path,
            key_id=key_id,
            author_name=author_name,
            author_email=author_email,
            author_organization=author_organization,
            pubkey_url=pubkey_url,
            embed_pubkey=embed_pubkey,
            passphrase=passphrase,
            tags=tags,
            notes=notes
        )
    
    @staticmethod
    def create_filter_complex(filter_string: str) -> Dict[str, Any]:
        """
        Create a filter complex argument for FFmpeg.
        
        Args:
            filter_string: FFmpeg filter complex string.
            
        Returns:
            Dictionary of FFmpeg arguments.
        """
        return {
            'output_args': {
                'filter_complex': filter_string
            }
        }
    
    @staticmethod
    def create_video_filter(name: str, **args) -> Dict[str, Any]:
        """
        Create a video filter argument for FFmpeg.
        
        Args:
            name: Filter name.
            **args: Filter arguments.
            
        Returns:
            Dictionary of FFmpeg arguments.
        """
        return {
            'video_filters': {
                name: args
            }
        }
    
    @staticmethod
    def create_audio_filter(name: str, **args) -> Dict[str, Any]:
        """
        Create an audio filter argument for FFmpeg.
        
        Args:
            name: Filter name.
            **args: Filter arguments.
            
        Returns:
            Dictionary of FFmpeg arguments.
        """
        return {
            'audio_filters': {
                name: args
            }
        }
    
    @staticmethod
    def combine_args(*args) -> Dict[str, Any]:
        """
        Combine multiple FFmpeg arguments.
        
        Args:
            *args: FFmpeg arguments to combine.
            
        Returns:
            Combined FFmpeg arguments.
        """
        result = {}
        
        for arg in args:
            for key, value in arg.items():
                result = FFmpegWrapper._merge_arg_value(result, key, value)
        
        return result
    
    @staticmethod
    def _merge_arg_value(result: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Merge a new argument value with existing arguments."""
        if key not in result:
            # Add new key
            result[key] = value
            return result
            
        # Key exists, need to merge
        if isinstance(result[key], list):
            result = FFmpegWrapper._merge_with_list(result, key, value)
        elif isinstance(result[key], dict):
            result = FFmpegWrapper._merge_with_dict(result, key, value)
        else:
            # Convert to list
            result[key] = [result[key], value]
            
        return result
    
    @staticmethod
    def _merge_with_list(result: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Merge a value with an existing list value."""
        if isinstance(value, list):
            result[key].extend(value)
        else:
            result[key].append(value)
        return result
    
    @staticmethod
    def _merge_with_dict(result: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Merge a value with an existing dict value."""
        if isinstance(value, dict):
            result[key].update(value)
        else:
            # Can't merge dict with non-dict
            raise AVCFError(f"Cannot merge {key} arguments of different types")
        return result

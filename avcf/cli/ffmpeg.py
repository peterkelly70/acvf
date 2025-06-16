"""
Command-line interface for processing and signing videos with FFmpeg.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import click

from ..app.services import SigningService
from ..infra.ffmpeg_wrapper import FFmpegWrapper
from ..infra.exceptions import AVCFError


@dataclass
class CliArgs:
    """Container for CLI arguments to reduce parameter count."""
    input_file: str
    output: str
    key: str
    author_name: str
    author_email: Optional[str] = None
    author_org: Optional[str] = None
    pubkey_url: Optional[str] = None
    embed_pubkey: bool = False
    gnupg_home: Optional[str] = None
    tag: Tuple[str, ...] = field(default_factory=tuple)
    notes: Optional[str] = None
    passphrase_file: Optional[str] = None
    ffmpeg_args: Optional[str] = None
    video_filter: Tuple[str, ...] = field(default_factory=tuple)
    audio_filter: Tuple[str, ...] = field(default_factory=tuple)
    filter_complex: Optional[str] = None


@dataclass
class FFmpegConfig:
    """Configuration for FFmpeg processing and signing."""
    input_path: Path
    output_path: Path
    key_id: str
    author_name: str
    author_email: Optional[str] = None
    author_organization: Optional[str] = None
    pubkey_url: Optional[str] = None
    embed_pubkey: bool = False
    gnupg_home: Optional[Path] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    passphrase: Optional[str] = None
    ffmpeg_arguments: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_cli_args(cls, args: CliArgs) -> 'FFmpegConfig':
        """Create a config from CLI arguments."""
        # Convert paths
        input_path = Path(args.input_file).resolve()
        output_path = Path(args.output).resolve()
        
        # Get the passphrase if a file is specified
        passphrase = cls._read_passphrase(args.passphrase_file)
        
        # Convert gnupg_home to Path if specified
        gnupg_home_path = Path(args.gnupg_home) if args.gnupg_home else None
        
        # Parse FFmpeg arguments
        ffmpeg_arguments = cls._parse_ffmpeg_arguments(
            args.ffmpeg_args, args.video_filter, args.audio_filter, args.filter_complex)
        
        return cls(
            input_path=input_path,
            output_path=output_path,
            key_id=args.key,
            author_name=args.author_name,
            author_email=args.author_email,
            author_organization=args.author_org,
            pubkey_url=args.pubkey_url,
            embed_pubkey=args.embed_pubkey,
            gnupg_home=gnupg_home_path,
            tags=list(args.tag) if args.tag else None,
            notes=args.notes,
            passphrase=passphrase,
            ffmpeg_arguments=ffmpeg_arguments
        )
    
    @staticmethod
    def _read_passphrase(passphrase_file: Optional[str]) -> Optional[str]:
        """Read passphrase from file if specified."""
        if not passphrase_file:
            return None
            
        with open(passphrase_file, 'r') as f:
            return f.read().strip()
    
    @staticmethod
    def _parse_ffmpeg_arguments(ffmpeg_args: Optional[str], video_filter: tuple, 
                               audio_filter: tuple, filter_complex: Optional[str]) -> Dict[str, Any]:
        """Parse FFmpeg arguments from CLI options."""
        result = {
            'video_filters': {},
            'audio_filters': {},
            'output_args': {}
        }
        
        # Process each argument source
        result = FFmpegConfig._load_json_args(result, ffmpeg_args)
        result = FFmpegConfig._process_video_filters(result, video_filter)
        result = FFmpegConfig._process_audio_filters(result, audio_filter)
        
        # Add filter complex if provided
        if filter_complex:
            result['output_args']['filter_complex'] = filter_complex
        
        return result
    
    @staticmethod
    def _load_json_args(result: Dict[str, Any], ffmpeg_args: Optional[str]) -> Dict[str, Any]:
        """Load arguments from JSON file if provided."""
        if not ffmpeg_args:
            return result
            
        try:
            with open(ffmpeg_args, 'r') as f:
                json_args = json.load(f)
                
            # Update result with JSON arguments
            for key, value in json_args.items():
                if key in result:
                    result[key].update(value)
                else:
                    result[key] = value
        except (json.JSONDecodeError, IOError) as e:
            raise AVCFError(f"Error loading FFmpeg arguments from {ffmpeg_args}: {e}")
            
        return result
    
    @staticmethod
    def _process_video_filters(result: Dict[str, Any], video_filter: tuple) -> Dict[str, Any]:
        """Process video filters from CLI arguments."""
        if video_filter:
            for filter_str in video_filter:
                filter_dict = FFmpegConfig._parse_filter_string(filter_str)
                result['video_filters'].update(filter_dict)
        return result
    
    @staticmethod
    def _process_audio_filters(result: Dict[str, Any], audio_filter: tuple) -> Dict[str, Any]:
        """Process audio filters from CLI arguments."""
        if audio_filter:
            for filter_str in audio_filter:
                filter_dict = FFmpegConfig._parse_filter_string(filter_str)
                result['audio_filters'].update(filter_dict)
        return result
    
    @staticmethod
    def _parse_filter_string(filter_str: str) -> Dict[str, Any]:
        """Parse filter string into dictionary."""
        filter_dict = {}
        for param in filter_str.split(':'):
            if '=' in param:
                name, value = param.split('=', 1)
                filter_dict[name] = value
            else:
                filter_dict[param] = True
        return filter_dict


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--output', '-o', type=click.Path(dir_okay=False, writable=True), required=True,
              help='Output file path.')
@click.option('--key', '-k', required=True,
              help='ID or fingerprint of the private key to use for signing.')
@click.option('--author-name', '-n', required=True,
              help='Name of the author.')
@click.option('--author-email', '-e',
              help='Email of the author.')
@click.option('--author-org', '-g',
              help='Organization of the author.')
@click.option('--pubkey-url', '-u',
              help='URL to retrieve the author\'s public key.')
@click.option('--embed-pubkey/--no-embed-pubkey', default=False,
              help='Whether to embed the public key in the metadata.')
@click.option('--gnupg-home', type=click.Path(file_okay=False, exists=True),
              help='Path to the GnuPG home directory.')
@click.option('--tag', '-t', multiple=True,
              help='Tags for categorization. Can be specified multiple times.')
@click.option('--notes',
              help='Notes about the content.')
@click.option('--passphrase-file', type=click.Path(exists=True, dir_okay=False, readable=True),
              help='File containing the passphrase for the private key.')
@click.option('--ffmpeg-args', type=click.Path(exists=True, dir_okay=False, readable=True),
              help='JSON file containing FFmpeg arguments.')
@click.option('--video-filter', '-vf', multiple=True,
              help='FFmpeg video filter. Format: name=value:name2=value2. Can be specified multiple times.')
@click.option('--audio-filter', '-af', multiple=True,
              help='FFmpeg audio filter. Format: name=value:name2=value2. Can be specified multiple times.')
@click.option('--filter-complex', '-fc',
              help='FFmpeg filter complex string.')
def main(**kwargs) -> None:
    """
    Process a video with FFmpeg and sign it with AVCF metadata.
    
    INPUT_FILE is the path to the video file to process and sign.
    """
    try:
        # Create CLI args object from kwargs
        cli_args = CliArgs(**kwargs)
        
        # Create config from CLI arguments
        config = FFmpegConfig.from_cli_args(cli_args)
        
        # Process and sign the video
        process_and_sign_video(config)
        
        click.echo(f"Video processed and signed successfully: {config.output_path}")
        sys.exit(0)
    except AVCFError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


def process_and_sign_video(config: FFmpegConfig) -> None:
    """Process and sign a video using the provided configuration."""
    # Create the signing service
    signing_service = SigningService(gnupg_home=config.gnupg_home)
    
    # Create the FFmpeg wrapper
    ffmpeg_wrapper = FFmpegWrapper(signing_service)
    
    # Process and sign the video
    ffmpeg_wrapper.process_and_sign(
        input_path=config.input_path,
        output_path=config.output_path,
        key_id=config.key_id,
        author_name=config.author_name,
        ffmpeg_args=config.ffmpeg_arguments,
        author_email=config.author_email,
        author_organization=config.author_organization,
        pubkey_url=config.pubkey_url,
        embed_pubkey=config.embed_pubkey,
        passphrase=config.passphrase,
        tags=config.tags,
        notes=config.notes
    )


if __name__ == '__main__':
    main()

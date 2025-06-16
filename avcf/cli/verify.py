"""
Command-line interface for verifying AVCF signatures in video files.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

import click

from ..app.services import VerificationService
from ..domain.models import SignatureStatus
from ..infra.exceptions import AVCFError


@click.command()
@click.argument('video_file', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--gnupg-home', type=click.Path(file_okay=False, exists=True),
              help='Path to the GnuPG home directory.')
@click.option('--no-fetch-keys', is_flag=True,
              help='Do not fetch missing public keys from URLs.')
@click.option('--json-output', is_flag=True,
              help='Output the result as JSON.')
def main(video_file: str, gnupg_home: Optional[str], no_fetch_keys: bool, json_output: bool) -> None:
    """
    Verify the AVCF signature in a video file.
    
    VIDEO_FILE is the path to the video file to verify.
    """
    try:
        # Convert paths
        video_path = Path(video_file).resolve()
        
        # Convert gnupg_home to Path if specified
        gnupg_home_path = Path(gnupg_home) if gnupg_home else None
        
        # Create the verification service
        verification_service = VerificationService(gnupg_home=gnupg_home_path)
        
        # Verify the video
        result = verification_service.verify_video(
            video_path=video_path,
            fetch_keys=not no_fetch_keys
        )
        
        # Output the result
        if json_output:
            # Convert the result to a JSON-serializable dict
            result_dict = {
                "status": result.status.value,
                "verification_time": result.verification_time.isoformat(),
                "error_message": result.error_message
            }
            
            if result.metadata:
                # Convert the metadata to a dict
                metadata_dict = result.metadata.model_dump()
                # Convert datetime to ISO format
                metadata_dict["timestamp"] = metadata_dict["timestamp"].isoformat()
                result_dict["metadata"] = metadata_dict
            
            click.echo(json.dumps(result_dict, indent=2))
        else:
            # Output in a human-readable format
            click.echo(f"Verification status: {result.status.value.upper()}")
            
            if result.error_message:
                click.echo(f"Error: {result.error_message}")
            
            if result.metadata:
                click.echo("\nMetadata:")
                click.echo(f"  Author: {result.metadata.author_name}")
                if result.metadata.author_email:
                    click.echo(f"  Email: {result.metadata.author_email}")
                if result.metadata.author_organization:
                    click.echo(f"  Organization: {result.metadata.author_organization}")
                click.echo(f"  Timestamp: {result.metadata.timestamp.isoformat()}")
                click.echo(f"  Public key fingerprint: {result.metadata.pubkey_fingerprint}")
                if result.metadata.pubkey_url:
                    click.echo(f"  Public key URL: {result.metadata.pubkey_url}")
                if result.metadata.embedded_pubkey:
                    click.echo("  Public key: Embedded in metadata")
                if result.metadata.tags:
                    click.echo(f"  Tags: {', '.join(result.metadata.tags)}")
                if result.metadata.notes:
                    click.echo(f"  Notes: {result.metadata.notes}")
        
        # Exit with appropriate status code
        if result.status == SignatureStatus.VALID:
            sys.exit(0)
        else:
            sys.exit(1)
    except AVCFError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


if __name__ == '__main__':
    main()

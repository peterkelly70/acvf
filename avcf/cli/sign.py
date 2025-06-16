"""
Command-line interface for signing video files with AVCF metadata.
"""

import sys
import os
from pathlib import Path
from typing import Optional

import click

from ..app.services import SigningService
from ..infra.exceptions import AVCFError


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--output', '-o', type=click.Path(dir_okay=False, writable=True),
              help='Output file path. If not specified, a suffix will be added to the input file name.')
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
def main(input_file: str, output: Optional[str], key: str, author_name: str,
         author_email: Optional[str], author_org: Optional[str], pubkey_url: Optional[str],
         embed_pubkey: bool, gnupg_home: Optional[str], tag: tuple, notes: Optional[str],
         passphrase_file: Optional[str]) -> None:
    """
    Sign a video file with AVCF metadata.
    
    INPUT_FILE is the path to the video file to sign.
    """
    try:
        # Convert paths
        input_path = Path(input_file).resolve()
        
        if output:
            output_path = Path(output).resolve()
        else:
            # Add a suffix to the input file name
            stem = input_path.stem
            suffix = input_path.suffix
            output_path = input_path.with_name(f"{stem}_signed{suffix}")
        
        # Get the passphrase if a file is specified
        passphrase = None
        if passphrase_file:
            with open(passphrase_file, 'r') as f:
                passphrase = f.read().strip()
        
        # Convert gnupg_home to Path if specified
        gnupg_home_path = Path(gnupg_home) if gnupg_home else None
        
        # Create the signing service
        signing_service = SigningService(gnupg_home=gnupg_home_path)
        
        # Sign the video
        signed_path = signing_service.sign_video(
            input_path=input_path,
            output_path=output_path,
            key_id=key,
            author_name=author_name,
            author_email=author_email,
            author_organization=author_org,
            pubkey_url=pubkey_url,
            embed_pubkey=embed_pubkey,
            passphrase=passphrase,
            tags=list(tag) if tag else None,
            notes=notes
        )
        
        click.echo(f"Video signed successfully: {signed_path}")
        sys.exit(0)
    except AVCFError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


if __name__ == '__main__':
    main()

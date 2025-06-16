#!/usr/bin/env python3
"""
AVCF Demo Script

This script demonstrates the complete workflow of the AVCF system:
1. Generate a temporary GPG key
2. Create a sample video file
3. Sign the video with AVCF metadata
4. Verify the signed video
5. Tamper with the video and show detection
"""

import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path
import json

# Add the parent directory to the path so we can import the avcf package
sys.path.insert(0, str(Path(__file__).parent.parent))

from avcf.app.services import SigningService, VerificationService
from avcf.domain.models import SignatureStatus
from avcf.infra.ffmpeg_wrapper import FFmpegWrapper


# Constants for demo configuration
DEMO_AUTHOR_NAME = "AVCF Demo"
DEMO_AUTHOR_EMAIL = "demo@avcf.example"
DEMO_ORGANIZATION = "AVCF Project"


def generate_test_key(gnupg_home, name=DEMO_AUTHOR_NAME, email=DEMO_AUTHOR_EMAIL):
    """Generate a temporary GPG key for testing."""
    print(f"Generating test GPG key for {name} <{email}>...")
    
    # Generate key using gpg command line
    cmd = [
        "gpg", "--batch", "--gen-key", "--homedir", gnupg_home,
        "--no-tty", "--passphrase", ""
    ]
    
    key_config = f"""
    Key-Type: RSA
    Key-Length: 2048
    Name-Real: {name}
    Name-Email: {email}
    Expire-Date: 0
    %no-protection
    %commit
    """
    
    result = subprocess.run(cmd, input=key_config.encode(), capture_output=True)
    if result.returncode != 0:
        print(f"Error generating key: {result.stderr.decode()}")
        sys.exit(1)
    
    # Get the key fingerprint
    result = subprocess.run(
        ["gpg", "--homedir", gnupg_home, "--list-secret-keys", "--with-colons"],
        capture_output=True, text=True
    )
    
    for line in result.stdout.splitlines():
        if line.startswith("fpr:"):
            fingerprint = line.split(":")[9]
            return fingerprint
    
    print("Failed to get key fingerprint")
    sys.exit(1)


def create_test_video(output_path):
    """Create a simple test video file using FFmpeg."""
    print(f"Creating test video at {output_path}...")
    
    # Create a 5-second test video with text
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=5", 
        "-vf", "drawtext=text='AVCF Demo Video':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"Error creating test video: {result.stderr.decode()}")
        sys.exit(1)


def sign_video(input_path, output_path, key_id, gnupg_home):
    """Sign a video with AVCF metadata."""
    print(f"Signing video {input_path} -> {output_path}...")
    
    signing_service = SigningService(gnupg_home=Path(gnupg_home))
    
    signing_service.sign_video(
        input_path=input_path,
        output_path=output_path,
        key_id=key_id,
        author_name=DEMO_AUTHOR_NAME,
        author_email=DEMO_AUTHOR_EMAIL,
        author_organization=DEMO_ORGANIZATION,
        embed_pubkey=True,
        tags=["demo", "test", "example"],
        notes="This is a demonstration of the AVCF signing process."
    )


def verify_video(video_path, gnupg_home):
    """Verify a signed video and print the results."""
    print(f"Verifying video {video_path}...")
    
    verification_service = VerificationService(gnupg_home=Path(gnupg_home))
    result = verification_service.verify_video(video_path)
    
    print("\nVerification Results:")
    print(f"Status: {result.status.name}")
    
    if result.metadata:
        print("\nMetadata:")
        print(f"  Author: {result.metadata.author_name} <{result.metadata.author_email}>")
        print(f"  Organization: {result.metadata.author_organization}")
        print(f"  Timestamp: {result.metadata.timestamp}")
        print(f"  Key Fingerprint: {result.metadata.key_fingerprint}")
        print(f"  Tags: {', '.join(result.metadata.tags) if result.metadata.tags else 'None'}")
        print(f"  Notes: {result.metadata.notes}")
        print(f"  Public Key Embedded: {'Yes' if result.metadata.embedded_pubkey else 'No'}")
    
    if result.error_message:
        print(f"\nError: {result.error_message}")
    
    return result.status


def tamper_with_video(input_path, output_path):
    """Create a tampered copy of the video by modifying a few bytes."""
    print(f"Creating tampered copy of video {input_path} -> {output_path}...")
    
    # Copy the file
    shutil.copy2(input_path, output_path)
    
    # Modify a few bytes in the middle of the file
    with open(output_path, "r+b") as f:
        # Seek to a position in the middle of the file
        f.seek(int(os.path.getsize(output_path) / 2))
        # Write some bytes
        f.write(b"TAMPERED")


def process_with_ffmpeg(input_path, output_path, key_id, gnupg_home):
    """Process a video with FFmpeg and sign it."""
    print(f"Processing and signing video {input_path} -> {output_path}...")
    
    signing_service = SigningService(gnupg_home=Path(gnupg_home))
    ffmpeg_wrapper = FFmpegWrapper(signing_service)
    
    ffmpeg_wrapper.process_and_sign(
        input_path=input_path,
        output_path=output_path,
        key_id=key_id,
        author_name=DEMO_AUTHOR_NAME,
        author_email=DEMO_AUTHOR_EMAIL,
        author_organization=DEMO_ORGANIZATION,
        embed_pubkey=True,
        tags=["demo", "processed", "ffmpeg"],
        notes="This video was processed with FFmpeg and signed with AVCF.",
        ffmpeg_args={
            "video_filters": {
                "scale": "640:360"  # Resize to 640x360
            },
            "output_args": {
                "c:v": "libx264",
                "crf": "23"
            }
        }
    )


def main():
    """Run the complete AVCF demo workflow."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    gnupg_home = os.path.join(temp_dir, "gnupg")
    os.makedirs(gnupg_home, mode=0o700)
    
    try:
        print("=" * 80)
        print("AVCF Demo Script")
        print("=" * 80)
        
        # Define paths for test files
        original_video = Path(temp_dir) / "original.mp4"
        signed_video = Path(temp_dir) / "signed.mp4"
        tampered_video = Path(temp_dir) / "tampered.mp4"
        processed_video = Path(temp_dir) / "processed.mp4"
        
        # Generate a test key
        key_id = generate_test_key(gnupg_home)
        print(f"Generated key with ID: {key_id}")
        
        # Create a test video
        create_test_video(original_video)
        
        print("\n" + "=" * 80)
        print("1. Basic Signing and Verification")
        print("=" * 80)
        
        # Sign the video
        sign_video(original_video, signed_video, key_id, gnupg_home)
        
        # Verify the signed video
        status = verify_video(signed_video, gnupg_home)
        assert status == SignatureStatus.VALID, "Verification failed"
        
        print("\n" + "=" * 80)
        print("2. Tamper Detection")
        print("=" * 80)
        
        # Create a tampered copy
        tamper_with_video(signed_video, tampered_video)
        
        # Verify the tampered video
        status = verify_video(tampered_video, gnupg_home)
        assert status == SignatureStatus.INVALID, "Tamper detection failed"
        
        print("\n" + "=" * 80)
        print("3. FFmpeg Processing and Signing")
        print("=" * 80)
        
        # Process and sign with FFmpeg
        process_with_ffmpeg(original_video, processed_video, key_id, gnupg_home)
        
        # Verify the processed video
        status = verify_video(processed_video, gnupg_home)
        assert status == SignatureStatus.VALID, "Verification of processed video failed"
        
        print("\n" + "=" * 80)
        print("Demo completed successfully!")
        print("=" * 80)
        
    finally:
        # Clean up
        print("\nCleaning up temporary files...")
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()

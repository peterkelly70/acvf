# AVCF Usage Guide

## Overview

The Authenticated Video Container Format (AVCF) is a system for embedding cryptographic metadata directly into video files. This enables:

- **Authorship verification**: Prove who created or published a video
- **Tamper detection**: Verify that video content hasn't been modified
- **Protection against deepfakes**: Establish authentic source material
- **Offline verification**: Verify authenticity without requiring external services

AVCF works by embedding a signed cryptographic metadata block inside standard video containers like MP4 and MKV, making the files fully compatible with existing players while adding verification capabilities.

## Components

The AVCF system consists of several components:

1. **CLI Tools**:
   - `avcf-sign`: Sign video files with cryptographic metadata
   - `avcf-verify`: Verify the authenticity of signed videos
   - `avcf-ffmpeg`: Process videos with FFmpeg and sign them in one step

2. **VLC Plugin**: Display signature information during video playback

3. **Library**: Python modules for integrating AVCF into your applications

## Prerequisites

- Python 3.8 or higher
- GnuPG (GPG) installed on your system
- FFmpeg installed on your system (for container manipulation)
- VLC Media Player (for the verification plugin)

## Installation

```bash
# Install from PyPI
pip install avcf

# Or install from source
git clone https://github.com/peterkelly70/justice_protocol.git
cd justice_protocol
pip install -e .
```

## Key Management

AVCF uses PGP keys for signing and verification. If you don't already have a PGP key pair:

```bash
# Generate a new PGP key
gpg --full-generate-key
```

Choose RSA (sign only) or RSA (sign and encrypt) with at least 2048 bits.

To list your keys:

```bash
gpg --list-secret-keys --keyid-format LONG
```

## Basic Usage

### Signing a Video

```bash
avcf-sign input.mp4 -o signed.mp4 -k YOUR_KEY_ID -n "Your Name" -e "your.email@example.com"
```

Options:
- `-k, --key`: ID or fingerprint of your private key
- `-n, --author-name`: Your name as the author
- `-e, --author-email`: Your email (optional)
- `-g, --author-org`: Your organization (optional)
- `-u, --pubkey-url`: URL where your public key can be found (optional)
- `--embed-pubkey`: Embed your public key in the metadata
- `-t, --tag`: Add tags for categorization (can be used multiple times)
- `--notes`: Add notes about the content
- `--passphrase-file`: File containing your key passphrase
- `--gnupg-home`: Custom GnuPG home directory

### Verifying a Video

```bash
avcf-verify signed.mp4
```

Options:
- `--json`: Output verification results as JSON
- `--gnupg-home`: Custom GnuPG home directory
- `--fetch-keys/--no-fetch-keys`: Whether to fetch missing public keys from URLs

### Processing and Signing with FFmpeg

```bash
avcf-ffmpeg input.mp4 -o output.mp4 -k YOUR_KEY_ID -n "Your Name" -vf "scale=1280:720"
```

Options:
- All options from `avcf-sign` plus:
- `-vf, --video-filter`: FFmpeg video filters
- `-af, --audio-filter`: FFmpeg audio filters
- `-fc, --filter-complex`: FFmpeg filter complex string
- `--ffmpeg-args`: JSON file with complex FFmpeg arguments

## VLC Plugin Installation

1. Copy `vlc/avcf_verify.lua` to your VLC extensions directory:
   - Linux: `~/.local/share/vlc/lua/extensions/`
   - Windows: `%APPDATA%\vlc\lua\extensions\`
   - macOS: `/Users/[username]/Library/Application Support/org.videolan.vlc/lua/extensions/`

2. Restart VLC and enable the extension from the View > Extensions menu.

## Advanced Usage

### Embedding Public Keys

To make offline verification easier, embed your public key in the video:

```bash
avcf-sign input.mp4 -o signed.mp4 -k YOUR_KEY_ID -n "Your Name" --embed-pubkey
```

### Using Public Key URLs

Instead of embedding the full public key, you can provide a URL where it can be found:

```bash
avcf-sign input.mp4 -o signed.mp4 -k YOUR_KEY_ID -n "Your Name" -u "https://example.com/keys/mykey.asc"
```

### Complex FFmpeg Processing

For complex video processing with FFmpeg:

```bash
# Create a JSON file with FFmpeg arguments
echo '{
  "video_filters": [
    {"scale": "1280:720"},
    {"fps": "30"}
  ],
  "audio_filters": [
    {"volume": "2.0"}
  ],
  "output_args": {
    "c:v": "libx264",
    "preset": "medium",
    "crf": "23"
  }
}' > ffmpeg_args.json

# Use the JSON file with avcf-ffmpeg
avcf-ffmpeg input.mp4 -o output.mp4 -k YOUR_KEY_ID -n "Your Name" --ffmpeg-args ffmpeg_args.json
```

## Programmatic Usage

You can integrate AVCF into your Python applications:

```python
from pathlib import Path
from avcf.app.services import SigningService, VerificationService
from avcf.infra.ffmpeg_wrapper import FFmpegWrapper

# Sign a video
signing_service = SigningService()
signing_service.sign_video(
    input_path=Path("input.mp4"),
    output_path=Path("signed.mp4"),
    key_id="YOUR_KEY_ID",
    author_name="Your Name",
    author_email="your.email@example.com",
    embed_pubkey=True
)

# Verify a video
verification_service = VerificationService()
result = verification_service.verify_video(Path("signed.mp4"))
print(f"Signature status: {result.status}")
print(f"Author: {result.metadata.author_name}")

# Process and sign with FFmpeg
ffmpeg_wrapper = FFmpegWrapper(signing_service)
ffmpeg_wrapper.process_and_sign(
    input_path=Path("input.mp4"),
    output_path=Path("output.mp4"),
    key_id="YOUR_KEY_ID",
    author_name="Your Name",
    ffmpeg_args={
        "video_filters": {"scale": "1280:720"},
        "output_args": {"c:v": "libx264", "crf": "23"}
    }
)
```

## Security Considerations

- **Key Security**: Protect your private keys with strong passphrases
- **Offline Verification**: For highest security, verify videos offline with locally stored trusted keys
- **Key Fingerprints**: Always verify key fingerprints when importing new keys
- **Tamper Evidence**: AVCF can detect tampering but cannot prevent it
- **Metadata Privacy**: Consider what metadata you include, as it becomes part of the video file

## Troubleshooting

### Common Issues

1. **Key Not Found**: Ensure your GnuPG keyring contains the required keys
2. **FFmpeg Errors**: Check that FFmpeg is installed and in your PATH
3. **Container Compatibility**: Not all containers support metadata embedding; MP4 and MKV are recommended
4. **VLC Plugin Not Showing**: Verify the plugin is installed in the correct directory and enabled in VLC

### Getting Help

For issues, questions, or contributions, please visit:
https://github.com/peterkelly70/justice_protocol/issues

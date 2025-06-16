# Authenticated Video Container Format (AVCF)

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A system for embedding cryptographic metadata directly into video files to enable authorship verification and protect against AI-generated deepfakes, impersonation, and reputational sabotage.

**GitHub Repository**: [https://github.com/peterkelly70/acvf](https://github.com/peterkelly70/acvf)

## Overview

The AVCF system provides tools for signing video files with cryptographic metadata and verifying the authenticity of signed videos. The metadata is embedded directly into standard video containers (MP4, MKV, WebM) in a way that preserves compatibility with existing video players.

## Components

1. **CLI Tools**:
   - `avcf-sign`: Sign video files with cryptographic metadata
   - `avcf-verify`: Verify the authenticity of signed videos
   - `avcf-ffmpeg`: Process videos with FFmpeg and sign them in one step

2. **VLC Plugin**: Display signature information during video playback

3. **FFmpeg Integration**: Process videos with FFmpeg filters and sign them in a single operation

4. **JSON Schema**: Formal specification of the AVCF metadata format

## Trust Model

AVCF uses PGP signatures to establish trust. The system is designed to:

- Provide tamper-evident verification of video files
- Allow offline verification if the public key is available
- Support fetching public keys from trusted URLs
- Enable embedding public keys directly in the video for simplified verification

## Use Cases

- **Journalists**: Sign video evidence to prove authenticity
- **Content Creators**: Protect against unauthorized modifications or deepfakes
- **Organizations**: Establish official sources of video content
- **Legal**: Provide chain of custody for video evidence

## Installation

```bash
# Install from source
git clone https://github.com/peterkelly70/justice_protocol.git
cd justice_protocol
pip install -e .
```

## Usage

### Signing a Video

```bash
avcf-sign input.mp4 -o signed.mp4 -k YOUR_KEY_ID -n "Your Name" -e "your.email@example.com"
```

### Verifying a Video

```bash
avcf-verify signed.mp4
```

### Processing and Signing with FFmpeg

```bash
avcf-ffmpeg input.mp4 -o output.mp4 -k YOUR_KEY_ID -n "Your Name" -vf "scale=1280:720"
```

### VLC Plugin

Copy `vlc/avcf_verify.lua` to your VLC extensions directory and enable it from the View > Extensions menu.

## Examples

Check out the `examples` directory for complete workflow demonstrations:

- `demo.py`: End-to-end demonstration of signing, verification, and tamper detection

## Documentation

Detailed documentation is available in the `docs` directory:

- `usage_guide.md`: Comprehensive guide to using all AVCF features

## Integration Testing

The project includes integration tests that demonstrate the complete workflow:

```bash
python -m unittest tests/test_integration.py
```

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.

GPL-3.0 is a strong copyleft license that ensures the software remains free and open source. It requires that any derivative works or modifications must also be distributed under the same license terms, ensuring that the project and its derivatives remain freely available to all users.

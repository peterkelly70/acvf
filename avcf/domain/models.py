"""
Core domain models for the AVCF system.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class SignatureStatus(Enum):
    """Status of a signature verification."""
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    KEY_NOT_FOUND = "key_not_found"
    ERROR = "error"


class AVCFMetadata(BaseModel):
    """
    The core AVCF metadata block that gets embedded in video containers.
    This is serialized to JSON and signed with the author's private key.
    """
    # Video content identification
    video_hash: str = Field(..., description="SHA-256 hash of the video + audio stream")
    
    # Author identification
    author_name: str = Field(..., description="Name of the author or organization")
    author_email: Optional[str] = Field(None, description="Email of the author")
    author_organization: Optional[str] = Field(None, description="Organization of the author")
    
    # Cryptographic elements
    pubkey_fingerprint: str = Field(..., description="Fingerprint of the author's public key")
    pubkey_url: Optional[HttpUrl] = Field(None, description="URL to retrieve the author's public key")
    embedded_pubkey: Optional[str] = Field(None, description="Author's public key embedded directly")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of signature creation")
    tool_name: str = Field("avcf-sign", description="Tool used to create the signature")
    tool_version: str = Field(..., description="Version of the tool used")
    
    # Additional metadata
    tags: Optional[List[str]] = Field(None, description="Optional tags for categorization")
    notes: Optional[str] = Field(None, description="Optional notes about the content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "author_name": "Jane Doe",
                "author_email": "jane@example.com",
                "pubkey_fingerprint": "D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
                "pubkey_url": "https://example.com/keys/jane.asc",
                "timestamp": "2025-06-16T03:12:59Z",
                "tool_name": "avcf-sign",
                "tool_version": "0.1.0"
            }
        }


class SignedAVCFBlock(BaseModel):
    """
    The complete signed AVCF block that gets embedded in the video container.
    This includes both the metadata and its signature.
    """
    metadata: AVCFMetadata = Field(..., description="The AVCF metadata")
    signature: str = Field(..., description="PGP signature of the serialized metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "video_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "author_name": "Jane Doe",
                    "author_email": "jane@example.com",
                    "pubkey_fingerprint": "D4C9 D8F2 E1A1 D8BB 2F09 768A 5FBE 8F7B 07B4 328D",
                    "pubkey_url": "https://example.com/keys/jane.asc",
                    "timestamp": "2025-06-16T03:12:59Z",
                    "tool_name": "avcf-sign",
                    "tool_version": "0.1.0"
                },
                "signature": "-----BEGIN PGP SIGNATURE-----\n...\n-----END PGP SIGNATURE-----"
            }
        }


class VerificationResult(BaseModel):
    """Result of verifying an AVCF signature."""
    status: SignatureStatus
    metadata: Optional[AVCFMetadata] = None
    error_message: Optional[str] = None
    verification_time: datetime = Field(default_factory=datetime.utcnow)

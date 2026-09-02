"""Block structure for Healthcare Blockchain."""

import time
import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class MedicalRecord:
    """
    Medical record stored in the blockchain.

    Attributes:
        patient_id: Unique patient identifier
        ipfs_hash: IPFS CID of the encrypted medical image
        record_type: Type of medical record (X-ray, MRI, CT, etc.)
        diagnosis: AI-generated diagnosis (if available)
        uploader_id: ID of user who uploaded
        access_list: List of user IDs with access permissions
        timestamp: When the record was created
        metadata: Additional metadata
    """
    patient_id: str
    ipfs_hash: str
    record_type: str = "medical_image"
    diagnosis: Optional[str] = None
    confidence: Optional[float] = None
    uploader_id: str = ""
    access_list: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def has_access(self, user_id: str) -> bool:
        """Check if user has access to this record."""
        return user_id in self.access_list or user_id == self.patient_id or user_id == self.uploader_id

    def grant_access(self, user_id: str):
        """Grant access to a user."""
        if user_id not in self.access_list:
            self.access_list.append(user_id)

    def revoke_access(self, user_id: str):
        """Revoke access from a user."""
        if user_id in self.access_list:
            self.access_list.remove(user_id)


@dataclass
class Block:
    """
    Block in the Healthcare Blockchain.

    Attributes:
        index: Block number
        timestamp: When the block was created
        records: List of medical records in this block
        proof: Proof of work nonce
        previous_hash: Hash of the previous block
    """
    index: int
    timestamp: str
    records: List[MedicalRecord]
    proof: int
    previous_hash: str

    def to_dict(self) -> dict:
        """Convert block to dictionary for hashing."""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'records': [r.to_dict() for r in self.records],
            'proof': self.proof,
            'previous_hash': self.previous_hash
        }

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the block."""
        block_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> 'Block':
        """Create Block from dictionary."""
        records = [MedicalRecord(**r) for r in data.get('records', [])]
        return cls(
            index=data['index'],
            timestamp=data['timestamp'],
            records=records,
            proof=data['proof'],
            previous_hash=data['previous_hash']
        )


def create_genesis_block() -> Block:
    """Create the genesis (first) block."""
    return Block(
        index=0,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        records=[],
        proof=1,
        previous_hash="0"
    )

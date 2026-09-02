"""Healthcare Blockchain implementation with access control."""

import time
import json
import hashlib
import os
from typing import List, Dict, Any, Optional, Set
import requests

from .block import Block, MedicalRecord, create_genesis_block


class HealthcareBlockchain:
    """
    Blockchain for secure healthcare data management.

    Features:
    - Medical record storage with access control
    - Proof of Work consensus
    - Multi-node support
    - Record retrieval by patient
    """

    def __init__(self, difficulty: int = 4, node_address: str = None,
                 storage_path: str = None):
        """
        Initialize the blockchain.

        Args:
            difficulty: Number of leading zeros required for proof of work
            node_address: This node's address
        """
        self.chain: List[Block] = []
        self.pending_records: List[MedicalRecord] = []
        self.nodes: Set[str] = set()
        self.difficulty = difficulty
        self.storage_path = storage_path

        # Load chain from disk if available, otherwise create genesis block.
        if not self._load_state():
            genesis = create_genesis_block()
            self.chain.append(genesis)
            self._save_state()

        # Add this node
        if node_address:
            self.nodes.add(node_address)
            self._save_state()

    @property
    def last_block(self) -> Block:
        """Get the last block in the chain."""
        return self.chain[-1]

    def add_record(self, patient_id: str, ipfs_hash: str, uploader_id: str,
                   record_type: str = "medical_image", diagnosis: str = None,
                   confidence: float = None, metadata: dict = None) -> int:
        """
        Add a medical record to pending records.

        Args:
            patient_id: Patient's unique identifier
            ipfs_hash: IPFS CID of encrypted medical data
            uploader_id: ID of the user uploading the record
            record_type: Type of medical record
            diagnosis: AI diagnosis result (if available)
            confidence: AI confidence score
            metadata: Additional metadata

        Returns:
            Index of the block that will contain this record
        """
        record = MedicalRecord(
            patient_id=patient_id,
            ipfs_hash=ipfs_hash,
            uploader_id=uploader_id,
            record_type=record_type,
            diagnosis=diagnosis,
            confidence=confidence,
            access_list=[patient_id, uploader_id],  # Patient and uploader have access by default
            metadata=metadata or {}
        )
        self.pending_records.append(record)

        # Auto-mine if we have a record (for simplicity)
        return self.mine_block()

    def mine_block(self) -> int:
        """
        Mine a new block with pending records.

        Returns:
            Index of the new block
        """
        if not self.pending_records:
            return self.last_block.index

        last_block = self.last_block
        previous_hash = last_block.compute_hash()
        proof = self.proof_of_work(last_block.proof)

        new_block = Block(
            index=last_block.index + 1,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            records=self.pending_records.copy(),
            proof=proof,
            previous_hash=previous_hash
        )

        self.chain.append(new_block)
        self.pending_records = []
        self._save_state()

        return new_block.index

    def proof_of_work(self, previous_proof: int) -> int:
        """
        Simple Proof of Work algorithm.

        Args:
            previous_proof: Proof from the previous block

        Returns:
            New proof that satisfies difficulty requirement
        """
        new_proof = 1
        while True:
            hash_operation = hashlib.sha256(
                str(new_proof ** 2 - previous_proof ** 2).encode()
            ).hexdigest()

            if hash_operation[:self.difficulty] == '0' * self.difficulty:
                return new_proof
            new_proof += 1

    def is_chain_valid(self, chain: List[Block] = None) -> bool:
        """
        Validate the blockchain integrity.

        Args:
            chain: Chain to validate (defaults to self.chain)

        Returns:
            True if valid, False otherwise
        """
        if chain is None:
            chain = self.chain

        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            # Check previous hash
            if current.previous_hash != previous.compute_hash():
                return False

            # Check proof of work
            hash_operation = hashlib.sha256(
                str(current.proof ** 2 - previous.proof ** 2).encode()
            ).hexdigest()

            if hash_operation[:self.difficulty] != '0' * self.difficulty:
                return False

        return True

    def get_records_by_patient(self, patient_id: str, user_id: str) -> List[Dict]:
        """
        Get all records for a patient (if user has access).

        Args:
            patient_id: Patient's ID
            user_id: Requesting user's ID

        Returns:
            List of accessible records
        """
        records = []
        for block in self.chain:
            for record in block.records:
                if record.patient_id == patient_id and record.has_access(user_id):
                    records.append({
                        'block_index': block.index,
                        'timestamp': record.timestamp,
                        **record.to_dict()
                    })
        return records

    def get_record_by_hash(self, ipfs_hash: str, user_id: str) -> Optional[Dict]:
        """
        Get a specific record by IPFS hash.

        Args:
            ipfs_hash: IPFS CID
            user_id: Requesting user's ID

        Returns:
            Record if found and accessible, None otherwise
        """
        for block in self.chain:
            for record in block.records:
                if record.ipfs_hash == ipfs_hash and record.has_access(user_id):
                    return {
                        'block_index': block.index,
                        **record.to_dict()
                    }
        return None

    def grant_access(self, ipfs_hash: str, owner_id: str, target_user_id: str) -> bool:
        """
        Grant access to a record.

        Note: This creates a new record with updated access list
        (blockchain is immutable, so we add a new "access grant" record)

        Args:
            ipfs_hash: Record's IPFS hash
            owner_id: ID of record owner
            target_user_id: ID of user to grant access to

        Returns:
            True if successful
        """
        for block in self.chain:
            for record in block.records:
                if record.ipfs_hash == ipfs_hash:
                    if record.patient_id == owner_id or record.uploader_id == owner_id:
                        record.grant_access(target_user_id)
                        self._save_state()
                        return True
        return False

    def grant_access_to_patient_records(self, patient_id: str, owner_id: str,
                                        target_user_id: str) -> int:
        """Grant access to all records belonging to a patient."""
        granted_count = 0
        for block in self.chain:
            for record in block.records:
                if record.patient_id != patient_id:
                    continue
                if record.patient_id == owner_id or record.uploader_id == owner_id:
                    if target_user_id not in record.access_list:
                        record.grant_access(target_user_id)
                        granted_count += 1
        if granted_count > 0:
            self._save_state()
        return granted_count

    def revoke_access_for_patient_records(self, patient_id: str, owner_id: str,
                                          target_user_id: str,
                                          record_hash: str = None) -> int:
        """Revoke access from one or all patient records."""
        revoked_count = 0
        for block in self.chain:
            for record in block.records:
                if record.patient_id != patient_id:
                    continue
                if record_hash and record.ipfs_hash != record_hash:
                    continue
                if record.patient_id == owner_id or record.uploader_id == owner_id:
                    if target_user_id in record.access_list:
                        record.revoke_access(target_user_id)
                        revoked_count += 1
        if revoked_count > 0:
            self._save_state()
        return revoked_count

    def add_node(self, address: str):
        """Add a node to the network."""
        self.nodes.add(address)
        self._save_state()

    def remove_node(self, address: str):
        """Remove a node from the network."""
        self.nodes.discard(address)
        self._save_state()

    def replace_chain(self) -> bool:
        """
        Consensus algorithm: replace chain with longest valid chain.

        Returns:
            True if chain was replaced
        """
        longest_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            if node.startswith('0.0.0.0'):
                continue

            try:
                response = requests.get(f'http://{node}/api/chain', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    length = data['length']
                    chain_data = data['chain']

                    # Convert to Block objects
                    chain = [Block.from_dict(b) for b in chain_data]

                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        longest_chain = chain

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                continue

        if longest_chain:
            self.chain = longest_chain
            self._save_state()
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert blockchain to dictionary."""
        return {
            'chain': [block.to_dict() for block in self.chain],
            'length': len(self.chain),
            'nodes': list(self.nodes),
            'pending_records': [r.to_dict() for r in self.pending_records]
        }

    def get_all_records(self, user_id: str) -> List[Dict]:
        """Get all records accessible to a user."""
        records = []
        for block in self.chain:
            for record in block.records:
                if record.has_access(user_id):
                    records.append({
                        'block_index': block.index,
                        **record.to_dict()
                    })
        return records

    def _load_state(self) -> bool:
        """Load blockchain state from disk if a storage path is configured."""
        if not self.storage_path:
            return False
        if not os.path.exists(self.storage_path):
            return False

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            chain_data = data.get('chain', [])
            loaded_chain = [Block.from_dict(b) for b in chain_data]

            if not loaded_chain:
                return False
            if not self.is_chain_valid(loaded_chain):
                return False

            self.chain = loaded_chain
            self.nodes = set(data.get('nodes', []))
            self.pending_records = [MedicalRecord(**r) for r in data.get('pending_records', [])]
            return True
        except Exception:
            return False

    def _save_state(self):
        """Persist blockchain state to disk if a storage path is configured."""
        if not self.storage_path:
            return

        folder = os.path.dirname(self.storage_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

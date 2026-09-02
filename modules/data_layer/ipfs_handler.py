"""IPFS Handler for decentralized storage via Infura."""

import os
import base64
import hashlib
import shutil
import requests
from typing import Optional, Dict, Any


class LocalStorageHandler:
    """
    Local storage handler for testing without IPFS.
    Simulates IPFS behavior using local filesystem.
    """

    def __init__(self, storage_folder: str = "ipfs_storage"):
        """Initialize local storage."""
        self.storage_folder = storage_folder
        os.makedirs(storage_folder, exist_ok=True)

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """Upload file to local storage, return simulated CID."""
        # Generate hash-based CID
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()

        # Simulate IPFS CID format (Qm prefix)
        cid = f"Qm{file_hash[:44]}"

        # Copy file to storage
        dest_path = os.path.join(self.storage_folder, cid)
        shutil.copy(file_path, dest_path)

        return {
            'Hash': cid,
            'Name': os.path.basename(file_path),
            'Size': len(content)
        }

    def download_file(self, cid: str, output_path: str) -> str:
        """Download file from local storage."""
        source_path = os.path.join(self.storage_folder, cid)
        if not os.path.exists(source_path):
            raise Exception(f"File not found: {cid}")

        shutil.copy(source_path, output_path)
        return output_path

    def get_content(self, cid: str) -> bytes:
        """Get file content from local storage."""
        source_path = os.path.join(self.storage_folder, cid)
        if not os.path.exists(source_path):
            raise Exception(f"File not found: {cid}")

        with open(source_path, 'rb') as f:
            return f.read()


class IPFSHandler:
    """
    IPFS Handler for storing and retrieving medical data.

    Uses Infura's IPFS gateway for decentralized storage.
    """

    INFURA_IPFS_URL = "https://ipfs.infura.io:5001/api/v0"
    INFURA_GATEWAY_URL = "https://ipfs.infura.io/ipfs"

    def __init__(self, project_id: str = None, project_secret: str = None):
        """
        Initialize IPFS handler with Infura credentials.

        Args:
            project_id: Infura Project ID
            project_secret: Infura Project Secret
        """
        self.project_id = project_id or os.getenv('INFURA_PROJECT_ID')
        self.project_secret = project_secret or os.getenv('INFURA_PROJECT_SECRET')

        if not self.project_id or not self.project_secret:
            raise ValueError(
                "INFURA_PROJECT_ID and INFURA_PROJECT_SECRET must be set.\n"
                "Get credentials from: https://infura.io/dashboard"
            )

        # Basic Auth header for Infura
        auth_string = f"{self.project_id}:{self.project_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth_bytes}"
        }

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to IPFS.

        Args:
            file_path: Path to the file to upload

        Returns:
            Dictionary with 'Hash' (CID), 'Name', and 'Size'
        """
        url = f"{self.INFURA_IPFS_URL}/add"

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, headers=self.headers, files=files)

        if response.status_code != 200:
            raise Exception(f"IPFS upload failed: {response.text}")

        return response.json()

    def upload_bytes(self, data: bytes, filename: str = "data") -> Dict[str, Any]:
        """
        Upload bytes directly to IPFS.

        Args:
            data: Bytes to upload
            filename: Name for the file

        Returns:
            Dictionary with 'Hash' (CID), 'Name', and 'Size'
        """
        url = f"{self.INFURA_IPFS_URL}/add"
        files = {'file': (filename, data)}
        response = requests.post(url, headers=self.headers, files=files)

        if response.status_code != 200:
            raise Exception(f"IPFS upload failed: {response.text}")

        return response.json()

    def download_file(self, cid: str, output_path: str) -> str:
        """
        Download a file from IPFS by CID.

        Args:
            cid: Content Identifier (IPFS hash)
            output_path: Where to save the downloaded file

        Returns:
            Path to downloaded file
        """
        content = self.get_content(cid)

        with open(output_path, 'wb') as f:
            f.write(content)

        return output_path

    def get_content(self, cid: str) -> bytes:
        """
        Get content from IPFS by CID.

        Args:
            cid: Content Identifier (IPFS hash)

        Returns:
            File content as bytes
        """
        url = f"{self.INFURA_IPFS_URL}/cat"
        params = {'arg': cid}
        response = requests.post(url, headers=self.headers, params=params)

        if response.status_code != 200:
            raise Exception(f"IPFS download failed: {response.text}")

        return response.content

    def pin_file(self, cid: str) -> Dict[str, Any]:
        """
        Pin a file to keep it persistent on IPFS.

        Args:
            cid: Content Identifier to pin

        Returns:
            Pin response
        """
        url = f"{self.INFURA_IPFS_URL}/pin/add"
        params = {'arg': cid}
        response = requests.post(url, headers=self.headers, params=params)

        if response.status_code != 200:
            raise Exception(f"IPFS pin failed: {response.text}")

        return response.json()

    def get_gateway_url(self, cid: str) -> str:
        """
        Get public gateway URL for a CID.

        Args:
            cid: Content Identifier

        Returns:
            Public URL to access the content
        """
        return f"{self.INFURA_GATEWAY_URL}/{cid}"

    @staticmethod
    def is_valid_cid(cid: str) -> bool:
        """Check if a string looks like a valid IPFS CID."""
        # Basic validation: CIDv0 starts with Qm, CIDv1 starts with b
        if not cid:
            return False
        return cid.startswith('Qm') and len(cid) == 46 or cid.startswith('b')

"""Credential security, encryption, masking, and SSRF prevention for external data sources."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import socket
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.connectors.exceptions import SSRFSecurityError
from app.core.config import settings


class CredentialVault:
    """AES-256-GCM authenticated encryption for connector secrets."""

    def __init__(self, secret_key: str | None = None):
        key_source = (secret_key or settings.SECRET_KEY).encode("utf-8")
        # Derive 32-byte (256-bit) AES key via SHA-256
        self._derived_key = hashlib.sha256(key_source).digest()
        self._aesgcm = AESGCM(self._derived_key)

    def encrypt(self, data: dict[str, Any]) -> str:
        """Encrypt dictionary of secrets into a base64 string with a random 12-byte nonce."""
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        nonce = os.urandom(12)  # Standard GCM nonce size
        ciphertext = self._aesgcm.encrypt(nonce, json_bytes, None)
        # Combine nonce + ciphertext (which includes 16-byte auth tag)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, encrypted_str: str) -> dict[str, Any]:
        """Decrypt base64 string back into dictionary of secrets."""
        if not encrypted_str:
            return {}
        try:
            payload = base64.b64decode(encrypted_str.encode("utf-8"))
            if len(payload) < 28:  # 12 nonce + 16 auth tag minimum
                raise ValueError("Payload too short for AES-GCM")
            nonce = payload[:12]
            ciphertext = payload[12:]
            decrypted_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}") from e


vault = CredentialVault()


SENSITIVE_KEY_PATTERNS = {
    "password",
    "pass",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "private_key",
    "session_token",
    "auth_token",
    "uri",
    "conn_string",
    "connection_string",
}


def mask_credentials(data: dict[str, Any], mask_char: str = "•") -> dict[str, Any]:
    """Recursively mask sensitive values in configuration or credentials dict."""
    if not isinstance(data, dict):
        return data

    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pat in key_lower for pat in SENSITIVE_KEY_PATTERNS):
            if isinstance(value, str):
                if len(value) <= 6:
                    masked[key] = mask_char * 8
                else:
                    masked[key] = (mask_char * 8) + value[-4:]
            elif value is not None:
                masked[key] = mask_char * 8
            else:
                masked[key] = None
        elif isinstance(value, dict):
            masked[key] = mask_credentials(value, mask_char)
        elif isinstance(value, list):
            masked[key] = [
                mask_credentials(item, mask_char) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value

    return masked


class SSRFValidator:
    """Validates URLs against Server-Side Request Forgery risks."""

    BLOCKED_NETWORKS = [
        ipaddress.ip_network("0.0.0.0/8"),          # Current network
        ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
        ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space
        ipaddress.ip_network("127.0.0.0/8"),        # Loopback
        ipaddress.ip_network("169.254.0.0/16"),     # Link-Local
        ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
        ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
        ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
        ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
        ipaddress.ip_network("198.18.0.0/15"),      # Network Interconnect Device Benchmark
        ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
        ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
        ipaddress.ip_network("224.0.0.0/4"),        # Multicast
        ipaddress.ip_network("240.0.0.0/4"),        # Reserved
        ipaddress.ip_network("::1/128"),            # IPv6 Loopback
        ipaddress.ip_network("fc00::/7"),           # IPv6 Unique Local
        ipaddress.ip_network("fe80::/10"),          # IPv6 Link-Local
    ]

    @classmethod
    def validate_url(
        cls,
        url: str,
        allow_http: bool = False,
        allow_local: bool = False,
    ) -> str:
        """
        Validate URL for safe outbound requests.
        Raises SSRFSecurityError if URL is unsafe.
        Returns the parsed sanitized URL string.
        """
        if not url or not isinstance(url, str):
            raise SSRFSecurityError("Target URL is missing or empty.")

        parsed = urlparse(url.strip())

        if not parsed.scheme:
            raise SSRFSecurityError("URL must include an explicit protocol scheme (https://).")

        allowed_schemes = ["https"] if not allow_http else ["https", "http"]
        if parsed.scheme.lower() not in allowed_schemes:
            raise SSRFSecurityError(
                f"Protocol scheme '{parsed.scheme}' is prohibited. Only {allowed_schemes} are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityError("URL has no valid hostname.")

        if allow_local:
            return url

        # Resolve hostname to all associated IP addresses
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            raise SSRFSecurityError(f"Failed to resolve hostname '{hostname}': {str(e)}")

        resolved_ips: list[str] = [entry[4][0] for entry in addr_info]

        for ip_str in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                for blocked_net in cls.BLOCKED_NETWORKS:
                    if ip_obj in blocked_net:
                        raise SSRFSecurityError(
                            f"Host '{hostname}' resolves to restricted IP address '{ip_str}' within '{blocked_net}'."
                        )
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                    raise SSRFSecurityError(
                        f"Host '{hostname}' resolves to private/reserved IP '{ip_str}'."
                    )
            except ValueError:
                continue

        return url

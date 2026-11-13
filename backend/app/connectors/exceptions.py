"""Exceptions for external data source connectors."""

class ConnectorError(Exception):
    """Base exception for all connector operations."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConnectionAuthError(ConnectorError):
    """Authentication or permission failure connecting to external source."""
    pass


class ConnectionTimeoutError(ConnectorError):
    """Network timeout during connection or query execution."""
    pass


class ResourceNotFoundError(ConnectorError):
    """Requested database, schema, table, bucket, or endpoint not found."""
    pass


class QueryExecutionError(ConnectorError):
    """Failure executing discovery query or extraction operation."""
    pass


class SSRFSecurityError(ConnectorError):
    """SSRF risk detected in connection target."""
    pass


class DataExtractionError(ConnectorError):
    """Failure streaming or parsing records from external source."""
    pass


class SchemaDiscoveryError(ConnectorError):
    """Failure inspecting remote schema, columns, or types."""
    pass


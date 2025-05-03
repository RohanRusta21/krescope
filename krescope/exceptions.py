class KrescopeError(Exception):
    """Base exception for all krescope errors"""
    pass

class MetricsServerNotInstalled(KrescopeError):
    """Raised when metrics server is not available"""
    pass

class KubernetesConnectionError(KrescopeError):
    """Raised when connection to Kubernetes fails"""
    pass
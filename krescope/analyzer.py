from typing import Dict, List, Optional
from kubernetes.client import V1Pod, V1ResourceRequirements
from .models import PodRecommendation, ContainerRecommendation
from .exceptions import KrescopeError

class ResourceAnalyzer:
    SAFETY_BUFFER = 0.2  # 20% safety buffer
    
    @classmethod
    def _to_millicores(cls, value):
        """Convert CPU values to millicores."""
        try:
            if isinstance(value, str):
                if value.endswith("n"):
                    return float(value[:-1]) / 1_000_000  # nanocores to millicores
                elif value.endswith("m"):
                    return float(value[:-1])
                return float(value) * 1000  # cores to millicores
            return float(value)  # assume numeric is millicores
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def _to_megabytes(cls, value):
        """Convert memory values to megabytes."""
        try:
            if isinstance(value, str):
                if value.endswith("Ki"):
                    return float(value[:-2]) / 1024
                elif value.endswith("Mi"):
                    return float(value[:-2])
                elif value.endswith("Gi"):
                    return float(value[:-2]) * 1024
                return float(value) / (1024 * 1024)  # bytes to MiB
            return float(value) / (1024 * 1024)  # assume numeric is bytes
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def _generate_remarks(cls, container, metrics: Dict) -> List[str]:
        """Generate human-friendly recommendations."""
        remarks = []
        
        # CPU remarks
        cpu_usage = cls._to_millicores(metrics.get("cpu", "0m"))
        cpu_request = cls._to_millicores(container.resources.requests.get("cpu", "0m")) if hasattr(container, 'resources') and container.resources and container.resources.requests else 0
        
        if cpu_usage > cpu_request * 1.2:  # 20% over request
            remarks.append("Increase CPU request")
        elif cpu_request > 0 and cpu_usage < cpu_request * 0.5:  # Using less than half
            remarks.append("Decrease CPU request")
        
        # Memory remarks
        mem_usage = cls._to_megabytes(metrics.get("memory", "0Mi"))
        mem_request = cls._to_megabytes(container.resources.requests.get("memory", "0Mi")) if hasattr(container, 'resources') and container.resources and container.resources.requests else 0
        
        if mem_usage > mem_request * 1.2:
            remarks.append("Increase Memory request")
        elif mem_request > 0 and mem_usage < mem_request * 0.5:
            remarks.append("Decrease Memory request")
        
        return remarks or ["Optimal"]

    @classmethod
    def analyze_namespace(cls, k8s_client, namespace: str) -> List[PodRecommendation]:
        """Analyze all pods in a namespace."""
        try:
            pods = k8s_client.get_pods(namespace)
            metrics = k8s_client.get_pod_metrics(namespace)
            
            recommendations: List[PodRecommendation] = []
            for pod in pods:
                pod_metrics = metrics.get(pod.metadata.name, {})
                recommendations.append(cls.analyze_pod(pod, pod_metrics))
            
            return recommendations
        except Exception as e:
            raise KrescopeError(f"Analysis failed: {str(e)}")

    @classmethod
    def analyze_pod(cls, pod: V1Pod, metrics: Dict) -> PodRecommendation:
        """Analyze a single pod with proper null checks."""
        recommendation: PodRecommendation = {
            "name": pod.metadata.name,
            "containers": [],
            "warnings": []
        }
        
        if not pod.spec.containers:
            recommendation["warnings"].append("No containers found")
            return recommendation
        
        for container in pod.spec.containers:
            container_metrics = metrics.get(container.name, {})
            container_rec: ContainerRecommendation = {
                "name": container.name,
                "cpu": cls._analyze_cpu(container, container_metrics),
                "memory": cls._analyze_memory(container, container_metrics),
                "warnings": cls._get_container_warnings(container),
                "remarks": cls._generate_remarks(container, container_metrics),
                "current_usage": {
                    "cpu": container_metrics.get("cpu", "0m"),
                    "memory": container_metrics.get("memory", "0Mi")
                }
            }
            recommendation["containers"].append(container_rec)
        
        return recommendation

    @classmethod
    def _get_container_warnings(cls, container) -> List[str]:
        """Get warnings for container with null checks."""
        warnings = []
        if not hasattr(container, 'resources') or not container.resources:
            warnings.append("No resources specified")
            return warnings
            
        if not container.resources.requests:
            warnings.append("No resource requests set")
        if not container.resources.limits:
            warnings.append("No resource limits set")
        return warnings

    @classmethod
    def _analyze_cpu(cls, container, metrics: Dict) -> Dict[str, str]:
        """Analyze CPU resources with precise calculations"""
        # Initialize with defaults
        current_request = "0m"
        current_limit = "0m"
        current_usage = "0m"
        
        # Get actual usage from metrics
        if isinstance(metrics, dict):
            current_usage = metrics.get("cpu", "0m")
        
        # Get requests/limits
        if hasattr(container, 'resources') and container.resources:
            if container.resources.requests:
                current_request = container.resources.requests.get("cpu", "0m")
            if container.resources.limits:
                current_limit = container.resources.limits.get("cpu", "0m")

        usage_m = cls._to_millicores(current_usage)
        request_m = cls._to_millicores(current_request)
        
        # Calculate recommendation
        if usage_m > 1:  # Only recommend if usage > 1m
            recommended_m = max(usage_m * (1 + cls.SAFETY_BUFFER), 10)
            recommended_str = f"{recommended_m:.1f}m"
        else:
            recommended_m = 0
            recommended_str = "0m"
        
        savings_pct = ((request_m - recommended_m) / request_m * 100) if request_m > 0 else 0
        
        return {
            "current_request": current_request,
            "current_limit": current_limit,
            "current_usage": current_usage,
            "recommended_request": recommended_str,
            "savings_percent": f"{max(0, savings_pct):.1f}%",
            "limit_to_request_ratio": cls._calculate_ratio(current_limit, current_request)
        }

    @classmethod
    def _analyze_memory(cls, container, metrics: Dict) -> Dict[str, str]:
        """Analyze memory resources with precise calculations"""
        # Initialize with defaults
        current_request = "0Mi"
        current_limit = "0Mi"
        current_usage = "0Mi"
        
        # Get actual usage from metrics
        if isinstance(metrics, dict):
            current_usage = metrics.get("memory", "0Mi")
        
        # Get requests/limits
        if hasattr(container, 'resources') and container.resources:
            if container.resources.requests:
                current_request = container.resources.requests.get("memory", "0Mi")
            if container.resources.limits:
                current_limit = container.resources.limits.get("memory", "0Mi")

        usage_mb = cls._to_megabytes(current_usage)
        request_mb = cls._to_megabytes(current_request)
        
        # Calculate recommendation - round to nearest whole MiB
        if usage_mb >= 1:  # Only recommend if usage >= 1Mi
            recommended_mb = max(round(usage_mb * (1 + cls.SAFETY_BUFFER)), 1)
            recommended_str = f"{int(recommended_mb)}Mi"
        else:
            recommended_mb = 0
            recommended_str = "0Mi"
        
        savings_pct = ((request_mb - recommended_mb) / request_mb * 100) if request_mb > 0 else 0
        
        return {
            "current_request": current_request,
            "current_limit": current_limit,
            "current_usage": current_usage,
            "recommended_request": recommended_str,
            "savings_percent": f"{max(0, savings_pct):.1f}%",
            "limit_to_request_ratio": cls._calculate_ratio(current_limit, current_request)
        }
    
    @staticmethod
    def _calculate_ratio(limit: str, request: str) -> Optional[str]:
        """Calculate limit/request ratio with robust error handling."""
        try:
            if not limit or not request:
                return None
                
            def parse_value(v):
                if isinstance(v, str):
                    if v.endswith("m"):
                        return float(v[:-1]) / 1000
                    if v.endswith("n"):
                        return float(v[:-1]) / 1_000_000_000
                    return float(v)
                return float(v)
            
            limit_val = parse_value(limit)
            req_val = parse_value(request)
            
            if req_val == 0:
                return None
                
            return f"{limit_val/req_val:.2f}:1"
        except (ValueError, TypeError):
            return None



# from typing import Dict, List, Optional
# from kubernetes.client import V1Pod, V1ResourceRequirements
# from .models import PodRecommendation, ContainerRecommendation
# from .exceptions import KrescopeError

# class ResourceAnalyzer:
#     SAFETY_BUFFER = 0.2  # 20% safety buffer
    
#     @classmethod
#     def analyze_namespace(cls, k8s_client, namespace: str) -> List[PodRecommendation]:
#         """Analyze all pods in a namespace."""
#         try:
#             pods = k8s_client.get_pods(namespace)
#             metrics = k8s_client.get_pod_metrics(namespace)
            
#             recommendations: List[PodRecommendation] = []
#             for pod in pods:
#                 pod_metrics = metrics.get(pod.metadata.name, {})
#                 recommendations.append(cls.analyze_pod(pod, pod_metrics))
            
#             return recommendations
#         except Exception as e:
#             raise KrescopeError(f"Analysis failed: {str(e)}")

#     @classmethod
#     def analyze_pod(cls, pod: V1Pod, metrics: Dict) -> PodRecommendation:
#         """Analyze a single pod with proper null checks."""
#         recommendation: PodRecommendation = {
#             "name": pod.metadata.name,
#             "containers": [],
#             "warnings": []
#         }
        
#         if not pod.spec.containers:
#             recommendation["warnings"].append("No containers found")
#             return recommendation
        
#         for container in pod.spec.containers:
#             container_metrics = metrics.get(container.name, {})
#             container_rec: ContainerRecommendation = {
#                 "name": container.name,
#                 "cpu": cls._analyze_cpu(container, container_metrics),
#                 "memory": cls._analyze_memory(container, container_metrics),
#                 "warnings": cls._get_container_warnings(container)
#             }
#             recommendation["containers"].append(container_rec)
        
#         return recommendation

#     @classmethod
#     def _get_container_warnings(cls, container) -> List[str]:
#         """Get warnings for container with null checks."""
#         warnings = []
#         if not hasattr(container, 'resources') or not container.resources:
#             warnings.append("No resources specified")
#             return warnings
            
#         if not container.resources.requests:
#             warnings.append("No resource requests set")
#         if not container.resources.limits:
#             warnings.append("No resource limits set")
#         return warnings

#     @classmethod
#     def _analyze_cpu(cls, container, metrics: Dict) -> Dict[str, str]:
#         """Analyze CPU resources with precise calculations"""
#         # Initialize with defaults
#         current_request = "0m"
#         current_limit = "0m"
#         current_usage = "0m"
        
#         # Get actual usage from metrics
#         if isinstance(metrics, dict):
#             current_usage = metrics.get("cpu", "0m")
        
#         # Get requests/limits
#         if hasattr(container, 'resources') and container.resources:
#             if container.resources.requests:
#                 current_request = container.resources.requests.get("cpu", "0m")
#             if container.resources.limits:
#                 current_limit = container.resources.limits.get("cpu", "0m")

#         # Convert to millicores
#         def to_millicores(value):
#             try:
#                 if isinstance(value, str):
#                     if value.endswith("n"):
#                         return float(value[:-1]) / 1_000_000  # nanocores to millicores
#                     elif value.endswith("m"):
#                         return float(value[:-1])
#                     return float(value) * 1000  # cores to millicores
#                 return float(value)  # assume numeric is millicores
#             except (ValueError, TypeError):
#                 return 0.0

#         usage_m = to_millicores(current_usage)
#         request_m = to_millicores(current_request)
        
#         # Calculate recommendation
#         if usage_m > 1:  # Only recommend if usage > 1m
#             recommended_m = max(usage_m * (1 + cls.SAFETY_BUFFER), 10)
#             recommended_str = f"{recommended_m:.1f}m"
#         else:
#             recommended_m = 0
#             recommended_str = "0m"
        
#         savings_pct = ((request_m - recommended_m) / request_m * 100) if request_m > 0 else 0
        
#         return {
#             "current_request": current_request,
#             "current_limit": current_limit,
#             "current_usage": current_usage,
#             "recommended_request": recommended_str,
#             "savings_percent": f"{max(0, savings_pct):.1f}%",
#             "limit_to_request_ratio": cls._calculate_ratio(current_limit, current_request)
#         }

    
#     @classmethod
#     def _analyze_memory(cls, container, metrics: Dict) -> Dict[str, str]:
#         """Analyze memory resources with precise calculations"""
#         # Initialize with defaults
#         current_request = "0Mi"
#         current_limit = "0Mi"
#         current_usage = "0Mi"
        
#         # Get actual usage from metrics
#         if isinstance(metrics, dict):
#             current_usage = metrics.get("memory", "0Mi")
        
#         # Get requests/limits
#         if hasattr(container, 'resources') and container.resources:
#             if container.resources.requests:
#                 current_request = container.resources.requests.get("memory", "0Mi")
#             if container.resources.limits:
#                 current_limit = container.resources.limits.get("memory", "0Mi")

#         # Convert to megabytes
#         def to_megabytes(value):
#             try:
#                 if isinstance(value, str):
#                     if value.endswith("Ki"):
#                         return float(value[:-2]) / 1024
#                     elif value.endswith("Mi"):
#                         return float(value[:-2])
#                     elif value.endswith("Gi"):
#                         return float(value[:-2]) * 1024
#                     return float(value) / (1024 * 1024)  # bytes to MiB
#                 return float(value) / (1024 * 1024)  # assume numeric is bytes
#             except (ValueError, TypeError):
#                 return 0.0

#         usage_mb = to_megabytes(current_usage)
#         request_mb = to_megabytes(current_request)
        
#         # Calculate recommendation - round to nearest whole MiB
#         if usage_mb >= 1:  # Only recommend if usage >= 1Mi
#             recommended_mb = max(round(usage_mb * (1 + cls.SAFETY_BUFFER)), 1)
#             recommended_str = f"{int(recommended_mb)}Mi"
#         else:
#             recommended_mb = 0
#             recommended_str = "0Mi"
        
#         savings_pct = ((request_mb - recommended_mb) / request_mb * 100) if request_mb > 0 else 0
        
#         return {
#             "current_request": current_request,
#             "current_limit": current_limit,
#             "current_usage": current_usage,
#             "recommended_request": recommended_str,
#             "savings_percent": f"{max(0, savings_pct):.1f}%",
#             "limit_to_request_ratio": cls._calculate_ratio(current_limit, current_request)
#         }
    
    
#     @staticmethod
#     def _calculate_ratio(limit: str, request: str) -> Optional[str]:
#         """Calculate limit/request ratio with robust error handling."""
#         try:
#             if not limit or not request:
#                 return None
                
#             def parse_value(v):
#                 if isinstance(v, str):
#                     if v.endswith("m"):
#                         return float(v[:-1]) / 1000
#                     if v.endswith("n"):
#                         return float(v[:-1]) / 1_000_000_000
#                     return float(v)
#                 return float(v)
            
#             limit_val = parse_value(limit)
#             req_val = parse_value(request)
            
#             if req_val == 0:
#                 return None
                
#             return f"{limit_val/req_val:.2f}:1"
#         except (ValueError, TypeError):
#             return None
        
#     # In ResourceAnalyzer class, add these new methods:

#     @classmethod
#     def _generate_remarks(cls, container, metrics: Dict) -> List[str]:
#         """Generate human-friendly recommendations."""
#         remarks = []
        
#         # CPU remarks
#         cpu_usage = to_millicores(metrics.get("cpu", "0m"))
#         cpu_request = to_millicores(container.resources.requests.get("cpu", "0m")) if hasattr(container, 'resources') and container.resources else 0
        
#         if cpu_usage > cpu_request * 1.2:  # 20% over request
#             remarks.append("Increase CPU request")
#         elif cpu_usage < cpu_request * 0.5:  # Using less than half
#             remarks.append("Decrease CPU request")
        
#         # Memory remarks
#         mem_usage = to_megabytes(metrics.get("memory", "0Mi"))
#         mem_request = to_megabytes(container.resources.requests.get("memory", "0Mi")) if hasattr(container, 'resources') and container.resources else 0
        
#         if mem_usage > mem_request * 1.2:
#             remarks.append("Increase Memory request")
#         elif mem_usage < mem_request * 0.5:
#             remarks.append("Decrease Memory request")
        
#         return remarks or ["Optimal"]

#     # Update analyze_pod method to include remarks and usage:
#     @classmethod
#     def analyze_pod(cls, pod: V1Pod, metrics: Dict) -> PodRecommendation:
#         recommendation: PodRecommendation = {
#             "name": pod.metadata.name,
#             "containers": [],
#             "warnings": []
#         }
        
#         for container in pod.spec.containers:
#             container_metrics = metrics.get(container.name, {})
#             container_rec: ContainerRecommendation = {
#                 "name": container.name,
#                 "cpu": cls._analyze_cpu(container, container_metrics),
#                 "memory": cls._analyze_memory(container, container_metrics),
#                 "warnings": cls._get_container_warnings(container),
#                 "remarks": cls._generate_remarks(container, container_metrics),  # NEW
#                 "current_usage": {  # NEW
#                     "cpu": container_metrics.get("cpu", "0m"),
#                     "memory": container_metrics.get("memory", "0Mi")
#                 }
#             }
#             recommendation["containers"].append(container_rec)
        
#         return recommendation    
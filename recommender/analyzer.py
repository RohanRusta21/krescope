# analyzer.py
from datetime import datetime, timedelta
from typing import Dict, List

class ResourceAnalyzer:
    SAFETY_BUFFER = 0.2  # 20% safety buffer
    
    @classmethod
    def analyze_pod(cls, pod, metrics: Dict) -> Dict:
        recommendations = {
            "name": pod.metadata.name,
            "containers": [],
            "warnings": []
        }
        
        if not pod.spec.containers:
            recommendations["warnings"].append("No containers found in pod")
            return recommendations
        
        for container in pod.spec.containers:
            container_rec = {
                "name": container.name,
                "cpu": cls.analyze_cpu(container, metrics),
                "memory": cls.analyze_memory(container, metrics)
            }
            recommendations["containers"].append(container_rec)
        
        return recommendations

    @classmethod
    def analyze_cpu(cls, container, metrics: Dict) -> Dict:
        # Get current requests/limits
        requests = container.resources.requests or {}
        limits = container.resources.limits or {}
        current_request = requests.get("cpu", "0m")
        current_limit = limits.get("cpu", "0m")
        
        # Get actual usage
        usage = metrics.get(container.name, {}).get("cpu", "0m")
        
        # Convert to millicores for calculations
        def to_millicores(value):
            if isinstance(value, str):
                if value.endswith("m"):
                    return int(value[:-1])
                elif value.endswith("n"):
                    return int(value[:-1]) / 1_000_000
                return float(value) * 1000
            return float(value)
        
        usage_m = to_millicores(usage)
        request_m = to_millicores(current_request)
        
        # Calculate recommendation with safety buffer
        recommended_m = max(usage_m * (1 + cls.SAFETY_BUFFER), 100)  # At least 100m
        savings_pct = ((request_m - recommended_m) / request_m * 100) if request_m > 0 else 0
        
        return {
            "current_request": current_request,
            "current_limit": current_limit,
            "current_usage": usage,
            "recommended_request": f"{int(recommended_m)}m",
            "savings_percent": f"{max(0, savings_pct):.1f}%",
            "limit_to_request_ratio": cls._calculate_ratio(current_limit, current_request)
        }

    @classmethod
    def analyze_memory(cls, container, metrics: Dict) -> Dict:
        # Similar implementation for memory
        # ... (implementation omitted for brevity)
        pass

    @staticmethod
    def _calculate_ratio(limit, request):
        # Helper to calculate limit/request ratio
        pass
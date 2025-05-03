from typing import Dict, List, Optional, TypedDict

class ContainerRecommendation(TypedDict):
    name: str
    cpu: Dict[str, str]
    memory: Dict[str, str]
    warnings: List[str]
    remarks: List[str]  # NEW
    current_usage: Dict[str, str]  # NEW

class PodRecommendation(TypedDict):
    name: str
    containers: List[ContainerRecommendation]
    warnings: List[str]
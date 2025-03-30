# k8s_client.py
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from datetime import datetime, timedelta

class K8sClient:
    def __init__(self):
        self._load_config()
        self.core_v1 = client.CoreV1Api()
        self.metrics_client = client.CustomObjectsApi()
        
    def _load_config(self):
        try:
            config.load_kube_config()  # Local dev
        except:
            config.load_incluster_config()  # In-cluster
    
    def get_pod_metrics(self, namespace: str, pod_name: str = None) -> Dict:
        """Get CPU/memory metrics for pods"""
        try:
            metrics = self.metrics_client.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                name=pod_name
            )
            return self._process_metrics(metrics)
        except ApiException as e:
            if e.status == 404:
                raise MetricsServerNotInstalled("Metrics server not installed")
            raise
            
    def _process_metrics(self, raw_metrics: Dict) -> Dict:
        """Convert metrics to structured format"""
        result = {}
        for pod in raw_metrics.get('items', []):
            pod_name = pod['metadata']['name']
            result[pod_name] = {}
            for container in pod.get('containers', []):
                container_name = container['name']
                result[pod_name][container_name] = {
                    'cpu': container['usage'].get('cpu', '0m'),
                    'memory': container['usage'].get('memory', '0Mi')
                }
        return result
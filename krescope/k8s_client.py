from kubernetes import client, config
from kubernetes.client.rest import ApiException

class K8sClient:
    def __init__(self):
        try:
            config.load_kube_config()  # Local dev
        except:
            config.load_incluster_config()  # In-cluster
        
        self.core_v1 = client.CoreV1Api()
        self.metrics_client = None  # Will add later

    def get_pods(self, namespace):
        """Get all pods in a namespace."""
        try:
            return self.core_v1.list_namespaced_pod(namespace).items
        except ApiException as e:
            raise click.ClickException(f"K8s API error: {e.reason}")

    def get_pod_metrics(self, namespace):
        """Get CPU/memory metrics for pods (requires metrics-server)."""
        # Implement later
        pass
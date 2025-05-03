from typing import Dict, List, Optional
from kubernetes import client, config
from kubernetes.client import V1Pod
from kubernetes.client.rest import ApiException
import os
from .exceptions import MetricsServerNotInstalled, KrescopeError

class K8sClient:
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize the Kubernetes client with flexible configuration loading.
        
        Args:
            kubeconfig_path (Optional[str]): Path to kubeconfig file. If None, 
                it will attempt to load from default locations or in-cluster config.
        """
        try:
            # Attempt to load kubeconfig for local development
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            elif os.getenv("KUBECONFIG"):
                config.load_kube_config(config_file=os.getenv("KUBECONFIG"))
            else:
                config.load_kube_config()
        except Exception:
            try:
                # Fall back to in-cluster config for Kubernetes-native environments
                config.load_incluster_config()
            except Exception as e:
                raise KrescopeError(f"Failed to load Kubernetes configuration: {str(e)}")
        
        self.core_v1 = client.CoreV1Api()
        self.metrics_client = client.CustomObjectsApi()

    def get_pods(self, namespace: str) -> List[V1Pod]:
        """Get all pods in a namespace."""
        try:
            return self.core_v1.list_namespaced_pod(namespace).items
        except ApiException as e:
            raise KrescopeError(f"K8s API error while fetching pods: {e.reason}")

    def get_pod_metrics(self, namespace: str) -> Dict[str, Dict[str, str]]:
        """Get actual usage metrics from metrics-server."""
        try:
            metrics = self.metrics_client.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )
            return self._process_metrics(metrics) or {}
        except ApiException as e:
            if e.status == 404:
                raise MetricsServerNotInstalled("Metrics server is not installed or available.")
            raise KrescopeError(f"Error fetching pod metrics: {e.reason}")
        except Exception as e:
            raise KrescopeError(f"Unexpected error while fetching metrics: {str(e)}")

    def _process_metrics(self, raw_metrics: Dict) -> Dict[str, Dict[str, str]]:
        """Convert metrics to structured format with proper units."""
        result = {}
        if not raw_metrics or not isinstance(raw_metrics, dict):
            return result

        for pod in raw_metrics.get('items', []):
            if not pod or not isinstance(pod, dict):
                continue

            pod_name = pod.get('metadata', {}).get('name')
            if not pod_name:
                continue

            result[pod_name] = {}

            for container in pod.get('containers', []):
                if not container or not isinstance(container, dict):
                    continue

                container_name = container.get('name')
                if not container_name:
                    continue

                # Process CPU
                cpu = container.get('usage', {}).get('cpu', '0')
                try:
                    if isinstance(cpu, str):
                        if cpu.endswith('n'):
                            cpu_m = round(float(cpu[:-1]) / 1_000_000, 1)  # nanocores to millicores
                        elif cpu.endswith('m'):
                            cpu_m = float(cpu[:-1])
                        else:  # Assume cores
                            cpu_m = float(cpu) * 1000
                    else:  # Assume numeric is nanocores
                        cpu_m = round(float(cpu) / 1_000_000, 1)
                except (ValueError, TypeError):
                    cpu_m = 0.0

                # Process Memory
                memory = container.get('usage', {}).get('memory', '0')
                try:
                    if isinstance(memory, str):
                        if memory.endswith('Ki'):
                            memory_mi = float(memory[:-2]) / 1024
                        elif memory.endswith('Mi'):
                            memory_mi = float(memory[:-2])
                        elif memory.endswith('Gi'):
                            memory_mi = float(memory[:-2]) * 1024
                        else:  # Assume bytes
                            memory_mi = float(memory) / (1024 * 1024)
                    else:  # Assume bytes if numeric
                        memory_mi = float(memory) / (1024 * 1024)
                except (ValueError, TypeError):
                    memory_mi = 0.0

                result[pod_name][container_name] = {
                    'cpu': f"{cpu_m}m",
                    'memory': f"{int(round(memory_mi))}Mi"
                }

        return result

# from typing import Dict, List, Optional
# from kubernetes import client, config
# from kubernetes.client import V1Pod
# from kubernetes.client.rest import ApiException
# import os
# from .exceptions import MetricsServerNotInstalled, KrescopeError

# class K8sClient:
#     def __init__(self, kubeconfig_path: Optional[str] = None):
#         """
#         Initialize the Kubernetes client with flexible configuration loading.
        
#         Args:
#             kubeconfig_path (Optional[str]): Path to kubeconfig file. If None, 
#                 it will attempt to load from default locations or in-cluster config.
#         """
#         try:
#             # Attempt to load kubeconfig for local development
#             if kubeconfig_path:
#                 config.load_kube_config(config_file=kubeconfig_path)
#             elif os.getenv("KUBECONFIG"):
#                 config.load_kube_config(config_file=os.getenv("KUBECONFIG"))
#             else:
#                 config.load_kube_config()
#         except Exception:
#             try:
#                 # Fall back to in-cluster config for Kubernetes-native environments
#                 config.load_incluster_config()
#             except Exception as e:
#                 raise KrescopeError(f"Failed to load Kubernetes configuration: {str(e)}")
        
#         self.core_v1 = client.CoreV1Api()
#         self.metrics_client = client.CustomObjectsApi()

#     def get_pods(self, namespace: str) -> List[V1Pod]:
#         """Get all pods in a namespace."""
#         try:
#             return self.core_v1.list_namespaced_pod(namespace).items
#         except ApiException as e:
#             raise KrescopeError(f"K8s API error while fetching pods: {e.reason}")

#     def get_pod_metrics(self, namespace: str) -> Dict[str, Dict[str, str]]:
#         """Get actual usage metrics from metrics-server."""
#         try:
#             metrics = self.metrics_client.list_namespaced_custom_object(
#                 group="metrics.k8s.io",
#                 version="v1beta1",
#                 namespace=namespace,
#                 plural="pods"
#             )
#             return self._process_metrics(metrics) or {}
#         except ApiException as e:
#             if e.status == 404:
#                 raise MetricsServerNotInstalled("Metrics server is not installed or available.")
#             raise KrescopeError(f"Error fetching pod metrics: {e.reason}")
#         except Exception as e:
#             raise KrescopeError(f"Unexpected error while fetching metrics: {str(e)}")

#     def _process_metrics(self, raw_metrics: Dict) -> Dict[str, Dict[str, str]]:
#         """Convert metrics to structured format with proper units."""
#         result = {}
#         if not raw_metrics or not isinstance(raw_metrics, dict):
#             return result

#         for pod in raw_metrics.get('items', []):
#             if not pod or not isinstance(pod, dict):
#                 continue

#             pod_name = pod.get('metadata', {}).get('name')
#             if not pod_name:
#                 continue

#             result[pod_name] = {}

#             for container in pod.get('containers', []):
#                 if not container or not isinstance(container, dict):
#                     continue

#                 container_name = container.get('name')
#                 if not container_name:
#                     continue

#                 # Process CPU
#                 cpu = container.get('usage', {}).get('cpu', '0')
#                 try:
#                     if isinstance(cpu, str):
#                         if cpu.endswith('n'):
#                             cpu_m = round(float(cpu[:-1]) / 1_000_000, 1)  # nanocores to millicores
#                         elif cpu.endswith('m'):
#                             cpu_m = float(cpu[:-1])
#                         else:  # Assume cores
#                             cpu_m = float(cpu) * 1000
#                     else:  # Assume numeric is nanocores
#                         cpu_m = round(float(cpu) / 1_000_000, 1)
#                 except (ValueError, TypeError):
#                     cpu_m = 0.0

#                 # Process Memory
#                 memory = container.get('usage', {}).get('memory', '0')
#                 try:
#                     if isinstance(memory, str):
#                         if memory.endswith('Ki'):
#                             memory_mi = float(memory[:-2]) / 1024
#                         elif memory.endswith('Mi'):
#                             memory_mi = float(memory[:-2])
#                         elif memory.endswith('Gi'):
#                             memory_mi = float(memory[:-2]) * 1024
#                         else:  # Assume bytes
#                             memory_mi = float(memory) / (1024 * 1024)
#                     else:  # Assume bytes if numeric
#                         memory_mi = float(memory) / (1024 * 1024)
#                 except (ValueError, TypeError):
#                     memory_mi = 0.0

#                 result[pod_name][container_name] = {
#                     'cpu': f"{cpu_m}m",
#                     'memory': f"{int(round(memory_mi))}Mi"
#                 }

#         return result


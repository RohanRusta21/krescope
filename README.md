# Krescope - Kubernetes Resource Optimizer

🔍 **Analyze & optimize CPU/Memory requests/limits** in your Kubernetes clusters (EKS, AKS, GKE, etc.).

## 📦 Install
```sh
pip install krescope
```

## 📦 Install if metric-server not installed/enabled
```
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## 📌 Features
```sh
- Recommends optimal CPU/Memory requests & limits
- Works with EKS, AKS, GKE, and on-prem clusters
- Supports watch mode (--watch)
```

## 🚀 Usage
```
krescope analyze --namespace=default
```
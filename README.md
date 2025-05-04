# Krescope - Kubernetes Resource Optimizer

🔍 **Analyze & optimize CPU/Memory requests/limits** in your Kubernetes clusters (EKS, AKS, GKE, etc.).

## 📦 Install
```sh
pip install krescope
```

## 📦 Install if metric-server not installed/enabled
```sh
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## 📌 Features
```sh
- Recommends optimal CPU/Memory requests & limits
- Works with EKS, AKS, GKE, and on-prem clusters
- Supports watch mode (--watch)
```

## 🚀 Usage : To analyze cpu and memory limits/requests with current usage by application in specific namespace
```sh
krescope analyze --namespace=<your_namespace>
```

## 🚀 Usage : To analyze cpu and memory limits/requests with current usage by application in watch mode by giving custom time interval (in seconds)
```sh
krescope analyze --namespace=<your_namespace> --watch INTEGER
```

## 🚀 Usage : To get details in specific output format like json and text 
```sh
krescope analyze --namespace=<your_namespace> --output json
krescope analyze --namespace=<your_namespace> --output text
```

## 🚀 Usage : To get detailed information in verbose format
```sh
krescope analyze --verbose
```
# cli.py (partial update)
def analyze(namespace, output, verbose):
    k8s = K8sClient()
    try:
        metrics = k8s.get_pod_metrics(namespace)
    except MetricsServerNotInstalled:
        console.print("[red]Error:[/red] Metrics server not installed in cluster")
        if verbose:
            console.print("Install metrics server with: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
        return
        
    pods = k8s.get_pods(namespace)
    recommendations = [ResourceAnalyzer.analyze_pod(pod, metrics.get(pod.metadata.name, {})) 
                     for pod in pods]
    
    if output == "json":
        console.print_json(data=recommendations)
    else:
        _print_human_output(recommendations, verbose)

def _print_human_output(recommendations: List[Dict], verbose: bool):
    console.print(f"\n[bold]Resource Optimization Recommendations[/bold]")
    console.print(f"[dim]Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    
    for pod in recommendations:
        console.print(f"\n[cyan]Pod:[/cyan] {pod['name']}")
        
        for warning in pod.get('warnings', []):
            console.print(f"  [yellow]⚠ {warning}[/yellow]")
            
        for container in pod['containers']:
            console.print(f"  [bold]Container:[/bold] {container['name']}")
            
            # CPU Output
            cpu = container['cpu']
            console.print(f"    [bold]CPU:[/bold]")
            console.print(f"      Current: {cpu['current_request']} request, {cpu['current_limit']} limit")
            console.print(f"      Usage:   {cpu['current_usage']}")
            console.print(f"      [green]Recommend:[/green] {cpu['recommended_request']} (save {cpu['savings_percent']})")
            
            if verbose and cpu['limit_to_request_ratio']:
                console.print(f"      [dim]Limit/Request Ratio: {cpu['limit_to_request_ratio']}[/dim]")
import click
from rich.console import Console
from recommender.analyzer import analyze_namespace
from recommender.k8s_client import K8sClient

console = Console()

@click.group()
def cli():
    """K8s Resource Recommender - Optimize your Kubernetes resources."""
    pass

@cli.command()
@click.option("--namespace", default="default", help="Namespace to analyze")
@click.option("--output", type=click.Choice(["text", "json"]), default="text")
def analyze(namespace, output):
    """Analyze resource usage and suggest optimizations."""
    k8s = K8sClient()
    recommendations = analyze_namespace(k8s, namespace)
    
    if output == "json":
        console.print_json(data=recommendations)
    else:
        # Pretty-print with Rich
        console.print("[bold]Recommendations[/bold]")
        for pod in recommendations:
            console.print(f"\nPod: [cyan]{pod['name']}[/cyan]")
            console.print(f"  CPU: {pod['cpu']}")
            console.print(f"  Memory: {pod['memory']}")

@cli.command()
@click.option("--namespace", required=True, help="Namespace to audit")
def audit(namespace):
    """Audit resource limits/requests for security risks."""
    k8s = K8sClient()
    # Implement later
    pass

if __name__ == "__main__":
    cli()
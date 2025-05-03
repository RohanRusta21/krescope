from typing import List, Dict
from datetime import datetime
import click
from rich.console import Console
from rich.table import Table
from rich.box import SIMPLE
from .analyzer import ResourceAnalyzer
from .k8s_client import K8sClient
from .exceptions import MetricsServerNotInstalled, KrescopeError
from .models import PodRecommendation

console = Console()

@click.group()
def cli():
    """K8s Resource Recommender - Optimize your Kubernetes resources."""
    pass

@cli.command()
@click.option("--namespace", default="default", help="Namespace to analyze")
@click.option("--output", type=click.Choice(["text", "json"]), default="text")
@click.option("--verbose", is_flag=True, help="Show detailed information")
@click.option("--watch", is_flag=True, help="Continuously watch for changes")
def analyze(namespace, output, verbose, watch):
    """Analyze resource usage and suggest optimizations."""
    try:
        k8s = K8sClient()
        
        def run_analysis():
            recommendations = ResourceAnalyzer.analyze_namespace(k8s, namespace)
            if output == "json":
                console.print_json(data=recommendations)
            else:
                console.clear()  # Clear screen for watch mode
                _print_human_output(recommendations, verbose)

        if watch:
            import time
            console.print("[yellow]Watch mode enabled. Press Ctrl+C to stop.[/yellow]\n")
            while True:
                run_analysis()
                time.sleep(5)  # Update every 5 seconds
        else:
            run_analysis()
            
    except MetricsServerNotInstalled:
        console.print("[red]Error:[/red] Metrics server not installed in cluster", style="bold")
        console.print("Install it with: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
    except KrescopeError as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())

def _print_human_output(recommendations: List[PodRecommendation], verbose: bool):
    """Pretty-print recommendations using Rich."""
    console.print(f"\n[bold]Kubernetes Resource Recommendations[/bold]")
    console.print(f"[dim]Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    
    table = Table(box=SIMPLE, show_header=True, header_style="bold magenta")
    table.add_column("Pod")
    table.add_column("Container")
    table.add_column("CPU (Req → Rec)", justify="right")
    table.add_column("Mem (Req → Rec)", justify="right")
    table.add_column("Current Usage", justify="right")
    table.add_column("Remarks")
    
    for pod in recommendations:
        for container in pod['containers']:
            # Get values with fallbacks
            cpu_req = container['cpu'].get('current_request', '?')
            cpu_rec = container['cpu'].get('recommended_request', '?')
            mem_req = container['memory'].get('current_request', '?')
            mem_rec = container['memory'].get('recommended_request', '?')
            cpu_usage = container['current_usage'].get('cpu', '?')
            mem_usage = container['current_usage'].get('memory', '?')
            remarks = ", ".join(container.get('remarks', []))
            
            # Color coding for recommendations
            cpu_color = "red" if "Increase" in remarks else "green"
            mem_color = "red" if "Increase" in remarks else "green"
            
            table.add_row(
                pod['name'],
                container['name'],
                f"{cpu_req} → [{cpu_color}]{cpu_rec}[/{cpu_color}]",
                f"{mem_req} → [{mem_color}]{mem_rec}[/{mem_color}]",
                f"CPU: [cyan]{cpu_usage}[/cyan]\nMem: [cyan]{mem_usage}[/cyan]",
                "[yellow]" + remarks + "[/yellow]"
            )
            
            if verbose and container.get('warnings'):
                for warning in container['warnings']:
                    table.add_row("", f"[yellow]⚠ {warning}[/yellow]", "", "", "", "")
    
    console.print(table)

if __name__ == "__main__":
    cli()
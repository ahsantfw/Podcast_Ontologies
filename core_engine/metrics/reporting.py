"""
Reporting utilities for cost and performance metrics.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path
from datetime import datetime

from core_engine.metrics.cost_tracker import CostSummary, get_cost_tracker
from core_engine.metrics.performance_tracker import PerformanceSummary, get_performance_tracker


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{int(hours)}h {int(minutes)}m"


def format_cost(cost: float) -> str:
    """Format cost in USD."""
    if cost < 0.01:
        return f"${cost * 1000:.2f}¢"
    elif cost < 1:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


def format_tokens(tokens: int) -> str:
    """Format token count."""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1_000_000:
        return f"{tokens / 1000:.1f}K"
    else:
        return f"{tokens / 1_000_000:.2f}M"


def print_cost_report(summary: Optional[CostSummary] = None) -> None:
    """Print cost summary report."""
    if summary is None:
        summary = get_cost_tracker().get_summary()
    
    if summary.total_calls == 0:
        print("📊 No API calls tracked.")
        return
    
    print("\n" + "=" * 80)
    print("💰 COST REPORT")
    print("=" * 80)
    
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"  Total API Calls:     {summary.total_calls:,}")
    print(f"  Total Input Tokens:  {format_tokens(summary.total_input_tokens)}")
    print(f"  Total Output Tokens: {format_tokens(summary.total_output_tokens)}")
    print(f"  Total Cost:          {format_cost(summary.total_cost)}")
    print(f"  Total Duration:      {format_duration(summary.total_duration)}")
    
    if summary.total_duration > 0:
        calls_per_sec = summary.total_calls / summary.total_duration
        print(f"  Calls per Second:    {calls_per_sec:.2f}")
    
    if summary.by_model:
        print(f"\n📊 BY MODEL:")
        for model, stats in sorted(summary.by_model.items(), key=lambda x: x[1]["cost"], reverse=True):
            print(f"  {model}:")
            print(f"    Calls:      {stats['calls']:,}")
            print(f"    Input:      {format_tokens(stats['input_tokens'])}")
            print(f"    Output:     {format_tokens(stats['output_tokens'])}")
            print(f"    Cost:       {format_cost(stats['cost'])}")
            print(f"    Duration:   {format_duration(stats['duration'])}")
    
    if summary.by_operation:
        print(f"\n📊 BY OPERATION:")
        for op, stats in sorted(summary.by_operation.items(), key=lambda x: x[1]["cost"], reverse=True):
            print(f"  {op.upper()}:")
            print(f"    Calls:      {stats['calls']:,}")
            print(f"    Input:      {format_tokens(stats['input_tokens'])}")
            print(f"    Output:     {format_tokens(stats['output_tokens'])}")
            print(f"    Cost:       {format_cost(stats['cost'])}")
            print(f"    Duration:   {format_duration(stats['duration'])}")
    
    print("\n" + "=" * 80)


def print_performance_report(summary: Optional[PerformanceSummary] = None) -> None:
    """Print performance summary report."""
    if summary is None:
        summary = get_performance_tracker().get_summary()
    
    if summary.total_operations == 0:
        print("⚡ No operations tracked.")
        return
    
    print("\n" + "=" * 80)
    print("⚡ PERFORMANCE REPORT")
    print("=" * 80)
    
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"  Total Operations:      {summary.total_operations:,}")
    print(f"  Total Duration:        {format_duration(summary.total_duration)}")
    print(f"  Total Items Processed: {summary.total_items_processed:,}")
    if summary.overall_throughput:
        print(f"  Overall Throughput:    {summary.overall_throughput:.2f} items/sec")
    
    if summary.by_operation:
        print(f"\n📊 BY OPERATION:")
        for op_name, stats in sorted(summary.by_operation.items(), key=lambda x: x[1]["total_duration"], reverse=True):
            print(f"  {op_name}:")
            print(f"    Count:         {stats['count']:,}")
            print(f"    Total Time:    {format_duration(stats['total_duration'])}")
            print(f"    Items:         {stats['total_items']:,}")
            print(f"    Avg Duration:  {format_duration(stats['avg_duration'])}")
            if stats['avg_throughput'] > 0:
                print(f"    Avg Throughput: {stats['avg_throughput']:.2f} items/sec")
            if stats['min_duration'] != stats['max_duration']:
                print(f"    Min/Max:        {format_duration(stats['min_duration'])} / {format_duration(stats['max_duration'])}")
    
    print("\n" + "=" * 80)


def print_combined_report() -> None:
    """Print combined cost and performance report."""
    cost_summary = get_cost_tracker().get_summary()
    perf_summary = get_performance_tracker().get_summary()
    
    print("\n" + "=" * 80)
    print("📊 INGESTION METRICS REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    print_cost_report(cost_summary)
    print_performance_report(perf_summary)
    
    # Combined insights
    if cost_summary.total_calls > 0 and perf_summary.total_duration > 0:
        print("\n" + "=" * 80)
        print("💡 INSIGHTS")
        print("=" * 80)
        
        cost_per_minute = (cost_summary.total_cost / perf_summary.total_duration) * 60
        print(f"  Cost per Minute:      {format_cost(cost_per_minute)}")
        
        if perf_summary.total_items_processed > 0:
            cost_per_item = cost_summary.total_cost / perf_summary.total_items_processed
            print(f"  Cost per Item:        {format_cost(cost_per_item)}")
        
        if cost_summary.total_input_tokens > 0:
            tokens_per_second = cost_summary.total_input_tokens / perf_summary.total_duration
            print(f"  Tokens per Second:    {tokens_per_second:.0f}")
    
    print("\n" + "=" * 80)


def save_reports(output_dir: Path) -> None:
    """Save cost and performance reports to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save cost data
    cost_tracker = get_cost_tracker()
    cost_tracker.save(output_dir / f"cost_report_{timestamp}.json")
    
    # Save performance data
    perf_tracker = get_performance_tracker()
    perf_tracker.save(output_dir / f"performance_report_{timestamp}.json")
    
    # Save combined report
    report_path = output_dir / f"combined_report_{timestamp}.txt"
    with open(report_path, "w") as f:
        import sys
        from io import StringIO
        
        # Capture print output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        print_combined_report()
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        f.write(output)
    
    print(f"\n✅ Reports saved to: {output_dir}")
    print(f"  - Cost: {output_dir / f'cost_report_{timestamp}.json'}")
    print(f"  - Performance: {output_dir / f'performance_report_{timestamp}.json'}")
    print(f"  - Combined: {report_path}")


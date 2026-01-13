#!/usr/bin/env python3
"""
Benchmark script for the semantic code search system.

Compares performance against ripgrep baseline and measures:
- Index time
- Average search time
- P99 search time
"""
import time
import statistics
import subprocess
import sys
from pathlib import Path

from src.indexer import Indexer
from src.search import Searcher
from src.config import get_index_path


def format_time(seconds: float) -> str:
    """Format time in human-readable format."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    else:
        return f"{seconds:.2f}s"


def benchmark_indexing(project_path: Path) -> dict:
    """Benchmark indexing performance."""
    print("\n" + "=" * 60)
    print("INDEXING BENCHMARK")
    print("=" * 60)

    # Clean existing index
    index_path = get_index_path(project_path)
    if index_path.exists():
        import shutil
        shutil.rmtree(index_path)

    # Benchmark indexing
    indexer = Indexer(project_path, force=True)

    start_time = time.time()
    indexer.index()
    index_time = time.time() - start_time

    stats = {
        "index_time": index_time,
        "files_indexed": indexer.stats["files_indexed"],
        "chunks_created": indexer.stats["chunks_created"],
    }

    print(f"\n✅ Indexing completed")
    print(f"Files indexed:    {stats['files_indexed']}")
    print(f"Chunks created:   {stats['chunks_created']}")
    print(f"Total time:       {format_time(index_time)}")

    if stats["files_indexed"] > 0:
        avg_per_file = index_time / stats["files_indexed"]
        print(f"Avg per file:     {format_time(avg_per_file)}")

    return stats


def benchmark_search(project_path: Path, queries: list, num_runs: int = 10) -> dict:
    """Benchmark search performance."""
    print("\n" + "=" * 60)
    print("SEARCH BENCHMARK")
    print("=" * 60)

    searcher = Searcher(project_path)

    all_times = []
    results_per_query = {}

    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        query_times = []

        for i in range(num_runs):
            start_time = time.time()
            results = searcher.search(query, top_k=5)
            search_time = time.time() - start_time

            query_times.append(search_time)
            all_times.append(search_time)

            if i == 0:  # First run
                print(f"   Results found: {len(results)}")

        avg_time = statistics.mean(query_times)
        print(f"   Avg time: {format_time(avg_time)}")

        results_per_query[query] = {
            "times": query_times,
            "avg": avg_time,
        }

    # Calculate overall statistics
    stats = {
        "avg_search_time": statistics.mean(all_times),
        "median_search_time": statistics.median(all_times),
        "p99_search_time": statistics.quantiles(all_times, n=100)[98],
        "min_search_time": min(all_times),
        "max_search_time": max(all_times),
        "total_searches": len(all_times),
    }

    print("\n" + "-" * 60)
    print("OVERALL STATISTICS")
    print("-" * 60)
    print(f"Total searches:   {stats['total_searches']}")
    print(f"Avg time:         {format_time(stats['avg_search_time'])}")
    print(f"Median time:      {format_time(stats['median_search_time'])}")
    print(f"P99 time:         {format_time(stats['p99_search_time'])}")
    print(f"Min time:         {format_time(stats['min_search_time'])}")
    print(f"Max time:         {format_time(stats['max_search_time'])}")

    # Check if we meet the <100ms target
    target_ms = 100
    if stats['avg_search_time'] * 1000 < target_ms:
        print(f"\n✅ PASSED: Avg search time < {target_ms}ms")
    else:
        print(f"\n⚠️  MISSED TARGET: Avg search time > {target_ms}ms")

    return stats


def benchmark_ripgrep(project_path: Path, patterns: list) -> dict:
    """Benchmark ripgrep for comparison."""
    print("\n" + "=" * 60)
    print("RIPGREP BASELINE")
    print("=" * 60)

    # Check if ripgrep is installed
    try:
        subprocess.run(["rg", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  ripgrep not installed, skipping baseline")
        return {}

    all_times = []

    for pattern in patterns:
        print(f"\n🔍 Pattern: '{pattern}'")

        # Run ripgrep 5 times
        times = []
        for _ in range(5):
            start_time = time.time()
            subprocess.run(
                ["rg", "-l", pattern, str(project_path)],
                capture_output=True,
            )
            rg_time = time.time() - start_time
            times.append(rg_time)
            all_times.append(rg_time)

        avg_time = statistics.mean(times)
        print(f"   Avg time: {format_time(avg_time)}")

    if all_times:
        stats = {
            "avg_time": statistics.mean(all_times),
            "median_time": statistics.median(all_times),
        }

        print("\n" + "-" * 60)
        print(f"Avg ripgrep time: {format_time(stats['avg_time'])}")
        print(f"Median time:      {format_time(stats['median_time'])}")

        return stats

    return {}


def main():
    """Run all benchmarks."""
    # Get project path from args or use current directory
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1]).resolve()
    else:
        # Use the src directory as test project
        project_path = Path(__file__).parent / "src"

    if not project_path.exists():
        print(f"❌ Project path does not exist: {project_path}")
        sys.exit(1)

    print("\n🚀 Starting benchmarks")
    print(f"📁 Project: {project_path}")

    # Test queries
    queries = [
        "authentication",
        "database connection",
        "error handling",
        "API endpoint",
        "user management",
    ]

    # Ripgrep patterns (simpler, literal)
    rg_patterns = [
        "authenticate",
        "database",
        "error",
        "api",
        "user",
    ]

    try:
        # 1. Benchmark indexing
        index_stats = benchmark_indexing(project_path)

        # 2. Benchmark search
        search_stats = benchmark_search(project_path, queries, num_runs=10)

        # 3. Benchmark ripgrep
        rg_stats = benchmark_ripgrep(project_path, rg_patterns)

        # Final comparison
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)

        print("\nSemantic Search:")
        print(f"  Avg: {format_time(search_stats['avg_search_time'])}")
        print(f"  P99: {format_time(search_stats['p99_search_time'])}")

        if rg_stats:
            print("\nRipgrep (baseline):")
            print(f"  Avg: {format_time(rg_stats['avg_time'])}")

            speedup = rg_stats['avg_time'] / search_stats['avg_search_time']
            if speedup > 1:
                print(f"\n⚡ Semantic search is {speedup:.1f}x FASTER than ripgrep")
            else:
                print(f"\n⏱️  Semantic search is {1/speedup:.1f}x slower than ripgrep")
                print("   (but provides semantic understanding!)")

        print("\n" + "=" * 60)
        print("✅ Benchmark complete!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

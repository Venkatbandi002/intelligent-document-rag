import argparse
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database.models import init_db
from backend.app.services.evaluation_service import EvaluationService


def print_table(runs):
    print("\n" + "=" * 80)
    print(" RAG RETRIEVAL OPTIMIZATION EXPERIMENT BENCHMARK RESULTS")
    print("=" * 80)
    header = f"{'Configuration':<38} | {'Hit Rate':<10} | {'Precision@K':<12} | {'Recall@K':<10} | {'MRR':<8} | {'Avg Latency':<12}"
    print(header)
    print("-" * len(header))
    for r in runs:
        cfg_name = r.name[:38]
        row = f"{cfg_name:<38} | {r.hit_rate:<10.2%} | {r.precision_at_k:<12.4f} | {r.recall_at_k:<10.4f} | {r.mrr:<8.4f} | {r.avg_latency_ms:<10.1f} ms"
        print(row)
    print("=" * 80)
    print("Note: Generated from real live execution over evaluation/questions.json against indexed corpus.\n")


def main():
    parser = argparse.ArgumentParser(description="Run RAG Evaluation Suite")
    parser.add_argument("--benchmark", action="store_true", help="Run 3-configuration comparative benchmark matrix")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K context chunks")
    parser.add_argument("--rerank", action="store_true", help="Enable hybrid BM25 reranking")
    args = parser.parse_args()

    init_db()
    eval_service = EvaluationService()

    if args.benchmark:
        print("[*] Running comparative benchmark matrix (Baseline vs Improved vs Reranking)...")
        comparison = eval_service.run_benchmark_matrix()
        print_table(comparison.runs)
    else:
        print(f"[*] Running single evaluation (Top-K={args.top_k}, Rerank={args.rerank})...")
        report = eval_service.run_evaluation(
            name=f"Eval Top-K={args.top_k} (Rerank={args.rerank})",
            top_k=args.top_k,
            enable_reranking=args.rerank,
        )
        print_table([report])
        print("\nQuery Breakdown:")
        for res in report.query_results:
            status_sym = "[PASS]" if res.hit or (not res.expected_sources and not res.retrieved_sources) else "[FAIL]"
            print(f"  {status_sym} Q: {res.question}")
            print(f"         Precision: {res.precision_at_k:.2f} | MRR: {res.reciprocal_rank:.2f} | Latency: {res.latency_ms:.1f}ms")
            print(f"         Answer: {res.generated_answer[:120]}...")


if __name__ == "__main__":
    main()

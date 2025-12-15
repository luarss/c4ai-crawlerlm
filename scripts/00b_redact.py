import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString
from tqdm import tqdm

from src.qwen_utils import count_tokens


def get_text_content(element):
    """Extract all text from an element and its children."""
    if isinstance(element, NavigableString):
        return element.strip()
    return element.get_text(separator=" ", strip=True)


def calculate_text_coverage(element, target_text):
    """Calculate what percentage of target_text is contained in element."""
    element_text = get_text_content(element)
    if not element_text or not target_text:
        return 0.0

    # Word-based coverage - more accurate than character-based
    target_words = set(target_text.lower().split())
    element_words = set(element_text.lower().split())

    if not target_words:
        return 0.0

    overlap = target_words.intersection(element_words)
    return len(overlap) / len(target_words)


def find_minimal_fragment(soup, target_coverage=0.95):
    """
    Find the minimal HTML subtree that contains target_coverage of the text.

    Strategy:
    1. Extract full text from the document
    2. Traverse tree from root, finding smallest element with sufficient coverage
    3. Return that element's HTML
    """
    # Get the full text we're trying to capture
    full_text = soup.get_text(separator=" ", strip=True)

    if not full_text:
        # Empty document, return body or html
        return str(soup.body or soup.html or soup), {
            "element": soup.body or soup.html or soup,
            "coverage": 0.0,
            "tokens": 0,
            "text_length": 0,
            "depth": 0,
            "tag": "empty",
        }

    # Start with the root element
    root = soup.body or soup.html or soup

    # Find all candidate elements (non-NavigableString)
    candidates = []

    def traverse(element, depth=0):
        if isinstance(element, (NavigableString, Comment)):
            return

        # Calculate coverage for this element
        coverage = calculate_text_coverage(element, full_text)
        element_html = str(element)
        element_tokens = count_tokens(element_html)
        element_text = get_text_content(element)

        candidates.append(
            {
                "element": element,
                "coverage": coverage,
                "tokens": element_tokens,
                "text_length": len(element_text),
                "depth": depth,
                "tag": element.name,
            }
        )

        # Recurse into children
        for child in element.children:
            traverse(child, depth + 1)

    traverse(root)

    if not candidates:
        return str(root), {
            "element": root,
            "coverage": 1.0,
            "tokens": count_tokens(str(root)),
            "text_length": len(full_text),
            "depth": 0,
            "tag": root.name if hasattr(root, "name") else "unknown",
        }

    # Filter candidates with sufficient coverage
    sufficient = [c for c in candidates if c["coverage"] >= target_coverage]

    if not sufficient:
        # No element meets coverage requirement, return the best we have
        best = max(candidates, key=lambda x: x["coverage"])
        return str(best["element"]), best

    # Among sufficient candidates, choose the smallest by token count
    minimal = min(sufficient, key=lambda x: x["tokens"])

    return str(minimal["element"]), minimal


def process_html_files(input_dir, output_dir, target_coverage=0.95, dry_run=False):
    """Process all HTML files and extract minimal fragments."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_path.glob("*.html"))

    if not html_files:
        print(f"No HTML files found in {input_dir}")
        return []

    results = []
    print(f"Processing {len(html_files)} HTML files...")
    print(f"Target coverage: {target_coverage * 100:.1f}%")

    for html_file in tqdm(html_files, desc="Extracting minimal fragments"):
        # Read original HTML
        with open(html_file, encoding="utf-8", errors="replace") as f:
            original_html = f.read()

        # Parse and find minimal fragment
        soup = BeautifulSoup(original_html, "html.parser")
        minimal_html, info = find_minimal_fragment(soup, target_coverage)

        # Calculate statistics
        original_tokens = count_tokens(original_html)
        minimal_tokens = info["tokens"]
        reduction = (1 - minimal_tokens / original_tokens) * 100 if original_tokens > 0 else 0

        # Save minimal fragment
        if not dry_run:
            output_file = output_path / html_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(minimal_html)

        results.append(
            {
                "file": html_file.name,
                "schema_type": html_file.stem.split("_")[0],
                "original_tokens": original_tokens,
                "minimal_tokens": minimal_tokens,
                "reduction_pct": reduction,
                "coverage": info["coverage"],
                "selected_tag": info["tag"],
                "depth": info["depth"],
            }
        )

    # Print summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_original = sum(r["original_tokens"] for r in results)
    total_minimal = sum(r["minimal_tokens"] for r in results)
    avg_reduction = (1 - total_minimal / total_original) * 100 if total_original > 0 else 0
    avg_coverage = sum(r["coverage"] for r in results) / len(results) if results else 0

    print(f"Total files processed: {len(results)}")
    print("\nToken reduction:")
    print(f"  Total original: {total_original:,} tokens")
    print(f"  Total minimal: {total_minimal:,} tokens")
    print(f"  Average reduction: {avg_reduction:.1f}%")
    print(f"\nAverage text coverage: {avg_coverage * 100:.1f}%")

    # Breakdown by schema type
    schema_stats = {}
    for r in results:
        schema = r["schema_type"]
        if schema not in schema_stats:
            schema_stats[schema] = {"count": 0, "original_tokens": 0, "minimal_tokens": 0, "coverage_sum": 0}
        schema_stats[schema]["count"] += 1
        schema_stats[schema]["original_tokens"] += r["original_tokens"]
        schema_stats[schema]["minimal_tokens"] += r["minimal_tokens"]
        schema_stats[schema]["coverage_sum"] += r["coverage"]

    print("\nBreakdown by schema type:")
    for schema, stats in sorted(schema_stats.items()):
        count = stats["count"]
        orig = stats["original_tokens"]
        mini = stats["minimal_tokens"]
        reduction = (1 - mini / orig) * 100 if orig > 0 else 0
        avg_cov = stats["coverage_sum"] / count if count > 0 else 0
        print(f"  {schema:12s}: {count:3d} files, {reduction:5.1f}% reduction, {avg_cov * 100:5.1f}% coverage")

    # Save detailed results
    if not dry_run:
        results_file = output_path / "extraction_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to {results_file}")
        print(f"Minimal fragments saved to {output_path}/")
    else:
        print("\n[DRY RUN] No files were written")

    # Show examples of high reduction
    print("\nTop 10 files with highest reduction:")
    top_reductions = sorted(results, key=lambda x: x["reduction_pct"], reverse=True)[:10]
    for r in top_reductions:
        print(
            f"  {r['file']:30s}: {r['reduction_pct']:5.1f}% "
            f"({r['original_tokens']:6,} → {r['minimal_tokens']:6,} tokens, "
            f"tag={r['selected_tag']})"
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract minimal HTML fragments containing text content")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/seeds/candidates",
        help="Directory containing HTML files (default: data/seeds/candidates)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/seeds/minimal",
        help="Directory to save minimal fragments (default: data/seeds/minimal)",
    )
    parser.add_argument("--coverage", type=float, default=0.95, help="Target text coverage (0.0-1.0, default: 0.95)")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing files (for testing)")

    args = parser.parse_args()

    if not 0.0 <= args.coverage <= 1.0:
        print("Error: coverage must be between 0.0 and 1.0")
        return 1

    process_html_files(args.input_dir, args.output_dir, target_coverage=args.coverage, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    exit(main())

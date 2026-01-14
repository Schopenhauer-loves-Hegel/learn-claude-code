#!/usr/bin/env python3
"""
Helper script for Triton kernel verification.
Simplifies calling the TritonCopilotServer verification service.
"""
import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Server configuration
BASE_URL = "http://172.24.13.255:8890"
VENDOR = "offline/nvidia/0"
REQUEST_TIMEOUT = 300

# Verification endpoints
ENDPOINTS = {
    "triton": "/verify/triton",
    "test_func": "/verify/test_func",
    "benchmark_func": "/verify/benchmark_func",
}


async def verify_kernel(
    endpoint: str,
    data: Dict[str, Any],
    base_url: str = BASE_URL,
    vendor: str = VENDOR,
    timeout: int = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """
    Verify a kernel using the TritonCopilotServer.

    Args:
        endpoint: Verification endpoint ("triton", "test_func", or "benchmark_func")
        data: Verification data (see examples/)
        base_url: Server base URL
        vendor: Vendor prefix
        timeout: Request timeout in seconds

    Returns:
        Verification result dictionary
    """
    if endpoint not in ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint}. Available: {list(ENDPOINTS.keys())}")

    # Build full URL
    endpoint_path = ENDPOINTS[endpoint]
    if vendor:
        url = f"{base_url}/{vendor}{endpoint_path}"
    else:
        url = f"{base_url}{endpoint_path}"

    print(f"Sending verification request to: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = await response.json()
                return {
                    "status_code": response.status,
                    "success": response.status == 200,
                    "result": result
                }
    except asyncio.TimeoutError:
        return {
            "status_code": None,
            "success": False,
            "error": f"Request timeout after {timeout}s"
        }
    except Exception as e:
        return {
            "status_code": None,
            "success": False,
            "error": str(e)
        }


def load_example(example_name: str) -> Dict[str, Any]:
    """
    Load an example verification data file.

    Args:
        example_name: Name of the example (e.g., "verify_triton_example")

    Returns:
        Example data dictionary
    """
    examples_dir = Path(__file__).parent / "examples"
    example_file = examples_dir / f"{example_name}.json"

    if not example_file.exists():
        raise FileNotFoundError(f"Example not found: {example_file}")

    with open(example_file, 'r') as f:
        return json.load(f)


def print_result(result: Dict[str, Any], verbose: bool = False):
    """
    Print verification result in a readable format.

    Args:
        result: Verification result from verify_kernel()
        verbose: Whether to print detailed information
    """
    print("\n" + "="*60)
    print("Verification Result")
    print("="*60)

    if not result.get("success"):
        print(f"❌ Request failed: {result.get('error', 'Unknown error')}")
        return

    verification_result = result.get("result", {})

    # Main status
    op_name = verification_result.get("op_name", "N/A")
    success = verification_result.get("success", False)

    status_icon = "✓" if success else "✗"
    print(f"{status_icon} Operation: {op_name}")
    print(f"  Status: {'PASSED' if success else 'FAILED'}")

    # Test statistics
    info = verification_result.get("info", {})
    if info:
        total = info.get("total", 0)
        success_count = info.get("success", 0)
        failed = info.get("failed", 0)
        print(f"  Tests: {success_count}/{total} passed, {failed} failed")

    # Performance results
    speedup = verification_result.get("speedup")
    if speedup and isinstance(speedup, list) and len(speedup) > 0:
        print(f"\n  Performance Results:")
        for i, item in enumerate(speedup[:5]):
            if isinstance(item, dict):
                speedup_val = item.get("speedup", "N/A")
                params = item.get("params", {})
                if params != "avg":
                    print(f"    [{i+1}] Speedup: {speedup_val:.3f}x, Params: {params}")
                else:
                    print(f"    [Avg] Speedup: {speedup_val:.3f}x")
        if len(speedup) > 5:
            print(f"    ... and {len(speedup) - 5} more results")

    # Error details
    traceback = verification_result.get("traceback")
    if traceback:
        print(f"\n  Error Details:")
        error_lines = traceback.split('\n')
        if verbose:
            print("    " + "\n    ".join(error_lines))
        else:
            # Print last 5 lines
            print("    " + "\n    ".join(error_lines[-5:]))
            if len(error_lines) > 5:
                print(f"    ... ({len(error_lines) - 5} more lines, use --verbose to see all)")

    print("="*60)


async def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Triton Kernel Verification Helper")
    parser.add_argument(
        "endpoint",
        choices=list(ENDPOINTS.keys()),
        help="Verification endpoint"
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to JSON data file or example name (e.g., 'verify_triton_example')"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=BASE_URL,
        help=f"Server base URL (default: {BASE_URL})"
    )
    parser.add_argument(
        "--vendor",
        type=str,
        default=VENDOR,
        help=f"Vendor prefix (default: {VENDOR})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=REQUEST_TIMEOUT,
        help=f"Request timeout in seconds (default: {REQUEST_TIMEOUT})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed information"
    )

    args = parser.parse_args()

    # Load data
    if args.data:
        data_path = Path(args.data)
        if data_path.exists():
            # Load from file path
            with open(data_path, 'r') as f:
                data = json.load(f)
        else:
            # Try loading as example name
            try:
                data = load_example(args.data)
            except FileNotFoundError:
                print(f"Error: Data file not found: {args.data}")
                print(f"Available examples: verify_triton_example, verify_test_func_example, verify_benchmark_func_example")
                sys.exit(1)
    else:
        # Use default example for the endpoint
        example_map = {
            "triton": "verify_triton_example",
            "test_func": "verify_test_func_example",
            "benchmark_func": "verify_benchmark_func_example",
        }
        data = load_example(example_map[args.endpoint])
        print(f"Using default example: {example_map[args.endpoint]}")

    # Run verification
    result = await verify_kernel(
        endpoint=args.endpoint,
        data=data,
        base_url=args.base_url,
        vendor=args.vendor,
        timeout=args.timeout
    )

    # Print result
    print_result(result, verbose=args.verbose)

    # Exit with appropriate code
    if result.get("success") and result.get("result", {}).get("success"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

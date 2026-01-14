#!/usr/bin/env python3
"""
Helper script for Triton kernel verification.
Calls the TritonCopilotServer verification service and returns raw results.
"""
import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from typing import Dict, Any

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

    Returns the raw JSON response from the verification service.
    """
    if endpoint not in ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint}. Available: {list(ENDPOINTS.keys())}")

    # Build full URL
    endpoint_path = ENDPOINTS[endpoint]
    if vendor:
        url = f"{base_url}/{vendor}{endpoint_path}"
    else:
        url = f"{base_url}{endpoint_path}"

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
                    "url": url,
                    "result": result
                }
    except asyncio.TimeoutError:
        return {
            "status_code": None,
            "url": url,
            "error": f"Request timeout after {timeout}s"
        }
    except Exception as e:
        return {
            "status_code": None,
            "url": url,
            "error": str(e)
        }


def load_example(example_name: str) -> Dict[str, Any]:
    """Load an example verification data file."""
    examples_dir = Path(__file__).parent / "examples"
    example_file = examples_dir / f"{example_name}.json"

    if not example_file.exists():
        raise FileNotFoundError(f"Example not found: {example_file}")

    with open(example_file, 'r') as f:
        return json.load(f)


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

    args = parser.parse_args()

    # Load data
    if args.data:
        data_path = Path(args.data)
        if data_path.exists():
            with open(data_path, 'r') as f:
                data = json.load(f)
        else:
            try:
                data = load_example(args.data)
            except FileNotFoundError:
                print(f"Error: Data file not found: {args.data}", file=sys.stderr)
                print(f"Available examples: verify_triton_example, verify_test_func_example, verify_benchmark_func_example", file=sys.stderr)
                sys.exit(1)
    else:
        # Use default example for the endpoint
        example_map = {
            "triton": "verify_triton_example",
            "test_func": "verify_test_func_example",
            "benchmark_func": "verify_benchmark_func_example",
        }
        data = load_example(example_map[args.endpoint])

    # Run verification
    result = await verify_kernel(
        endpoint=args.endpoint,
        data=data,
        base_url=args.base_url,
        vendor=args.vendor,
        timeout=args.timeout
    )

    # Output raw JSON result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit with appropriate code
    if result.get("status_code") == 200:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

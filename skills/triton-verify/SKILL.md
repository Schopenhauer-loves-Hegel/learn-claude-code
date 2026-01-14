---
name: triton-verify
description: Verify Triton/Torch kernels, test functions, and benchmark functions using the TritonCopilotServer validation service.
---

# Triton Kernel Verification Skill

## Overview

This skill provides expertise in verifying Triton and PyTorch kernel implementations using the TritonCopilotServer validation service located at `/share/project/tj/workspace/TritonCopilotServer`.

The verification service can validate:
- **Triton kernels** against reference Torch implementations
- **Test functions** for correctness
- **Benchmark functions** for performance testing

## Server Configuration

- **Server URL**: `http://172.24.13.255:8890` (default, may need to be updated)
- **Vendor Prefix**: `offline/nvidia/0` (if applicable)
- **Timeout**: 300 seconds (default)

## Available Verification Endpoints

### 1. Verify Triton Kernel (`/verify/triton`)

Validates a Triton kernel implementation against a reference Torch implementation with test cases.

**Required Parameters:**
- `triton_kernel_name` (str): Name of the Triton kernel function
- `triton_kernel_code` (str): Complete Triton kernel implementation (including imports)
- `torch_kernel_name` (str): Name of the reference Torch kernel function
- `torch_kernel_code` (str): Reference Torch implementation
- `test_func_name` (str): Name of the test function
- `test_func_code` (str): Test code with `@parametrize` decorators
- `benchmark_func_name` (str, optional): Name of benchmark function
- `benchmark_func_code` (str, optional): Benchmark code
- `language` (str): Language code (e.g., "zh_CN", "en_US")

**Example Data Structure:**
```python
{
    "triton_kernel_name": "gather",
    "triton_kernel_code": "import torch\nimport triton\n...",
    "torch_kernel_name": "gather",
    "torch_kernel_code": "import torch\ndef gather(...)...",
    "test_func_name": "test_gather",
    "test_func_code": "@label('gather')\n@parametrize(...)\ndef test_gather(...)...",
    "benchmark_func_name": None,
    "benchmark_func_code": None,
    "language": "zh_CN"
}
```

### 2. Verify Test Function (`/verify/test_func`)

Validates a test function for correctness.

**Required Parameters:**
- `test_func_name` (str): Name of the test function
- `test_func_code` (str): Complete test function code
- `torch_kernel_name` (str): Name of the Torch kernel being tested
- `torch_kernel_code` (str): Torch kernel implementation

### 3. Verify Benchmark Function (`/verify/benchmark_func`)

Validates a performance benchmark function.

**Required Parameters:**
- `test_func_name` (str): Name of the benchmark function
- `test_func_code` (str): Complete benchmark function code
- `torch_kernel_name` (str): Name of the Torch kernel
- `torch_kernel_code` (str): Torch kernel implementation

## How to Use the Verification Service

### Method 1: Using the Helper Script (Recommended)

The skill includes `verify_helper.py` which provides an easy-to-use interface:

```bash
# Verify using built-in example
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton

# Verify with custom data file
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton --data /path/to/data.json

# Verify test function
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py test_func

# Verify benchmark function
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py benchmark_func
```

### Method 2: Programmatic Usage

To verify custom kernels programmatically, you need to:

1. **Prepare your data** in the correct format (see examples in `skills/triton-verify/examples/`)
2. **Send a POST request** to the verification endpoint
3. **Parse the results** to check if verification passed

Example using Python:
```python
import aiohttp
import asyncio

async def verify_triton_kernel(data):
    url = "http://172.24.13.255:8890/offline/nvidia/0/verify/triton"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=300)) as response:
            result = await response.json()
            return result

# Use the data from examples
data = {...}  # Load from examples
result = asyncio.run(verify_triton_kernel(data))
print(f"Verification {'passed' if result['success'] else 'failed'}")
```

## Understanding Verification Results

The verification service returns a JSON response with the following structure:

```python
{
    "op_name": str,           # Name of the operation verified
    "success": bool,          # True if verification passed, False otherwise
    "traceback": str | None,  # Error traceback if verification failed
    "params": dict,           # Test parameters used
    "speedup": list | None,   # Performance comparison results (if benchmark was run)
    "info": {
        "success": int,       # Number of successful test cases
        "failed": int,        # Number of failed test cases
        "total": int          # Total number of test cases
    },
    "code": str               # The verified code
}
```

**Key Fields:**
- **success**: Main indicator - `True` means all tests passed
- **info**: Detailed statistics about test execution
- **traceback**: If `success` is `False`, this contains the error details
- **speedup**: Performance comparison (only for benchmark functions)

## Common Verification Workflows

### Workflow 1: Verify a New Triton Kernel

1. **Write the Triton kernel** with proper imports
2. **Write a reference Torch implementation** for comparison
3. **Create test cases** using `@parametrize` decorators
4. **Prepare the verification data** (see examples)
5. **Run verification** using the test script or programmatically
6. **Check results** - if failed, examine the `traceback` field

### Workflow 2: Debug a Failing Kernel

1. **Run verification** to get the error traceback
2. **Analyze the traceback** to identify the issue
3. **Fix the kernel code**
4. **Re-run verification** to confirm the fix
5. **Iterate** until all tests pass

### Workflow 3: Performance Benchmarking

1. **Verify correctness first** using `/verify/triton`
2. **Add benchmark function** with performance tests
3. **Run verification with benchmark** to get speedup metrics
4. **Analyze speedup results** to evaluate performance

## Best Practices

### 1. Always Include Complete Code

```python
# ✅ Good - includes all imports
triton_kernel_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def my_kernel(...):
    ...
"""

# ❌ Bad - missing imports
triton_kernel_code = """
@triton.jit
def my_kernel(...):
    ...
"""
```

### 2. Use Comprehensive Test Cases

```python
# ✅ Good - tests multiple scenarios
@parametrize("M, N", [(32, 32), (64, 128), (1024, 2048)])
@parametrize("dtype", [torch.float16, torch.float32, torch.bfloat16])
def test_kernel(M, N, dtype):
    ...

# ❌ Bad - only one test case
def test_kernel():
    x = torch.randn(32, 32)
    ...
```

### 3. Check Verification Results Carefully

```python
result = verify_kernel(data)

if result['success']:
    print(f"✓ Verification passed: {result['info']['success']}/{result['info']['total']} tests")
    if result.get('speedup'):
        print(f"  Average speedup: {result['speedup'][-1]['speedup']:.2f}x")
else:
    print(f"✗ Verification failed: {result['info']['failed']}/{result['info']['total']} tests")
    print(f"  Error: {result['traceback']}")
```

### 4. Use Examples as Templates

The `skills/triton-verify/examples/` directory contains complete examples for each verification type. Use these as templates for your own verifications.

## Troubleshooting

### Issue: "Request timeout"
- **Cause**: Verification is taking too long (>300s)
- **Solution**: Reduce test case complexity or increase timeout

### Issue: "success: False" with traceback
- **Cause**: Kernel implementation has bugs
- **Solution**: Read the traceback carefully, fix the code, and re-verify

### Issue: "Connection refused"
- **Cause**: Server is not running or URL is incorrect
- **Solution**: Check if the server is running and update the BASE_URL in the test script

### Issue: Empty or missing fields in response
- **Cause**: Data format is incorrect
- **Solution**: Compare your data structure with the examples

## Examples

See the `examples/` directory for complete working examples:
- `verify_triton_example.json` - Example data for Triton kernel verification
- `verify_test_func_example.json` - Example data for test function verification
- `verify_benchmark_func_example.json` - Example data for benchmark function verification

## Quick Reference

**Verify Triton Kernel:**
```bash
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton
```

**Verify Test Function:**
```bash
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py test_func
```

**Verify Benchmark Function:**
```bash
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py benchmark_func
```

**Verify with custom data:**
```bash
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton --data /path/to/data.json
```

**Get help:**
```bash
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py --help
```

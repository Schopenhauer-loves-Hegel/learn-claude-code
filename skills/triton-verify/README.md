# Triton Verify Skill

This skill provides expertise in verifying Triton and PyTorch kernel implementations using the TritonCopilotServer validation service.

## Quick Start

### Using the Helper Script

```bash
# Verify using default example
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton

# Verify with custom data
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py triton --data /path/to/your/data.json

# Verify test function
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py test_func

# Verify benchmark function
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py benchmark_func

# Get help
python /share/project/tj/workspace/agent_exploration/learn-claude-code/skills/triton-verify/verify_helper.py --help
```

## Files

- **SKILL.md** - Complete skill documentation with usage examples
- **verify_helper.py** - Helper script for easy verification
- **examples/** - Example verification data files
  - `verify_triton_example.json` - Triton kernel verification example
  - `verify_test_func_example.json` - Test function verification example
  - `verify_benchmark_func_example.json` - Benchmark function verification example

## For Agent Usage

When an agent needs to verify a Triton kernel:

1. Load this skill using the Skill tool
2. Use the helper script or follow the patterns in SKILL.md
3. Check the verification results for success/failure

See SKILL.md for detailed documentation.

# C3: Python REPL Tool - User Guide

**Issue:** C3 - Python REPL Tool - Arbitrary Code Execution
**Implementation:** Environment Variable Based Conditional Loading
**Status:** Ready for Review

---

## Quick Start

### Python REPL Disabled (Default)

```bash
python src/app.py
```

Available tools:
- File management (read, write, delete files)
- Web search
- Wikipedia lookups
- Push notifications

**Python REPL:** NOT available (safe default)

---

### Python REPL Enabled (Requires Opt-In)

```bash
export ENABLE_PYTHON_REPL=true
python src/app.py
```

Available tools:
- File management (read, write, delete files)
- Web search
- Wikipedia lookups
- Push notifications
- **Python REPL (arbitrary code execution)**

**Warning:** ⚠️ Python REPL allows arbitrary code execution. Only enable in trusted environments.

---

## Configuration Methods

### Method 1: Command Line Export

```bash
# Enable Python REPL
export ENABLE_PYTHON_REPL=true
python src/app.py

# Or disable explicitly (default)
export ENABLE_PYTHON_REPL=false
python src/app.py
```

### Method 2: Inline Environment Variable

```bash
# Enable for this run only
ENABLE_PYTHON_REPL=true python src/app.py

# Disable for this run only
ENABLE_PYTHON_REPL=false python src/app.py
```

### Method 3: .env File

1. Edit `.env` file:
```bash
nano .env
```

2. Add or modify:
```
ENABLE_PYTHON_REPL=true
```

3. Save and restart app:
```bash
python src/app.py
```

### Method 4: Python Code (Not Recommended)

```python
import os
os.environ["ENABLE_PYTHON_REPL"] = "true"

# Then import and initialize
from sidekick import Sidekick
sidekick = Sidekick()
await sidekick.setup()
```

---

## Understanding the Warning

When you enable Python REPL, you'll see:

```
⚠️  Python REPL tool is ENABLED. This allows arbitrary code execution.
⚠️  Only enable this in trusted environments with trusted agents.
```

### What This Means

**"Arbitrary code execution":**
- The Python REPL can run ANY Python code
- Includes file system access
- Includes system command execution
- Includes network operations

**"Trusted environments":**
- Only use on your personal computer
- Only use if you trust the agents/LLM running it
- Don't use on shared servers
- Don't use with untrusted prompts

---

## Use Cases

### ✅ Good Use Cases (Enable Python REPL)

- **Personal Assistant:** Your own AI agent on your computer
- **Data Analysis:** Running calculations and processing
- **File Processing:** Complex file operations
- **System Tasks:** Automation scripts
- **Development:** Testing and debugging code

### ❌ Bad Use Cases (Keep Python REPL Disabled)

- **Shared Server:** Multiple users, potential untrusted agents
- **Production Environment:** Security-critical deployments
- **Untrusted Prompts:** User-submitted queries
- **Public API:** Exposed to internet users
- **Sandboxed Deployment:** Isolated/containerized environment

---

## Checking Your Configuration

### How to Verify Python REPL is Enabled

1. **Check Environment Variable:**
```bash
echo $ENABLE_PYTHON_REPL
# Output should be: true
```

2. **Check Logs:**
When you start the app, look for:
```
Adding Python REPL tool to available tools
```

3. **Test with Agent:**
Ask the agent to execute Python code. If it works, Python REPL is enabled.

### How to Verify Python REPL is Disabled

1. **Check Environment Variable:**
```bash
echo $ENABLE_PYTHON_REPL
# Output should be: false (or empty if not set)
```

2. **Check Logs:**
When you start the app, look for:
```
Python REPL tool is disabled (ENABLE_PYTHON_REPL=false)
```

3. **Test with Agent:**
Ask the agent to execute Python code. It should say it can't (Python REPL not available).

---

## Troubleshooting

### Problem: Python REPL Not Available

**Check 1: Is the environment variable set?**
```bash
echo $ENABLE_PYTHON_REPL
# If empty, it defaults to false
```

**Check 2: Is the value exactly "true"?**
```bash
# Correct:
export ENABLE_PYTHON_REPL=true

# Incorrect (will be disabled):
export ENABLE_PYTHON_REPL=yes
export ENABLE_PYTHON_REPL=1
export ENABLE_PYTHON_REPL=True
```

Note: "true" is case-insensitive (True, TRUE, true all work), but the value must be exactly "true".

**Check 3: Did you reload the app?**
```bash
# You must restart the app after changing the environment variable
# Kill the current process (Ctrl+C)
# Start it again with the new environment variable
```

### Problem: Python REPL is Unexpectedly Enabled

**Check 1: Review environment variables**
```bash
env | grep PYTHON_REPL
```

**Check 2: Review .env file**
```bash
cat .env | grep PYTHON_REPL
```

**Check 3: Disable explicitly**
```bash
export ENABLE_PYTHON_REPL=false
python src/app.py
```

### Problem: Getting "Can't execute Python"

**This is normal when Python REPL is disabled.**

The agent correctly identifies it can't execute Python code. This is the intended behavior for safety.

If you need Python execution:
```bash
export ENABLE_PYTHON_REPL=true
python src/app.py
```

---

## Security Best Practices

### ✅ DO:
- [ ] Only enable in personal/trusted environments
- [ ] Disable by default on shared systems
- [ ] Monitor logs when enabled
- [ ] Review agent responses
- [ ] Disable when not needed
- [ ] Use strong authentication for agents

### ❌ DON'T:
- [ ] Leave enabled on production servers
- [ ] Enable for untrusted users
- [ ] Use with untrusted prompts
- [ ] Enable on shared computers
- [ ] Commit "true" to version control
- [ ] Expose to internet without authentication

---

## FAQ

### Q: What happens if I enable Python REPL?

A: The agent will be able to execute arbitrary Python code. This is powerful but risky.

### Q: What if I forget to disable it?

A: Default is disabled. If you don't set `ENABLE_PYTHON_REPL=true`, it stays disabled.

### Q: Can I change the configuration without restarting?

A: No. You must restart the app to pick up new environment variables.

### Q: Will other tools work without Python REPL?

A: Yes. File management, web search, Wikipedia, and notifications all work regardless.

### Q: Can I disable Python REPL for just one query?

A: No. It's an all-or-nothing setting per app instance.

### Q: Is Python REPL enabled by default?

A: No. It's **disabled by default** for safety.

### Q: What if the value is misspelled?

A: It will be treated as disabled. Only "true" (case-insensitive) enables it.

### Q: Can I enable it in code instead of environment variables?

A: Technically yes, but not recommended. Environment variables are clearer.

### Q: Will my data be secure with Python REPL enabled?

A: The Python REPL has access to everything the app process has access to. Be careful.

### Q: Can I use Python REPL to access other users' files?

A: If the app runs as root/admin and Python REPL is enabled, yes. Avoid this setup.

---

## Related Documentation

- **C3_PYTHON_REPL_CONDITIONAL.md** - Technical implementation details
- **IMPLEMENTATION_STEPS.md** - Step-by-step implementation walkthrough
- **TESTING_DETAILS.md** - Test coverage and verification
- **FINAL_SUMMARY.txt** - Executive summary

---

## Support

For issues or questions:

1. Check the FAQ above
2. Review the logs (look for "Python REPL" messages)
3. Verify environment variable: `echo $ENABLE_PYTHON_REPL`
4. Check documentation in improvements/C3_Python_REPL_Tool/

---

## Summary

- **Python REPL is disabled by default** (safe)
- **Enable with:** `export ENABLE_PYTHON_REPL=true`
- **Disable with:** `export ENABLE_PYTHON_REPL=false` (or don't set it)
- **Requires restart** to take effect
- **Only "true" enables** it (case-insensitive, but must be exact)
- **⚠️ Use carefully** - arbitrary code execution is powerful and risky

---

**Version:** 1.0
**Last Updated:** November 14, 2025
**Status:** Ready for Production

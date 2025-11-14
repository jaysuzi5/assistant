# H6: Missing Logging Framework - Technical Details

## Python Logging Architecture

This section explains the technical details of the logging framework implementation.

### Python Logging Hierarchy

Python's logging system uses a hierarchical structure:

```
root logger
├── sidekick (level: DEBUG)
│   ├── sidekick.worker
│   ├── sidekick.evaluator
│   └── sidekick.tools
├── app (level: DEBUG)
├── validation (level: DEBUG)
├── langchain (level: WARNING)
│   ├── langchain.core
│   └── langchain.community
└── gradio (level: WARNING)
```

**Hierarchy Benefits**:
- Child loggers inherit parent's level
- Can configure specific modules without affecting others
- Logging propagates up the hierarchy by default
- Allows fine-grained control

### Handler Architecture

The logging framework uses two handlers:

#### Console Handler (StreamHandler)

```python
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(self.log_level.value)  # Default: INFO
console_formatter = ColoredFormatter(fmt="%(levelname)s | %(name)s | %(message)s")
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)
```

**Properties**:
- Destination: stdout (shows in terminal)
- Level: Configurable (default INFO)
- Format: Simple with colors
- No buffering issues

#### File Handler (RotatingFileHandler)

```python
file_handler = logging.handlers.RotatingFileHandler(
    filename=log_file,
    maxBytes=self.max_bytes,        # Default: 10MB
    backupCount=self.backup_count,  # Default: 5
)
file_handler.setLevel(logging.DEBUG)  # Always capture everything
file_formatter = StructuredFormatter(fmt="%(asctime)s | %(levelname)s | %(name)s | ...")
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)
```

**Properties**:
- Destination: logs/sidekick.log
- Level: Always DEBUG (captures everything)
- Format: Structured with full context
- Rotation: Automatic size-based

### Handler Propagation

When a log message is created:

1. **Logger receives message**: `logger.info("Hello")`
2. **Logger processes message**:
   - Checks if logger level allows this message
   - Creates LogRecord with timestamp, level, message, etc.
3. **Handlers process LogRecord**:
   - Console handler: Checks level, formats with colors, outputs to stdout
   - File handler: Checks level, formats with structure, writes to file
4. **Propagation**: Message propagates to parent loggers
   - Child logger handlers run first
   - Parent logger handlers run next (unless propagate=False)

### Filter Chain

Log level filtering occurs at multiple points:

```python
# 1. Logger level check (prevents creating LogRecord)
if logger.level > record.levelno:
    return None

# 2. Handler level check (additional filtering)
if handler.level > record.levelno:
    return None

# 3. Handler filters (custom filter objects)
if not handler.filter(record):
    return None

# 4. Formatter (does NOT filter, only formats)
formatted = formatter.format(record)

# 5. Handler emit (finally output)
handler.emit(formatted)
```

**Efficiency**:
- Early filtering prevents unnecessary LogRecord creation
- Handler-level filtering allows different outputs at different levels
- Propagation can be controlled per logger

## File Rotation Mechanics

### RotatingFileHandler Behavior

The `RotatingFileHandler` automatically rotates logs when size threshold is reached.

```python
handler = RotatingFileHandler(
    filename="logs/sidekick.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5                # Keep 5 backups
)
```

### Rotation Process

When file size reaches maxBytes:

1. **Before rotation**:
   ```
   sidekick.log       (10.0 MB) ← size limit reached
   sidekick.log.1     (10.0 MB)
   sidekick.log.2     (10.0 MB)
   sidekick.log.3     (10.0 MB)
   sidekick.log.4     (10.0 MB)
   sidekick.log.5     (10.0 MB)
   ```

2. **Rotation occurs** (handler.doRollover()):
   ```
   # Rename files in reverse order
   sidekick.log.5  → deleted
   sidekick.log.4  → sidekick.log.5
   sidekick.log.3  → sidekick.log.4
   sidekick.log.2  → sidekick.log.3
   sidekick.log.1  → sidekick.log.2
   sidekick.log    → sidekick.log.1

   # Create new sidekick.log
   sidekick.log    (empty, 0 bytes)
   ```

3. **After rotation**:
   ```
   sidekick.log       (0 bytes)   ← new empty file
   sidekick.log.1     (10.0 MB)   ← most recent rollover
   sidekick.log.2     (10.0 MB)
   sidekick.log.3     (10.0 MB)
   sidekick.log.4     (10.0 MB)
   sidekick.log.5     (10.0 MB)   ← oldest kept
   ```

### Thread Safety

RotatingFileHandler uses locks for thread-safe operations:
```python
# Internal locking
self.lock = threading.RLock()

def emit(self, record):
    try:
        self.acquire()  # Thread lock
        # Check if rotation needed
        if self.shouldRollover(record):
            self.doRollover()
        # Write message
        ...
    finally:
        self.release()  # Release lock
```

**Guarantees**:
- Multiple threads can safely log simultaneously
- File rotation doesn't corrupt logs
- No messages lost during rotation

## Color Code Implementation

### ANSI Color Codes

The `ColoredFormatter` uses ANSI escape codes for terminal colors:

```python
COLORS = {
    logging.DEBUG: "\033[36m",      # Cyan (bright information)
    logging.INFO: "\033[32m",       # Green (positive action)
    logging.WARNING: "\033[33m",    # Yellow (caution)
    logging.ERROR: "\033[31m",      # Red (problem)
    logging.CRITICAL: "\033[41m",   # Red background (urgent)
}
RESET = "\033[0m"  # Reset to default
```

**Format**:
- `\033[` = Escape character
- `3Xm` = Color code (36=cyan, 32=green, etc.)
- `41m` = Background color (red)

**Example Output**:
```
\033[32m INFO \033[0m | sidekick | Application started
 └─────────┬──────────┘
           └─ This text appears in green
```

### Terminal Support

ANSI color codes work in:
- ✅ macOS Terminal
- ✅ Linux Terminal
- ✅ Windows PowerShell (Windows 10+)
- ✅ VS Code integrated terminal
- ✅ GitHub Actions logs
- ❌ Plain text files (escape codes visible)
- ❌ Log aggregation services (colors stripped)

**Detection**:
```python
# Detect if terminal supports colors
import sys
if sys.stdout.isatty():
    # Terminal supports colors
    use_colors = True
else:
    # Piped to file or non-interactive
    use_colors = False
```

Our implementation always outputs colors (can be disabled if needed).

## Structured Logging Format

### Format String

```
%(asctime)s | %(levelname)8s | %(name)-25s | %(funcName)s:%(lineno)d | %(message)s
```

**Components**:
- `%(asctime)s`: Timestamp in format specified by datefmt
- `%(levelname)8s`: Level padded to 8 chars (right-aligned)
- `%(name)-25s`: Logger name padded to 25 chars (left-aligned)
- `%(funcName)s`: Function name where log was called
- `%(lineno)d`: Line number (decimal)
- `%(message)s`: The log message

### Example Output

```
2025-11-14 10:30:45 | INFO     | sidekick              | setup:220 | LLM initialized
2025-11-14 10:30:46 | DEBUG    | sidekick              | worker:300 | Tool call: search
2025-11-14 10:30:47 | WARNING  | sidekick_tools        | search:450 | Timeout, retrying
2025-11-14 10:30:48 | ERROR    | app                   | process:150 | Task failed
```

**Advantages**:
- Fixed-width columns align for easy reading
- Timestamp always first (sortable)
- Level visible at consistent position
- Function name for source location
- Exception tracebacks automatically included

## LogRecord Attributes

When logging occurs, Python creates a LogRecord with these attributes:

```python
record = LogRecord(
    name="sidekick.worker",        # Logger name
    level=logging.INFO,             # Log level
    pathname="/src/sidekick.py",   # Full file path
    lineno=300,                     # Line number
    msg="Task completed",           # Message (before formatting)
    args=(),                        # Message arguments
    exc_info=None,                  # Exception tuple (if any)
    func="worker",                  # Function name
    sinfo=None,                     # Stack info
    # Plus 20+ other attributes...
)
```

**Custom Attributes**:
```python
# Add custom fields
logger.info("Operation complete", extra={
    "duration_ms": 1234,
    "status": "success",
    "items_processed": 100,
})

# Accessible in formatter
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Access extra fields
        duration = getattr(record, 'duration_ms', 'N/A')
        status = getattr(record, 'status', 'N/A')
        return f"{record.getMessage()} [{duration}ms] ({status})"
```

## Module-Level Configuration

### Configuration in setup_logging()

```python
def _configure_module_loggers(self) -> None:
    # Sidekick modules - DEBUG for development visibility
    sidekick_modules = [
        "sidekick", "sidekick_tools", "validation",
        "tool_error_handler", "llm_invocation", "app"
    ]
    for module in sidekick_modules:
        logging.getLogger(module).setLevel(logging.DEBUG)

    # External libraries - WARNING only
    external_modules = [
        "langchain", "gradio", "urllib3", "asyncio"
    ]
    for module in external_modules:
        logging.getLogger(module).setLevel(logging.WARNING)
```

### Hierarchy Inheritance

```
Level Hierarchy:
root logger (INFO)
├── sidekick (DEBUG) - explicitly set
│   ├── sidekick.worker (inherits DEBUG)
│   ├── sidekick.evaluator (inherits DEBUG)
│   └── sidekick.tools (inherits DEBUG)
├── validation (DEBUG) - explicitly set
└── langchain (WARNING) - explicitly set
    ├── langchain.core (inherits WARNING)
    └── langchain.community (inherits WARNING)
```

**Effect**:
- `logger = get_logger("sidekick.worker")`: Inherits DEBUG level
- `logger = get_logger("sidekick.tools.search")`: Inherits DEBUG level
- `logger = get_logger("langchain.core.memory")`: Inherits WARNING level

## Exception Logging

### Standard Exception Logging

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True)
```

**What happens**:
1. LogRecord created with exception info
2. Formatter calls `formatException()`
3. Full traceback included in log

**File output**:
```
2025-11-14 10:30:45 | ERROR    | app | process:100 | Operation failed
Traceback (most recent call last):
  File "/src/app.py", line 42, in process_message
    result = await sidekick.run_superstep(message)
  File "/src/sidekick.py", line 560, in run_superstep
    response = self.worker_llm_with_tools.invoke(state)
  File "/venv/lib/langchain/llm.py", line 123, in invoke
    return self._invoke(input)
RuntimeError: API request failed: Connection timeout
```

### Exception Chaining

```python
try:
    inner_operation()
except ValueError as e:
    try:
        recovery_operation()
    except Exception as recovery_error:
        logger.error("Recovery failed", exc_info=True)
        # Logs both exceptions and traceback chain
```

## Performance Profiling

### Logging Overhead

Typical costs per log call:

| Operation | Time | Notes |
|-----------|------|-------|
| Logger level check | < 0.1μs | Fast path (doesn't create LogRecord) |
| LogRecord creation | 1-5μs | More expensive |
| Console formatting | 5-20μs | ColoredFormatter adds minimal cost |
| Console output | 10-100μs | I/O dependent |
| File formatting | 5-20μs | StructuredFormatter similar cost |
| File write | 50-200μs | Disk I/O (buffered by OS) |

**Bottleneck**: Disk I/O (file writes), not formatting or level checking

### Optimization Strategies

1. **Use appropriate levels**: DEBUG logs in development, INFO in production
2. **Avoid string interpolation**: Use `logger.info("x=%s", x)` not `logger.info(f"x={x}")`
3. **Batch similar logs**: Log once with context, not repeatedly
4. **Disable verbose loggers**: Set external libraries to WARNING level

### Benchmarks

Typical application logging rates:
- **Development**: 100-1000 logs/second (DEBUG level)
- **Production**: 10-100 logs/second (INFO level)
- **Peak load**: Can handle 10000+ logs/second (with buffering)

File rotation at 10MB/file handles:
- ~10 log messages per second × 86400 seconds/day = ~860k messages/day
- ~500MB logs per day with current format
- Rotation every 1-2 days on typical application

## Testing Implementation

### Test Organization

```
tests/test_logging_framework_h6.py
├── TestLoggingConfigInitialization (6 tests)
├── TestLogLevel (2 tests)
├── TestColoredFormatter (3 tests)
├── TestStructuredFormatter (2 tests)
├── TestLoggingConfiguration (3 tests)
├── TestFileRotation (4 tests)
├── TestSetupLoggingFunction (3 tests)
├── TestGetLoggerFunction (3 tests)
├── TestGetLoggingConfigFunction (2 tests)
├── TestLoggingIntegration (3 tests)
├── TestLoggingErrorHandling (2 tests)
├── TestEnvironmentVariables (2 tests)
└── TestBackwardCompatibility (2 tests)

Total: 37 tests, all passing ✅
```

### Test Patterns

**Isolation with TemporaryDirectory**:
```python
def test_logging_config_creates_log_directory(self) -> None:
    with TemporaryDirectory() as temp_dir:
        log_dir = os.path.join(temp_dir, "logs")
        config = LoggingConfig(log_dir=log_dir)
        assert os.path.exists(log_dir)
```

**File Content Verification**:
```python
def test_logging_to_file(self) -> None:
    with TemporaryDirectory() as temp_dir:
        config = setup_logging(log_dir=temp_dir)
        logger = get_logger("test")
        logger.info("Test message")

        with open(config.get_log_file_path()) as f:
            assert "Test message" in f.read()
```

**State Management**:
```python
def test_get_logger_without_setup_initializes(self) -> None:
    import logging_config
    original = logging_config._logging_config
    logging_config._logging_config = None

    try:
        logger = get_logger("test")
        assert logging_config._logging_config is not None
    finally:
        logging_config._logging_config = original
```

## Thread Safety

### Logging Thread Safety

Python's logging module is thread-safe by design:

```python
# Multiple threads can safely call logger methods
import threading

def worker(logger, message):
    logger.info(message)

logger = get_logger(__name__)

threads = [
    threading.Thread(target=worker, args=(logger, f"Message {i}"))
    for i in range(10)
]

for t in threads:
    t.start()
for t in threads:
    t.join()
# No lost messages, no corruption
```

**Thread Safety Guarantees**:
- Logger methods are reentrant (same thread can call recursively)
- Handler emit() is protected with locks
- File writes are atomic
- No message loss during log rotation

### Async Safety

The logging module works with asyncio but has considerations:

```python
import asyncio
import logging

async def async_worker(logger):
    logger.info("Starting async work")
    await asyncio.sleep(1)
    logger.info("Async work complete")

async def main():
    logger = get_logger(__name__)
    await asyncio.gather(
        async_worker(logger),
        async_worker(logger),
    )

asyncio.run(main())
```

**Considerations**:
- Logging calls are blocking (briefly)
- For high-throughput async apps, consider QueueHandler
- Current implementation suitable for typical applications

## Integration with Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Logstash Configuration**:
```
input {
  file {
    path => "/app/logs/sidekick.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" =>
      "%{TIMESTAMP_ISO8601:timestamp} \| %{LOGLEVEL:level} \| %{DATA:logger} \| %{DATA:function}:%{INT:line} \| %{GREEDYDATA:msg}"
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
  }
}
```

### CloudWatch Logs

**AWS CloudWatch Agent**:
```
[/app/logs/sidekick.log]
log_group_name = /app/sidekick
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S
file = /app/logs/sidekick.log
```

### Splunk

**Splunk Forwarder inputs.conf**:
```
[monitor:///app/logs/sidekick.log]
sourcetype = python:sidekick
SHOULD_LINEMERGE = false
```

## Conclusion

The logging framework provides:
- ✅ Thread-safe logging operations
- ✅ Async-safe with minimal blocking
- ✅ Efficient filtering and formatting
- ✅ Automatic file rotation
- ✅ Production-ready structured output
- ✅ Integration with log aggregation
- ✅ Comprehensive test coverage
- ✅ Zero external dependencies

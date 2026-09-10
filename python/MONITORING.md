# Agent Performance Monitoring

## Overview

Agent Performance Monitoring is a built-in framework feature that automatically tracks key performance metrics for each agent in your orchestrator, including:

- **Success/failure rates** — detect unreliable agents
- **Latency statistics** — identify slow agents (avg, min, max, median, p99)
- **Automatic agent disabling** — temporarily disable agents with >50% failure rate
- **Health status** — view which agents are disabled and why
- **Metrics export** — serialize metrics for observability tools

## Enabling & Disabling

Performance monitoring is **enabled by default**. To disable it:

```python
from agent_squad.orchestrator import AgentSquad

orchestrator = AgentSquad(enable_performance_monitoring=False)
```

## Basic Usage

### Initialize an Orchestrator with Agents

```python
from agent_squad.orchestrator import AgentSquad
from agent_squad.agents import BedrockLLMAgent, BedrockLLMAgentOptions

orchestrator = AgentSquad()  # monitoring enabled by default

tech_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
    name="Tech Agent",
    description="Answers technical questions"
))
orchestrator.add_agent(tech_agent)

health_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
    name="Health Agent",
    description="Answers health questions"
))
orchestrator.add_agent(health_agent)
```

When you add agents, metrics are automatically initialized.

### Get Agent Metrics

```python
# Get metrics for a specific agent
tech_metrics = orchestrator.get_agent_metrics(tech_agent.id)
print(f"Tech Agent: {tech_metrics['success_rate']:.1f}% success")
print(f"  Avg latency: {tech_metrics['avg_latency_ms']:.0f}ms")
print(f"  Total calls: {tech_metrics['total_calls']}")

# Get all agents' metrics
all_metrics = orchestrator.get_agent_metrics()
for agent_id, metrics in all_metrics.items():
    print(f"{metrics['agent_name']}: {metrics['success_rate']:.1f}% success")
```

### Check Agent Status

```python
# Get disabled agents
disabled = orchestrator.get_disabled_agents()
if disabled:
    for agent_id, reason in disabled.items():
        print(f"⚠️  {agent_id} is disabled: {reason}")
```

### Re-enable a Disabled Agent

```python
# After fixing the underlying issue, re-enable the agent
orchestrator.enable_agent(tech_agent.id)
```

### Reset Metrics

```python
# Reset metrics for one agent
orchestrator.reset_agent_metrics(tech_agent.id)

# Reset all metrics
orchestrator.reset_agent_metrics()
```

## How Auto-Disable Works

Agents are **automatically disabled** when:

1. **Failure rate exceeds threshold** — defaults to 50%
2. **Minimum calls reached** — requires at least 5 calls before evaluation

**Why disable an agent?** 
- Protects users from poor user experiences
- Prevents cascading failures (e.g., if an LLM provider is down)
- Allows graceful degradation to fallback agents

When an agent is disabled, `route_request()` returns an error message instead of attempting to call the agent:

```
"The agent 'Tech Agent' is currently unavailable due to performance issues. 
Please try again later."
```

## Metrics Reference

### Per-Agent Metrics

Each agent's metrics include:

| Metric | Type | Description |
|--------|------|-------------|
| `agent_id` | str | Unique agent identifier |
| `agent_name` | str | Human-readable agent name |
| `total_calls` | int | Total number of calls (success + failure) |
| `successful_calls` | int | Number of successful executions |
| `failed_calls` | int | Number of failed executions |
| `success_rate` | float | Success rate as percentage (0-100) |
| `failure_rate` | float | Failure rate as percentage (0-100) |
| `avg_latency_ms` | float | Average latency in milliseconds |
| `min_latency_ms` | float | Minimum latency in milliseconds |
| `max_latency_ms` | float | Maximum latency in milliseconds |
| `median_latency_ms` | float | Median latency in milliseconds |
| `p99_latency_ms` | float | 99th percentile latency in milliseconds |
| `last_error` | str | Most recent error message |
| `last_call_time` | ISO 8601 | Timestamp of most recent call |
| `disabled` | bool | Whether agent is currently disabled |
| `disable_reason` | str | Reason for disabling (if disabled) |

### Example Metrics Output

```python
metrics = orchestrator.get_agent_metrics(agent_id)
print(metrics)
# Output:
# {
#   'agent_id': 'bedrock-tech-agent',
#   'agent_name': 'Tech Agent',
#   'total_calls': 125,
#   'successful_calls': 120,
#   'failed_calls': 5,
#   'success_rate': 96.0,
#   'failure_rate': 4.0,
#   'avg_latency_ms': 245.67,
#   'min_latency_ms': 120.45,
#   'max_latency_ms': 890.23,
#   'median_latency_ms': 230.12,
#   'p99_latency_ms': 850.0,
#   'last_error': 'Timeout after 30s',
#   'last_call_time': '2026-09-10T16:30:45.123456',
#   'disabled': False,
#   'disable_reason': None
# }
```

## Configuration

### Adjusting Failure Rate Threshold

To customize the failure rate threshold for auto-disable:

```python
from agent_squad.orchestrator import AgentSquad

orchestrator = AgentSquad()

# Access the metrics collector
orchestrator.metrics_collector.failure_rate_threshold = 30.0  # 30% instead of 50%
```

### Disabling Auto-Disable Logic

To prevent automatic agent disabling (but still collect metrics):

```python
orchestrator = AgentSquad()
orchestrator.metrics_collector.enable_auto_disable = False
```

## Integration with Observability

### Export to JSON for Logging

```python
import json

metrics = orchestrator.get_agent_metrics()
print(json.dumps(metrics, indent=2))
```

### Send to External Observability Tool

```python
import json
import httpx

async def send_metrics_to_datadog():
    metrics = orchestrator.get_agent_metrics()
    
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.datadoghq.com/api/v1/series",
            json={"series": metrics},
            headers={"DD-API-KEY": "YOUR_API_KEY"}
        )
```

### Query Metrics Periodically

```python
import asyncio

async def monitor_agents():
    while True:
        metrics = orchestrator.get_agent_metrics()
        
        for agent_id, agent_metrics in metrics.items():
            if agent_metrics['failure_rate'] > 25:
                print(f"⚠️  {agent_metrics['agent_name']} failure rate: "
                      f"{agent_metrics['failure_rate']:.1f}%")
        
        await asyncio.sleep(60)  # Check every minute

# In your async main loop:
# await monitor_agents()
```

## Real-World Examples

### Example 1: Graceful Fallback

```python
from agent_squad.orchestrator import AgentSquad
from agent_squad.classifiers import LLMClassifier

orchestrator = AgentSquad()

# Add primary agent
primary_agent = BedrockLLMAgent(...)
orchestrator.add_agent(primary_agent)

# Add fallback agent
fallback_agent = AnthropicAgent(...)
orchestrator.add_agent(fallback_agent)

# If primary fails too often, it gets auto-disabled and classifier
# will route to fallback_agent
response = await orchestrator.route_request(
    user_input="What's the weather?",
    user_id="user123",
    session_id="session456"
)
```

### Example 2: Alert on Degradation

```python
async def check_agent_health():
    metrics = orchestrator.get_agent_metrics()
    
    for agent_id, m in metrics.items():
        if m['total_calls'] > 10:  # Enough data to evaluate
            if m['success_rate'] < 80:
                # Send alert
                await send_alert(
                    f"Agent {m['agent_name']} success rate dropped to "
                    f"{m['success_rate']:.1f}%"
                )
            
            if m['avg_latency_ms'] > 1000:
                await send_alert(
                    f"Agent {m['agent_name']} latency increased to "
                    f"{m['avg_latency_ms']:.0f}ms"
                )
```

### Example 3: Debug Slow Agents

```python
# Find which agents are slow
all_metrics = orchestrator.get_agent_metrics()
slow_agents = [
    (m['agent_name'], m['p99_latency_ms'])
    for m in all_metrics.values()
    if m['p99_latency_ms'] > 2000
]

for agent_name, p99_latency in sorted(slow_agents, key=lambda x: x[1], reverse=True):
    print(f"🐢 {agent_name}: p99 latency is {p99_latency:.0f}ms")
```

## Implementation Details

### Metrics Collection Points

Metrics are collected at these points in the orchestration flow:

1. **Agent dispatch** — time from dispatch start to agent response
2. **Failure capture** — when an agent raises an exception
3. **Automatic disabling** — after each call, failure rate is checked

### Thread Safety

The `AgentMetricsCollector` is **not thread-safe** for concurrent writes. For production systems with concurrent requests, consider:

1. **Using a lock** (synchronization):
   ```python
   import threading
   orchestrator.metrics_lock = threading.Lock()
   ```

2. **Using a separate metrics service** — collect metrics in your observability platform instead

3. **Using async-safe collections** — for async-only applications (recommended)

### Performance Overhead

- **Memory:** ~1KB per agent for metrics storage
- **CPU:** <1ms per request (for recording metrics)
- **Disable:** Minimal — single dict lookup

## Troubleshooting

### Agents Keep Getting Disabled

**Symptom:** Agents are automatically disabled and don't recover.

**Solution:**
1. Check the disable reason: `orchestrator.get_disabled_agents()`
2. Fix the underlying issue (e.g., API credentials, network)
3. Reset metrics: `orchestrator.reset_agent_metrics(agent_id)`
4. Re-enable: `orchestrator.enable_agent(agent_id)`

### Metrics Are Always Zero

**Symptom:** All metrics show 0 calls even after making requests.

**Solution:** Check if monitoring is enabled:
```python
if orchestrator.metrics_collector is None:
    print("Performance monitoring is disabled!")
```

### High P99 Latency

**Symptom:** Average latency is fine but p99 latency is high.

**Solution:** This indicates occasional slow responses. Check for:
- External API rate limiting
- Network timeouts
- LLM provider issues
- Large input/output processing

Use `orchestrator.reset_agent_metrics(agent_id)` to clear outliers.

## API Reference

### `AgentSquad` Methods

```python
def get_agent_metrics(self, agent_id: str | None = None) -> Dict:
    """Get metrics for agent(s)."""

def get_disabled_agents(self) -> Dict[str, str]:
    """Get disabled agents and reasons."""

def enable_agent(self, agent_id: str) -> bool:
    """Re-enable a disabled agent."""

def reset_agent_metrics(self, agent_id: str | None = None) -> bool:
    """Reset metrics for agent(s)."""
```

### `AgentMetricsCollector` Methods

```python
def initialize_agent(self, agent_id: str, agent_name: str) -> None:
    """Initialize metrics for an agent."""

def record_success(self, agent_id: str, latency_ms: float) -> None:
    """Record successful execution."""

def record_failure(self, agent_id: str, error: str, latency_ms: float = 0.0) -> None:
    """Record failed execution."""

def is_agent_disabled(self, agent_id: str) -> bool:
    """Check if agent is disabled."""

def get_agent_metrics(self, agent_id: str) -> AgentMetrics:
    """Get metrics for specific agent."""

def get_all_metrics(self) -> Dict[str, Dict]:
    """Get metrics for all agents."""

def enable_agent(self, agent_id: str) -> bool:
    """Re-enable a disabled agent."""

def reset_agent_metrics(self, agent_id: str) -> bool:
    """Reset metrics for an agent."""

def reset_all_metrics(self) -> None:
    """Reset all metrics."""
```

## Future Enhancements

Planned improvements:

- [ ] Histogram bucketing for latency distribution
- [ ] Time-windowed metrics (last 1h, 24h, 7d)
- [ ] Cost tracking per agent (for paid LLM APIs)
- [ ] Built-in Prometheus exporter
- [ ] Metrics persistence to database
- [ ] Adaptive failure threshold based on historical data

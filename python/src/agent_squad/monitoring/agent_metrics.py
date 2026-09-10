"""Agent performance metrics collection and tracking."""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import statistics


@dataclass
class AgentMetrics:
    """Tracks performance metrics for a single agent."""
    
    agent_id: str
    agent_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    last_error: Optional[str] = None
    last_call_time: Optional[datetime] = None
    disabled: bool = False
    disable_reason: Optional[str] = None
    
    def record_success(self, latency_ms: float) -> None:
        """Record a successful agent execution."""
        self.total_calls += 1
        self.successful_calls += 1
        self.latencies_ms.append(latency_ms)
        self.last_call_time = datetime.now()
        self.last_error = None
    
    def record_failure(self, error: str, latency_ms: float = 0.0) -> None:
        """Record a failed agent execution."""
        self.total_calls += 1
        self.failed_calls += 1
        if latency_ms > 0:
            self.latencies_ms.append(latency_ms)
        self.last_error = error
        self.last_call_time = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.failed_calls / self.total_calls) * 100
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)
    
    @property
    def min_latency_ms(self) -> float:
        """Get minimum latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return min(self.latencies_ms)
    
    @property
    def max_latency_ms(self) -> float:
        """Get maximum latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return max(self.latencies_ms)
    
    @property
    def median_latency_ms(self) -> float:
        """Get median latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return statistics.median(self.latencies_ms)
    
    @property
    def p99_latency_ms(self) -> float:
        """Get 99th percentile latency in milliseconds."""
        if not self.latencies_ms or len(self.latencies_ms) < 100:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index]
    
    def disable(self, reason: str) -> None:
        """Disable this agent with a reason."""
        self.disabled = True
        self.disable_reason = reason
    
    def enable(self) -> None:
        """Re-enable this agent."""
        self.disabled = False
        self.disable_reason = None
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.latencies_ms = []
        self.last_error = None
        self.disabled = False
        self.disable_reason = None
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 2),
            "failure_rate": round(self.failure_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "median_latency_ms": round(self.median_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "last_error": self.last_error,
            "last_call_time": self.last_call_time.isoformat() if self.last_call_time else None,
            "disabled": self.disabled,
            "disable_reason": self.disable_reason,
        }


@dataclass
class AgentMetricsCollector:
    """Collects and manages metrics for all agents."""
    
    metrics: Dict[str, AgentMetrics] = field(default_factory=dict)
    failure_rate_threshold: float = 50.0  # Disable agents with >50% failure rate
    enable_auto_disable: bool = True
    
    def initialize_agent(self, agent_id: str, agent_name: str) -> None:
        """Initialize metrics tracking for an agent."""
        if agent_id not in self.metrics:
            self.metrics[agent_id] = AgentMetrics(
                agent_id=agent_id,
                agent_name=agent_name
            )
    
    def record_success(self, agent_id: str, latency_ms: float) -> None:
        """Record successful agent execution."""
        if agent_id in self.metrics:
            self.metrics[agent_id].record_success(latency_ms)
            self._check_and_update_agent_status(agent_id)
    
    def record_failure(self, agent_id: str, error: str, latency_ms: float = 0.0) -> None:
        """Record failed agent execution."""
        if agent_id in self.metrics:
            self.metrics[agent_id].record_failure(error, latency_ms)
            self._check_and_update_agent_status(agent_id)
    
    def _check_and_update_agent_status(self, agent_id: str) -> None:
        """Check if agent should be disabled based on metrics."""
        if not self.enable_auto_disable:
            return
        
        agent_metrics = self.metrics.get(agent_id)
        if not agent_metrics or agent_metrics.total_calls < 5:  # Require min 5 calls
            return
        
        if agent_metrics.failure_rate > self.failure_rate_threshold:
            if not agent_metrics.disabled:
                agent_metrics.disable(
                    f"Failure rate ({agent_metrics.failure_rate:.1f}%) "
                    f"exceeded threshold ({self.failure_rate_threshold}%)"
                )
    
    def is_agent_disabled(self, agent_id: str) -> bool:
        """Check if an agent is currently disabled."""
        return self.metrics.get(agent_id, AgentMetrics("", "")).disabled
    
    def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        return self.metrics.get(agent_id)
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """Get all metrics as dictionaries."""
        return {
            agent_id: metrics.to_dict()
            for agent_id, metrics in self.metrics.items()
        }
    
    def get_disabled_agents(self) -> Dict[str, str]:
        """Get all disabled agents and their disable reasons."""
        return {
            agent_id: metrics.disable_reason or "Unknown"
            for agent_id, metrics in self.metrics.items()
            if metrics.disabled
        }
    
    def enable_agent(self, agent_id: str) -> bool:
        """Re-enable a previously disabled agent."""
        if agent_id in self.metrics:
            self.metrics[agent_id].enable()
            return True
        return False
    
    def reset_agent_metrics(self, agent_id: str) -> bool:
        """Reset metrics for a specific agent."""
        if agent_id in self.metrics:
            self.metrics[agent_id].reset()
            return True
        return False
    
    def reset_all_metrics(self) -> None:
        """Reset all collected metrics."""
        for metrics in self.metrics.values():
            metrics.reset()

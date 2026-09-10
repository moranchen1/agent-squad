"""Unit tests for agent performance monitoring."""

import pytest
import asyncio
from agent_squad.monitoring import AgentMetrics, AgentMetricsCollector


class TestAgentMetrics:
    """Test AgentMetrics class."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = AgentMetrics(agent_id="test_agent", agent_name="Test Agent")
        
        assert metrics.agent_id == "test_agent"
        assert metrics.agent_name == "Test Agent"
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0
    
    def test_record_success(self):
        """Test recording successful execution."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        metrics.record_success(100.5)
        
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1
        assert metrics.failed_calls == 0
        assert metrics.success_rate == 100.0
        assert metrics.failure_rate == 0.0
        assert metrics.avg_latency_ms == 100.5
        assert metrics.last_error is None
    
    def test_record_failure(self):
        """Test recording failed execution."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        metrics.record_failure("Connection error", 50.0)
        
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 1
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 100.0
        assert metrics.last_error == "Connection error"
    
    def test_mixed_success_and_failure(self):
        """Test mixed success and failure rates."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        # 3 successes
        metrics.record_success(100.0)
        metrics.record_success(150.0)
        metrics.record_success(200.0)
        
        # 2 failures
        metrics.record_failure("Error 1")
        metrics.record_failure("Error 2", 50.0)
        
        assert metrics.total_calls == 5
        assert metrics.successful_calls == 3
        assert metrics.failed_calls == 2
        assert metrics.success_rate == 60.0
        assert metrics.failure_rate == 40.0
    
    def test_latency_statistics(self):
        """Test latency calculations."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        latencies = [100.0, 150.0, 200.0, 250.0, 300.0]
        for latency in latencies:
            metrics.record_success(latency)
        
        assert metrics.avg_latency_ms == 200.0
        assert metrics.min_latency_ms == 100.0
        assert metrics.max_latency_ms == 300.0
        assert metrics.median_latency_ms == 200.0
    
    def test_disable_enable(self):
        """Test agent disable/enable functionality."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        assert not metrics.disabled
        
        metrics.disable("High failure rate")
        assert metrics.disabled
        assert metrics.disable_reason == "High failure rate"
        
        metrics.enable()
        assert not metrics.disabled
        assert metrics.disable_reason is None
    
    def test_reset(self):
        """Test metrics reset."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test")
        
        metrics.record_success(100.0)
        metrics.record_failure("Error")
        metrics.disable("Test reason")
        
        assert metrics.total_calls == 2
        
        metrics.reset()
        
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0
        assert not metrics.disabled
        assert metrics.disable_reason is None
        assert metrics.latencies_ms == []
    
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = AgentMetrics(agent_id="test", agent_name="Test Agent")
        metrics.record_success(100.0)
        metrics.record_success(200.0)
        
        data = metrics.to_dict()
        
        assert data["agent_id"] == "test"
        assert data["agent_name"] == "Test Agent"
        assert data["total_calls"] == 2
        assert data["successful_calls"] == 2
        assert data["success_rate"] == 100.0
        assert data["avg_latency_ms"] == 150.0


class TestAgentMetricsCollector:
    """Test AgentMetricsCollector class."""
    
    def test_initialization(self):
        """Test collector initialization."""
        collector = AgentMetricsCollector()
        
        assert collector.failure_rate_threshold == 50.0
        assert collector.enable_auto_disable is True
        assert len(collector.metrics) == 0
    
    def test_initialize_agent(self):
        """Test agent initialization."""
        collector = AgentMetricsCollector()
        
        collector.initialize_agent("agent_1", "Agent One")
        
        assert "agent_1" in collector.metrics
        assert collector.metrics["agent_1"].agent_name == "Agent One"
    
    def test_record_success(self):
        """Test recording success in collector."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        
        collector.record_success("agent_1", 100.0)
        
        metrics = collector.get_agent_metrics("agent_1")
        assert metrics.successful_calls == 1
    
    def test_record_failure(self):
        """Test recording failure in collector."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        
        collector.record_failure("agent_1", "Test error", 50.0)
        
        metrics = collector.get_agent_metrics("agent_1")
        assert metrics.failed_calls == 1
        assert metrics.last_error == "Test error"
    
    def test_auto_disable_on_high_failure_rate(self):
        """Test automatic agent disabling on high failure rate."""
        collector = AgentMetricsCollector(failure_rate_threshold=50.0, enable_auto_disable=True)
        collector.initialize_agent("agent_1", "Agent One")
        
        # Record 3 failures and 2 successes (60% failure rate)
        for _ in range(2):
            collector.record_success("agent_1", 100.0)
        for _ in range(3):
            collector.record_failure("agent_1", "Error")
        
        # Agent should be disabled now
        assert collector.is_agent_disabled("agent_1")
        
        disabled_agents = collector.get_disabled_agents()
        assert "agent_1" in disabled_agents
    
    def test_no_auto_disable_with_flag_disabled(self):
        """Test that auto-disable is skipped when flag is False."""
        collector = AgentMetricsCollector(failure_rate_threshold=50.0, enable_auto_disable=False)
        collector.initialize_agent("agent_1", "Agent One")
        
        # Record 3 failures and 2 successes (60% failure rate)
        for _ in range(2):
            collector.record_success("agent_1", 100.0)
        for _ in range(3):
            collector.record_failure("agent_1", "Error")
        
        # Agent should NOT be disabled
        assert not collector.is_agent_disabled("agent_1")
    
    def test_minimum_calls_before_disable(self):
        """Test that agent is not disabled with less than min calls."""
        collector = AgentMetricsCollector(failure_rate_threshold=50.0, enable_auto_disable=True)
        collector.initialize_agent("agent_1", "Agent One")
        
        # Record only 2 calls (below minimum of 5)
        collector.record_failure("agent_1", "Error")
        collector.record_failure("agent_1", "Error")
        
        # Agent should NOT be disabled (min calls not met)
        assert not collector.is_agent_disabled("agent_1")
    
    def test_enable_agent(self):
        """Test re-enabling a disabled agent."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        
        metrics = collector.get_agent_metrics("agent_1")
        metrics.disable("Test disable")
        
        assert collector.is_agent_disabled("agent_1")
        
        collector.enable_agent("agent_1")
        
        assert not collector.is_agent_disabled("agent_1")
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        collector.initialize_agent("agent_2", "Agent Two")
        
        collector.record_success("agent_1", 100.0)
        collector.record_success("agent_2", 200.0)
        
        all_metrics = collector.get_all_metrics()
        
        assert len(all_metrics) == 2
        assert "agent_1" in all_metrics
        assert "agent_2" in all_metrics
        assert all_metrics["agent_1"]["total_calls"] == 1
        assert all_metrics["agent_2"]["total_calls"] == 1
    
    def test_reset_agent_metrics(self):
        """Test resetting individual agent metrics."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        
        collector.record_success("agent_1", 100.0)
        assert collector.get_agent_metrics("agent_1").total_calls == 1
        
        collector.reset_agent_metrics("agent_1")
        assert collector.get_agent_metrics("agent_1").total_calls == 0
    
    def test_reset_all_metrics(self):
        """Test resetting all metrics."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        collector.initialize_agent("agent_2", "Agent Two")
        
        collector.record_success("agent_1", 100.0)
        collector.record_success("agent_2", 200.0)
        
        collector.reset_all_metrics()
        
        assert collector.get_agent_metrics("agent_1").total_calls == 0
        assert collector.get_agent_metrics("agent_2").total_calls == 0
    
    def test_get_disabled_agents(self):
        """Test getting list of disabled agents."""
        collector = AgentMetricsCollector()
        collector.initialize_agent("agent_1", "Agent One")
        collector.initialize_agent("agent_2", "Agent Two")
        
        metrics_1 = collector.get_agent_metrics("agent_1")
        metrics_1.disable("High latency")
        
        disabled = collector.get_disabled_agents()
        
        assert len(disabled) == 1
        assert "agent_1" in disabled
        assert disabled["agent_1"] == "High latency"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

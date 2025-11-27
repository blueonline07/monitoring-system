"""
Plugin module for monitoring agent
"""
from agent.plugins.base import BasePlugin
from agent.plugins.deduplication import DeduplicationPlugin
from agent.plugins.threshold_alert import ThresholdAlertPlugin
from agent.plugins.filter import FilterPlugin
from agent.plugins.aggregation import AggregationPlugin

__all__ = [
    'BasePlugin',
    'DeduplicationPlugin',
    'ThresholdAlertPlugin',
    'FilterPlugin',
    'AggregationPlugin',
]


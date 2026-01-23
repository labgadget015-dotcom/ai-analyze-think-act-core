"""
AI Analyze->Think->Act Core Framework
Universal pipeline for AI-powered analysis, insights, and recommendations.
"""

__version__ = "0.1.0"
__author__ = "Gadget Lab"

from .ingest import ingest
from .analysis import analyze
from .recommendations import recommend

__all__ = ["ingest", "analyze", "recommend"]

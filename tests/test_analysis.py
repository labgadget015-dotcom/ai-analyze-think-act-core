"""
Unit tests for the analysis module.
"""

import pytest
import pandas as pd
from core.analysis import AnalysisRequest, AnalysisResult, AnalysisPipeline, analyze


class TestAnalysisRequest:
    """Test AnalysisRequest dataclass."""
    
    def test_request_creation(self):
        """Test creating an AnalysisRequest."""
        df = pd.DataFrame({'views': [100, 200, 300]})
        request = AnalysisRequest(
            dataset=df,
            goal='grow_subscribers',
            constraints={'budget': 500, 'timeframe_days': 30}
        )
        assert request.goal == 'grow_subscribers'
        assert request.constraints['budget'] == 500
        assert request.llm_model == 'gpt-4o'


class TestAnalysisPipeline:
    """Test AnalysisPipeline class."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initializes with correct stages."""
        pipeline = AnalysisPipeline()
        assert 'trend' in pipeline.analysis_stages
        assert 'anomaly' in pipeline.analysis_stages
        assert 'ranking' in pipeline.analysis_stages
        assert 'prediction' in pipeline.analysis_stages
    
    def test_goal_chains_defined(self):
        """Test that all goals have defined chains."""
        pipeline = AnalysisPipeline()
        assert 'grow_subscribers' in pipeline.goal_chains
        assert 'increase_ctr' in pipeline.goal_chains
        assert 'boost_watch_time' in pipeline.goal_chains
    
    def test_grow_subscribers_analysis(self):
        """Test analysis for grow_subscribers goal."""
        df = pd.DataFrame({
            'views': [100, 200, 300],
            'subscribers': [10, 20, 30],
            'engagement': [5, 10, 15]
        })
        request = AnalysisRequest(
            dataset=df,
            goal='grow_subscribers',
            constraints={'budget': 500, 'timeframe_days': 30}
        )
        pipeline = AnalysisPipeline()
        result = pipeline.run(request)
        
        assert isinstance(result, AnalysisResult)
        assert result.goal == 'grow_subscribers'
        assert isinstance(result.trends, list)
        assert isinstance(result.rankings, list)
        assert result.diagnosis != ""
    
    def test_increase_ctr_analysis(self):
        """Test analysis for increase_ctr goal."""
        df = pd.DataFrame({'ctr': [5.5, 6.2, 7.1]})
        request = AnalysisRequest(
            dataset=df,
            goal='increase_ctr',
            constraints={'budget': 200, 'timeframe_days': 7}
        )
        pipeline = AnalysisPipeline()
        result = pipeline.run(request)
        
        assert result.goal == 'increase_ctr'
        assert isinstance(result.anomalies, list)
        assert isinstance(result.metrics_to_watch, list)
    
    def test_boost_watch_time_analysis(self):
        """Test analysis for boost_watch_time goal."""
        df = pd.DataFrame({'watch_time': [3.2, 4.5, 5.1]})
        request = AnalysisRequest(
            dataset=df,
            goal='boost_watch_time',
            constraints={'budget': 500, 'timeframe_days': 14}
        )
        pipeline = AnalysisPipeline()
        result = pipeline.run(request)
        
        assert result.goal == 'boost_watch_time'
        assert result.predictions is not None
    
    def test_invalid_goal(self):
        """Test that invalid goal raises error."""
        df = pd.DataFrame({'data': [1, 2, 3]})
        request = AnalysisRequest(
            dataset=df,
            goal='invalid_goal',
            constraints={'budget': 100, 'timeframe_days': 7}
        )
        pipeline = AnalysisPipeline()
        with pytest.raises(ValueError, match="Unknown goal"):
            pipeline.run(request)
    
    def test_metrics_to_watch(self):
        """Test that metrics_to_watch are returned for all goals."""
        pipeline = AnalysisPipeline()
        
        metrics = pipeline._identify_metrics('grow_subscribers')
        assert len(metrics) > 0
        assert 'metric' in metrics[0]
        assert 'target' in metrics[0]
        assert 'period' in metrics[0]


class TestPublicAPI:
    """Test the public analyze API."""
    
    def test_analyze_function(self):
        """Test the public analyze() function."""
        df = pd.DataFrame({'views': [100, 200, 300]})
        request = AnalysisRequest(
            dataset=df,
            goal='grow_subscribers',
            constraints={'budget': 500, 'timeframe_days': 30}
        )
        result = analyze(request)
        
        assert isinstance(result, AnalysisResult)
        assert result.goal == 'grow_subscribers'

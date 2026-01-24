"""
Integration tests for the complete pipeline.
"""

import pytest
import pandas as pd
from datetime import datetime
from core.ingest import IngestConfig, ingest
from core.analysis import AnalysisRequest, analyze
from core.recommendations import RecommendationRequest, recommend


class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_full_pipeline_grow_subscribers(self):
        """Test complete pipeline for grow_subscribers goal."""
        # Step 1: Ingest data
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        dataset = ingest(config)
        
        # Step 2: Analyze data
        analysis_request = AnalysisRequest(
            dataset=dataset,
            goal='grow_subscribers',
            constraints={'budget': 500, 'timeframe_days': 30}
        )
        analysis_result = analyze(analysis_request)
        
        # Step 3: Generate recommendations
        rec_request = RecommendationRequest(
            insights={'analysis': analysis_result},
            goal='grow_subscribers',
            budget=500
        )
        recommendations = recommend(rec_request)
        
        # Verify results
        assert isinstance(dataset, pd.DataFrame)
        assert analysis_result.goal == 'grow_subscribers'
        assert len(recommendations) > 0
    
    def test_full_pipeline_increase_ctr(self):
        """Test complete pipeline for increase_ctr goal."""
        # Step 1: Ingest data
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        dataset = ingest(config)
        
        # Step 2: Analyze data
        analysis_request = AnalysisRequest(
            dataset=dataset,
            goal='increase_ctr',
            constraints={'budget': 200, 'timeframe_days': 7}
        )
        analysis_result = analyze(analysis_request)
        
        # Step 3: Generate recommendations
        rec_request = RecommendationRequest(
            insights={'analysis': analysis_result},
            goal='increase_ctr',
            budget=200
        )
        recommendations = recommend(rec_request)
        
        # Verify results
        assert analysis_result.goal == 'increase_ctr'
        assert len(recommendations) > 0
    
    def test_full_pipeline_boost_watch_time(self):
        """Test complete pipeline for boost_watch_time goal."""
        # Step 1: Ingest data
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        dataset = ingest(config)
        
        # Step 2: Analyze data
        analysis_request = AnalysisRequest(
            dataset=dataset,
            goal='boost_watch_time',
            constraints={'budget': 500, 'timeframe_days': 14}
        )
        analysis_result = analyze(analysis_request)
        
        # Step 3: Generate recommendations
        rec_request = RecommendationRequest(
            insights={'analysis': analysis_result},
            goal='boost_watch_time',
            budget=500
        )
        recommendations = recommend(rec_request)
        
        # Verify results
        assert analysis_result.goal == 'boost_watch_time'
        assert len(recommendations) > 0
    
    def test_pipeline_with_custom_data(self):
        """Test pipeline with custom YouTube-like data."""
        # Create custom dataset
        dataset = pd.DataFrame({
            'video_id': ['v1', 'v2', 'v3'],
            'views': [1000, 2000, 3000],
            'subscribers_gained': [10, 25, 40],
            'ctr': [5.2, 6.8, 7.5],
            'watch_time': [3.5, 4.2, 5.1]
        })
        
        # Analyze
        analysis_request = AnalysisRequest(
            dataset=dataset,
            goal='grow_subscribers',
            constraints={'budget': 500, 'timeframe_days': 30}
        )
        analysis_result = analyze(analysis_request)
        
        # Recommend
        rec_request = RecommendationRequest(
            insights={'analysis': analysis_result},
            goal='grow_subscribers',
            budget=500
        )
        recommendations = recommend(rec_request)
        
        # Verify
        assert len(analysis_result.trends) > 0
        assert len(recommendations) > 0
        assert all(action.priority in ['critical', 'high', 'medium', 'low'] for action in recommendations)

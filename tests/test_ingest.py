"""
Unit tests for the ingest module.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from core.ingest import IngestConfig, IngestPipeline, ingest


class TestIngestConfig:
    """Test IngestConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating an IngestConfig."""
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()},
            max_records=100
        )
        assert config.source_type == 'youtube'
        assert config.auth_token == 'test_token'
        assert config.max_records == 100


class TestIngestPipeline:
    """Test IngestPipeline class."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initializes with connectors."""
        pipeline = IngestPipeline()
        assert 'youtube' in pipeline.connectors
        assert 'crm' in pipeline.connectors
        assert 'email' in pipeline.connectors
    
    def test_youtube_ingest(self):
        """Test YouTube data ingestion."""
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        pipeline = IngestPipeline()
        result = pipeline.run(config)
        assert isinstance(result, pd.DataFrame)
    
    def test_invalid_source_type(self):
        """Test that invalid source type raises error."""
        config = IngestConfig(
            source_type='invalid',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        pipeline = IngestPipeline()
        with pytest.raises(ValueError, match="Unknown source type"):
            pipeline.run(config)
    
    def test_clean_and_normalize_empty_dataframe(self):
        """Test cleaning an empty DataFrame."""
        pipeline = IngestPipeline()
        df = pd.DataFrame()
        result = pipeline._clean_and_normalize(df, 'youtube')
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_clean_and_normalize_with_duplicates(self):
        """Test that duplicates are removed."""
        pipeline = IngestPipeline()
        df = pd.DataFrame({
            'id': [1, 1, 2],
            'value': ['a', 'a', 'b']
        })
        result = pipeline._clean_and_normalize(df, 'youtube')
        assert len(result) <= 2  # Duplicates should be removed


class TestPublicAPI:
    """Test the public ingest API."""
    
    def test_ingest_function(self):
        """Test the public ingest() function."""
        config = IngestConfig(
            source_type='youtube',
            auth_token='test_token',
            timeframe={'start': datetime.now(), 'end': datetime.now()}
        )
        result = ingest(config)
        assert isinstance(result, pd.DataFrame)

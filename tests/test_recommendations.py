"""
Unit tests for the recommendations module.
"""

import pytest
from core.recommendations import (
    Priority, Effort, Action, RecommendationRequest,
    RecommendationGenerator, recommend
)


class TestEnums:
    """Test Priority and Effort enums."""
    
    def test_priority_levels(self):
        """Test Priority enum has all expected levels."""
        assert Priority.CRITICAL == "critical"
        assert Priority.HIGH == "high"
        assert Priority.MEDIUM == "medium"
        assert Priority.LOW == "low"
    
    def test_effort_levels(self):
        """Test Effort enum has all expected levels."""
        assert Effort.LOW == "low"
        assert Effort.MEDIUM == "medium"
        assert Effort.HIGH == "high"


class TestAction:
    """Test Action dataclass."""
    
    def test_action_creation(self):
        """Test creating an Action."""
        action = Action(
            id="test_001",
            description="Test action",
            priority=Priority.HIGH,
            effort=Effort.MEDIUM,
            expected_impact_metric="Test metric",
            rationale="Test rationale",
            budget_required=100
        )
        assert action.id == "test_001"
        assert action.priority == Priority.HIGH
        assert action.effort == Effort.MEDIUM
        assert action.budget_required == 100


class TestRecommendationGenerator:
    """Test RecommendationGenerator class."""
    
    def test_generator_initialization(self):
        """Test generator initializes with goal templates."""
        generator = RecommendationGenerator()
        assert 'grow_subscribers' in generator.goal_templates
        assert 'increase_ctr' in generator.goal_templates
        assert 'boost_watch_time' in generator.goal_templates
    
    def test_grow_subscribers_recommendations(self):
        """Test recommendations for grow_subscribers goal."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='grow_subscribers',
            budget=500
        )
        actions = generator.run(request)
        
        assert isinstance(actions, list)
        assert len(actions) <= 5
        assert all(isinstance(action, Action) for action in actions)
        assert all(action.budget_required <= 500 for action in actions if action.budget_required)
    
    def test_increase_ctr_recommendations(self):
        """Test recommendations for increase_ctr goal."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='increase_ctr',
            budget=200
        )
        actions = generator.run(request)
        
        assert len(actions) <= 5
        assert all(hasattr(action, 'id') for action in actions)
    
    def test_boost_watch_time_recommendations(self):
        """Test recommendations for boost_watch_time goal."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='boost_watch_time',
            budget=500
        )
        actions = generator.run(request)
        
        assert len(actions) <= 5
    
    def test_invalid_goal(self):
        """Test that invalid goal raises error."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='invalid_goal',
            budget=100
        )
        with pytest.raises(ValueError, match="Unknown goal"):
            generator.run(request)
    
    def test_budget_filtering(self):
        """Test that recommendations respect budget constraints."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='grow_subscribers',
            budget=0  # Zero budget
        )
        actions = generator.run(request)
        
        # All actions should have budget_required of 0 or None
        for action in actions:
            if action.budget_required is not None:
                assert action.budget_required <= 0
    
    def test_prioritization(self):
        """Test that actions are properly prioritized."""
        generator = RecommendationGenerator()
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='grow_subscribers',
            budget=1000
        )
        actions = generator.run(request)
        
        # Check that high priority actions come before medium/low
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        if len(actions) > 1:
            for i in range(len(actions) - 1):
                assert priority_order[actions[i].priority] <= priority_order[actions[i+1].priority]


class TestPublicAPI:
    """Test the public recommend API."""
    
    def test_recommend_function(self):
        """Test the public recommend() function."""
        request = RecommendationRequest(
            insights={'analysis': {}},
            goal='grow_subscribers',
            budget=500
        )
        actions = recommend(request)
        
        assert isinstance(actions, list)
        assert len(actions) <= 5
        assert all(isinstance(action, Action) for action in actions)

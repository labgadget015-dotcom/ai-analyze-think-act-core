# Prompts Directory

This directory contains YAML-based prompt templates for different analysis goals and domains.

## Structure

```
prompts/
├── __init__.py           # Prompt loading utilities
├── youtube_goals.yaml    # YouTube-specific analysis prompts
├── ecommerce_goals.yaml  # (Future) E-commerce analysis prompts
└── crm_goals.yaml        # (Future) CRM intelligence prompts
```

## YouTube Goals

The `youtube_goals.yaml` file defines prompt templates for three primary YouTube growth goals:

### 1. Grow Subscribers (`grow_subscribers`)
**Analysis Chain**: Trend → Ranking → Prediction

Analyzes upload frequency, content types, engagement metrics, and seasonal patterns to identify strategies for subscriber growth.

**Key Outputs**:
- Upload frequency vs subscriber growth correlation
- High-converting content types
- Predicted subscriber count for next 7/14/30 days
- Actionable recommendations

### 2. Increase CTR (`increase_ctr`)
**Analysis Chain**: Anomaly → Ranking

Optimizes thumbnails and titles by analyzing outliers and identifying patterns in high-performing content.

**Key Outputs**:
- Videos with exceptional CTR (positive/negative outliers)
- Common thumbnail design patterns
- Effective title formulas
- A/B testing recommendations

### 3. Boost Watch Time (`boost_watch_time`)
**Analysis Chain**: Trend → Prediction

Maximizes viewer retention by analyzing retention curves, video structure, and content pacing.

**Key Outputs**:
- Optimal video length by topic type
- Audience drop-off points
- Content pacing recommendations
- Playlist/series strategies

## Prompt Format

Each goal includes:

```yaml
goal_name:
  description: "Brief goal description"
  chain:
    - stage1
    - stage2
    - stage3
  
  stage1_prompt: |
    Multi-line prompt template with {placeholders}
    
  stage2_prompt: |
    Another prompt template
```

### Placeholders

Prompts use `{placeholder}` syntax for dynamic data injection:

- `{dataset}` - The input data (DataFrame as JSON)
- `{timeframe_days}` - Analysis period in days
- `{current_subscribers}` - Current subscriber count
- `{avg_ctr}` - Average click-through rate
- `{video_data}` - Individual video metrics
- `{historical_data}` - Historical performance data

## Adding New Goals

To add a new analysis goal:

1. Define the goal in the appropriate YAML file:
```yaml
your_goal_name:
  description: "What this goal achieves"
  chain:
    - trend  # or anomaly, ranking, prediction
    - ranking
  
  trend_prompt: |
    Your custom prompt template here...
    Data: {dataset}
    
  ranking_prompt: |
    Your ranking prompt...
```

2. Implement goal logic in `core/analysis.py`:
```python
self.goal_chains['your_goal_name'] = ['trend', 'ranking']
```

3. Add recommendation templates in `core/recommendations.py`:
```python
self.goal_templates['your_goal_name'] = self._recommend_your_goal
```

## LLM Configuration

Prompts are configured with:

```yaml
parameters:
  temperature: 0.3      # Lower = more deterministic
  max_tokens: 2000      # Response length limit
  model: "gpt-4o"       # LLM model to use
```

## Output Format

All prompts return structured JSON:

```json
{
  "trend_analysis": [
    {
      "trend_name": "Upload Frequency Impact",
      "data_points": [...],
      "confidence": "high",
      "interpretation": "..."
    }
  ],
  "ranking": [...],
  "prediction": [...]
}
```

## Best Practices

1. **Be Specific**: Include clear instructions and expected output format
2. **Use Examples**: Provide example outputs in prompts when possible
3. **Set Constraints**: Define acceptable value ranges and formats
4. **Handle Errors**: Include fallback behaviors for edge cases
5. **Test Thoroughly**: Validate prompts with diverse datasets

## Error Handling

The prompt system includes predefined error responses:

```yaml
error_responses:
  insufficient_data: "Not enough data points..."
  no_trends_found: "No significant trends detected..."
  high_variance: "Data shows high variance..."
```

## Future Enhancements

- [ ] Multi-language prompt support
- [ ] A/B testing framework for prompt optimization
- [ ] Prompt versioning and rollback
- [ ] Dynamic prompt composition
- [ ] Prompt effectiveness metrics

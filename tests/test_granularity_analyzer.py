import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from controllers.granularity_analyzer import GranularityAnalyzer

def test_detect_metric_columns():
    df = pd.DataFrame({
        "Product": ["A", "B"],
        "Price": [10, 20],
        "Quantity": [1, 2],
        "Date": ["2024-01-01", "2024-01-02"]
    })
    analyzer = GranularityAnalyzer(df)
    metrics = analyzer.detect_metric_columns()
    assert "Price" in metrics
    assert "Quantity" in metrics
    assert "Product" not in metrics

def test_detect_date_columns():
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Product": ["A", "B"]
    })
    analyzer = GranularityAnalyzer(df)
    dates = analyzer.detect_date_columns()
    assert "Date" in dates
    assert "Product" not in dates

def test_evaluate_granularities():
    df = pd.DataFrame({
        "Product": ["A", "A", "B", "B"],
        "Store": ["X", "Y", "X", "Y"],
        "Price": [10, 20, 30, 40]
    })
    analyzer = GranularityAnalyzer(df)
    result = analyzer.evaluate_granularities(["Product", "Store", "Price"])
    # The best granularity should be "Product" and "Store" with 4 unique combinations
    assert result[0][0] == ["Product", "Store"]
    assert result[0][1] == 4
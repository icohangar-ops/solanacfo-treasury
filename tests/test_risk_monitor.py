import pytest
class TestRisk:
    def test_levels(self):
        levels = ['low', 'medium', 'high', 'critical']
        assert len(levels) == 4
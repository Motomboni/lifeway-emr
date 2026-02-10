"""
Performance tests for query optimization.
Tests N+1 query problems and ensures proper select_related/prefetch_related usage.
"""
import pytest
from django.test.utils import override_settings
from django.db import connection, reset_queries
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.patients.models import Patient


@pytest.mark.django_db
class TestQueryOptimization:
    """Test query optimization in views."""
    
    def test_visit_list_queries(self, visit):
        """Test that visit list doesn't cause N+1 queries."""
        reset_queries()
        
        # Simulate what the viewset does
        visits = Visit.objects.all().select_related('patient', 'closed_by')
        
        list(visits)  # Force evaluation
        
        # Should use select_related to avoid N+1
        queries = connection.queries
        assert len(queries) < 10  # Reasonable query count
    
    def test_visit_with_consultation_queries(self, visit, consultation):
        """Test fetching visit with consultation doesn't cause extra queries."""
        reset_queries()
        
        visit = Visit.objects.select_related('patient').prefetch_related('consultation').get(id=visit.id)
        
        # Access related objects
        _ = visit.patient
        _ = visit.consultation
        
        queries = connection.queries
        # Should be optimized with select_related/prefetch_related
        assert len(queries) < 5

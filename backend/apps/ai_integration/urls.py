"""
URL configuration for AI Integration app.

Per EMR Rules:
- All endpoints are visit-scoped
- Nested under /api/v1/visits/{visit_id}/ai/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIRequestViewSet, AIClinicalViewSet, AIConfigurationViewSet

router = DefaultRouter()
router.register(r'ai-requests', AIRequestViewSet, basename='ai-request')

# Custom actions for AI clinical features (using as_view for proper visit_id passing)
ai_clinical_viewset = AIClinicalViewSet.as_view({
    'post': 'clinical_decision_support'
})

ai_nlp_viewset = AIClinicalViewSet.as_view({
    'post': 'nlp_summarize'
})

ai_coding_viewset = AIClinicalViewSet.as_view({
    'post': 'automated_coding'
})

ai_interaction_viewset = AIClinicalViewSet.as_view({
    'post': 'drug_interaction_check'
})

urlpatterns = [
    # AI clinical features - custom actions
    path('clinical-decision-support/', ai_clinical_viewset, name='ai-clinical-decision-support'),
    path('nlp-summarize/', ai_nlp_viewset, name='ai-nlp-summarize'),
    path('automated-coding/', ai_coding_viewset, name='ai-automated-coding'),
    path('drug-interaction-check/', ai_interaction_viewset, name='ai-drug-interaction-check'),
    # Router URLs for AI request history
    path('', include(router.urls)),
]

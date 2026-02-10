"""
API views for Explainable Lock System.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .lock_system import LockEvaluator, LockReasonCode

logger = logging.getLogger(__name__)


class LockEvaluationViewSet(viewsets.ViewSet):
    """
    ViewSet for evaluating action locks.
    
    Provides endpoints to check if actions are locked and why.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def evaluate(self, request):
        """
        Evaluate lock for an action.
        
        Request body:
        {
            "action_type": "consultation",
            "visit_id": 123,
            "consultation_id": 456,  // optional
            ...
        }
        """
        action_type = request.data.get('action_type')
        if not action_type:
            return Response(
                {'error': 'action_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_action_lock(
                action_type=action_type,
                **{k: v for k, v in request.data.items() if k != 'action_type'}
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def consultation(self, request):
        """Check if consultation is locked for a visit."""
        visit_id = request.query_params.get('visit_id')
        if not visit_id:
            return Response(
                {'error': 'visit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_consultation_lock(
                visit_id=int(visit_id),
                user_role=request.user.role if hasattr(request.user, 'role') else None
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating consultation lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def radiology_upload(self, request):
        """Check if radiology upload is locked."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        if not radiology_order_id:
            return Response(
                {'error': 'radiology_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_radiology_upload_lock(
                radiology_order_id=int(radiology_order_id)
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating radiology upload lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def drug_dispense(self, request):
        """Check if drug dispense is locked."""
        prescription_id = request.query_params.get('prescription_id')
        if not prescription_id:
            return Response(
                {'error': 'prescription_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_drug_dispense_lock(
                prescription_id=int(prescription_id)
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating drug dispense lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def lab_order(self, request):
        """Check if lab order is locked."""
        visit_id = request.query_params.get('visit_id')
        consultation_id = request.query_params.get('consultation_id')
        
        if not visit_id:
            return Response(
                {'error': 'visit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_lab_order_lock(
                visit_id=int(visit_id),
                consultation_id=int(consultation_id) if consultation_id else None
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating lab order lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def lab_result_post(self, request):
        """Check if lab result posting is locked."""
        lab_order_id = request.query_params.get('lab_order_id')
        if not lab_order_id:
            return Response(
                {'error': 'lab_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_lab_result_post_lock(
                lab_order_id=int(lab_order_id)
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating lab result post lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def radiology_report(self, request):
        """Check if radiology report posting is locked."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        if not radiology_order_id:
            return Response(
                {'error': 'radiology_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_radiology_report_lock(
                radiology_order_id=int(radiology_order_id)
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating radiology report lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def radiology_view(self, request):
        """Check if radiology viewing is locked."""
        radiology_order_id = request.query_params.get('radiology_order_id')
        if not radiology_order_id:
            return Response(
                {'error': 'radiology_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_radiology_view_lock(
                radiology_order_id=int(radiology_order_id)
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating radiology view lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def procedure(self, request):
        """Check if procedure is locked."""
        visit_id = request.query_params.get('visit_id')
        consultation_id = request.query_params.get('consultation_id')
        
        if not visit_id:
            return Response(
                {'error': 'visit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = LockEvaluator.evaluate_procedure_lock(
                visit_id=int(visit_id),
                consultation_id=int(consultation_id) if consultation_id else None
            )
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error evaluating procedure lock: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


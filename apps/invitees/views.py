from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

from apps.invitees.models import Invitee
from apps.invitees.serializers import InviteeSerializer, CSVUploadSerializer
from apps.invitees.services.csv_importer import InviteeCSVImporter

class InviteeImportView(APIView):
    """
    Ingests, validates, and optionally persists an invitee CSV list.
    Supports preview mode (?preview_only=true or multipart preview_only=true)
    and reports line-by-line validation errors.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['file']
        preview_only = serializer.validated_data.get('preview_only', False)

        # Allow query parameter override
        if 'preview_only' in request.query_params:
            preview_only = request.query_params.get('preview_only', '').lower() in ('true', '1', 't')

        importer = InviteeCSVImporter()
        try:
            result = importer.process_file(uploaded_file, preview_only=preview_only)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({
                'error': {
                    'code': 'CSV_VALIDATION_ERROR',
                    'message': str(err)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return Response({
                'error': {
                    'code': 'INTERNAL_IMPORT_ERROR',
                    'message': f"An error occurred while processing the CSV file: {str(err)}"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InviteeListView(ListAPIView):
    """
    Searchable, paginated directory of all imported invitees.
    Query param ?search=... searches across name, phone, email.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InviteeSerializer

    def get_queryset(self):
        queryset = Invitee.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(external_id__icontains=search)
            )
        return queryset

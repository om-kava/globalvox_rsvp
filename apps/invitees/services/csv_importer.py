import io
import csv
import re
from typing import Dict, Any, List, Tuple
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.invitees.models import Invitee

class InviteeCSVImporter:
    """
    Robust CSV ingestion engine with line-by-line validation,
    DDE/formula injection sanitization, preview mode, and bulk insertion.
    """
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
    REQUIRED_COLUMNS = {'name', 'phone', 'email'}

    def __init__(self):
        self.email_validator = EmailValidator()
        # Allows international format with optional + and 7 to 20 digits
        self.phone_regex = re.compile(r'^\+?[0-9]{7,20}$')

    def sanitize_cell(self, value: str) -> str:
        """
        Mitigates CSV Formula Injection (DDE) by escaping dangerous leading characters.
        """
        val = (value or '').strip()
        if val and val[0] in ('=', '+', '-', '@', '\t', '\r'):
            # Prepend single quote to neutralize formula evaluation in spreadsheets
            return "'" + val
        return val

    def normalize_phone(self, phone: str) -> str:
        """
        Strips whitespace, hyphens, parentheses, and periods from phone numbers.
        """
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
        return cleaned

    def validate_row(self, row: Dict[str, str], row_num: int, seen_phones: set) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Performs strict field validation for a single CSV row.
        """
        errors = []
        name = self.sanitize_cell(row.get('name', ''))
        raw_phone = row.get('phone', '')
        phone = self.normalize_phone(raw_phone)
        email = (row.get('email', '') or '').strip()
        external_id = (row.get('id', '') or '').strip()

        # Name validation
        if not name:
            errors.append('Name cannot be blank.')
        elif len(name) > 255:
            errors.append('Name exceeds 255 characters.')

        # Phone validation
        if not phone:
            errors.append('Phone number cannot be blank.')
        elif not self.phone_regex.match(phone):
            errors.append(f'Invalid phone number format: "{raw_phone}". Must be 7-20 digits (e.g. +919876543210).')
        elif phone in seen_phones:
            errors.append(f'Duplicate phone number in uploaded file: "{phone}".')

        # Email validation
        if not email:
            errors.append('Email address cannot be blank.')
        elif len(email) > 254:
            errors.append('Email exceeds 254 characters.')
        else:
            try:
                self.email_validator(email)
            except ValidationError:
                errors.append(f'Invalid email format: "{email}".')

        is_valid = len(errors) == 0
        cleaned_data = {
            'external_id': external_id or None,
            'name': name,
            'phone': phone,
            'email': email
        }
        return is_valid, errors, cleaned_data

    def process_file(self, file_obj, preview_only: bool = False) -> Dict[str, Any]:
        """
        Parses and validates CSV stream.
        If preview_only=True, returns validation report without database writes.
        If preview_only=False, persists valid invitees in bulk.
        """
        if file_obj.size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of 10MB (file size: {file_obj.size} bytes).")

        try:
            content = file_obj.read().decode('utf-8-sig', errors='replace')
        except Exception as e:
            raise ValueError(f"Failed to decode file content: {str(e)}")

        csv_file = io.StringIO(content)
        reader = csv.reader(csv_file)

        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("The uploaded CSV file is empty.")

        # Normalize header column names
        headers = [h.strip().lower() for h in raw_headers]
        missing_headers = self.REQUIRED_COLUMNS - set(headers)
        if missing_headers:
            raise ValueError(f"Missing required CSV column headers: {', '.join(sorted(missing_headers))}. Expected headers include: id, name, phone, email.")

        header_index = {h: idx for idx, h in enumerate(headers)}

        valid_records = []
        invalid_rows = []
        seen_phones = set()
        total_rows = 0

        for line_num, row_values in enumerate(reader, start=2):
            if not row_values or all(not v.strip() for v in row_values):
                # Skip empty lines
                continue

            total_rows += 1
            row_dict = {}
            for col_name, col_idx in header_index.items():
                row_dict[col_name] = row_values[col_idx].strip() if col_idx < len(row_values) else ''

            is_valid, errors, cleaned_data = self.validate_row(row_dict, line_num, seen_phones)

            if is_valid:
                seen_phones.add(cleaned_data['phone'])
                valid_records.append(cleaned_data)
            else:
                invalid_rows.append({
                    'row': line_num,
                    'raw_data': row_dict,
                    'reasons': errors
                })

        imported_count = 0
        if not preview_only and valid_records:
            with transaction.atomic():
                # Prepare Invitee model instances for bulk creation
                invitee_instances = [
                    Invitee(
                        external_id=rec['external_id'],
                        name=rec['name'],
                        phone=rec['phone'],
                        email=rec['email']
                    )
                    for rec in valid_records
                ]
                # bulk_create in batches of 1000
                created_objs = Invitee.objects.bulk_create(
                    invitee_instances,
                    batch_size=1000,
                    ignore_conflicts=False
                )
                imported_count = len(created_objs)

        return {
            'total_rows': total_rows,
            'valid_count': len(valid_records),
            'invalid_count': len(invalid_rows),
            'imported_count': imported_count if not preview_only else 0,
            'is_preview': preview_only,
            'sample_valid': valid_records[:5],
            'errors': invalid_rows
        }

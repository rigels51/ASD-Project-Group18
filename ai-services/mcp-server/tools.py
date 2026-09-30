import os
from typing import Any

import requests


DATABASE_SERVICE_URL = os.getenv(
	"DATABASE_SERVICE_URL", "http://student2-database:5002"
).rstrip("/")
PUBLIC_STAFF_FIELDS = ("staff_id", "given_name", "family_name", "department", "employment_type")


def _get_staff_records() -> list[dict[str, Any]]:
	response = requests.get(f"{DATABASE_SERVICE_URL}/staff", timeout=10)
	response.raise_for_status()
	records = response.json()
	if not isinstance(records, list):
		raise ValueError("Database service returned an invalid staff list")
	return records


def _public_staff_record(record: dict[str, Any]) -> dict[str, Any]:
	return {field: record[field] for field in PUBLIC_STAFF_FIELDS if field in record}


def staff_count() -> dict[str, int]:
	"""Return the number of staff records in the registry."""
	return {"staff_count": len(_get_staff_records())}


def staff_directory(department: str = "") -> list[dict[str, Any]]:
	"""List staff names and work classifications, optionally filtered by department."""
	records = _get_staff_records()
	if department.strip():
		department_key = department.strip().casefold()
		records = [
			record
			for record in records
			if str(record.get("department", "")).casefold() == department_key
		]
	return [_public_staff_record(record) for record in records[:100]]


def staff_member(staff_id: int) -> dict[str, Any]:
	"""Look up one staff record by its numeric ID, excluding email addresses."""
	if staff_id < 1:
		raise ValueError("staff_id must be a positive integer")
	for record in _get_staff_records():
		if record.get("staff_id") == staff_id:
			return _public_staff_record(record)
	return {"error": "Staff member not found", "staff_id": staff_id}


def employment_summary() -> dict[str, dict[str, int]]:
	"""Count staff by department and employment type."""
	by_department: dict[str, int] = {}
	by_employment_type: dict[str, int] = {}
	for record in _get_staff_records():
		department = str(record.get("department", "Unknown"))
		employment_type = str(record.get("employment_type", "Unknown"))
		by_department[department] = by_department.get(department, 0) + 1
		by_employment_type[employment_type] = by_employment_type.get(employment_type, 0) + 1
	return {
		"by_department": by_department,
		"by_employment_type": by_employment_type,
	}

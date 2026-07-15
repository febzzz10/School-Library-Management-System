"""Integration tests for services/student_service.py."""

import pytest

from app import config
from services import ServiceError, student_service


class TestStudentService:
    def test_add_valid_student(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "STU001",
            "name": "Rahul",
            "class_name": "10",
            "division": "A",
        })
        assert sid > 0
        student = student_service.get_student(sid)
        assert student["student_code"] == "STU001"
        assert student["name"] == "Rahul"
        assert student["status"] == config.STATUS_ACTIVE

    def test_add_duplicate_code_raises(self, fresh_db, sample_student):
        with pytest.raises(ServiceError, match="already exists"):
            student_service.add_student({
                "student_code": "STU001",
                "name": "Duplicate",
            })

    def test_add_student_without_code_raises(self, fresh_db):
        with pytest.raises(ServiceError, match="required"):
            student_service.add_student({
                "student_code": "",
                "name": "No Code",
            })

    def test_search_by_name(self, fresh_db):
        student_service.add_student({"student_code": "S1", "name": "Alpha"})
        student_service.add_student({"student_code": "S2", "name": "Beta"})
        students = student_service.get_students(search="Alpha")
        assert len(students) == 1

    def test_search_by_code(self, fresh_db):
        student_service.add_student({"student_code": "STU001", "name": "Rahul"})
        students = student_service.get_students(search="STU001")
        assert len(students) == 1

    def test_get_active_students(self, fresh_db, sample_student):
        active = student_service.get_active_students()
        codes = [s["student_code"] for s in active]
        assert "STU001" in codes

    def test_update_student(self, fresh_db, sample_student):
        student_service.update_student(sample_student["id"], {
            "student_code": "STU001",
            "name": "Rahul Updated",
            "class_name": "11",
            "division": "B",
        })
        updated = student_service.get_student(sample_student["id"])
        assert updated["name"] == "Rahul Updated"
        assert updated["class_name"] == "11"

    def test_update_duplicate_code_raises(self, fresh_db):
        student_service.add_student({"student_code": "S1", "name": "First"})
        s2_id = student_service.add_student({"student_code": "S2", "name": "Second"})
        with pytest.raises(ServiceError, match="already exists"):
            student_service.update_student(s2_id, {
                "student_code": "S1",
                "name": "Second",
            })

    def test_delete_student(self, fresh_db, sample_student):
        student_service.delete_student(sample_student["id"])
        assert student_service.get_student(sample_student["id"]) is None

    def test_delete_with_active_issue_raises(self, fresh_db, sample_issue):
        with pytest.raises(ServiceError, match="issued"):
            student_service.delete_student(sample_issue["student_id"])

    def test_get_pending_count(self, fresh_db, sample_issue):
        count = student_service.get_pending_count(sample_issue["student_id"])
        assert count == 1

    def test_get_student_history(self, fresh_db, sample_issue):
        history = student_service.get_student_history(sample_issue["student_id"])
        assert len(history) >= 1
        assert history[0]["book_title"] == sample_issue["book_title"]

    # -- Division uppercase tests -------------------------------------------

    def test_add_student_uppercases_division_a(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_A", "name": "Test A",
            "division": "a",
        })
        student = student_service.get_student(sid)
        assert student["division"] == "A"

    def test_add_student_uppercases_division_b(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_B", "name": "Test B",
            "division": "b",
        })
        student = student_service.get_student(sid)
        assert student["division"] == "B"

    def test_add_student_uppercases_division_multi_word(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_MW", "name": "Test MW",
            "division": "science a",
        })
        student = student_service.get_student(sid)
        assert student["division"] == "SCIENCE A"

    def test_add_student_uppercases_division_mixed_case(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_MC", "name": "Test MC",
            "division": "mixedCase",
        })
        student = student_service.get_student(sid)
        assert student["division"] == "MIXEDCASE"

    def test_add_student_strips_and_uppercases_division(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_WS", "name": "Test WS",
            "division": "  c  ",
        })
        student = student_service.get_student(sid)
        assert student["division"] == "C"

    def test_add_student_empty_division_is_none(self, fresh_db):
        sid = student_service.add_student({
            "student_code": "DIV_EM", "name": "Test EM",
            "division": "",
        })
        student = student_service.get_student(sid)
        assert student["division"] is None

    def test_update_student_uppercases_division(self, fresh_db, sample_student):
        student_service.update_student(sample_student["id"], {
            "student_code": sample_student["student_code"],
            "name": sample_student["name"],
            "division": "lowercase",
        })
        updated = student_service.get_student(sample_student["id"])
        assert updated["division"] == "LOWERCASE"

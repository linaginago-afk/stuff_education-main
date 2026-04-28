from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import schemas
from ..config import PASSING_SCORE
from ..database import get_db
from ..deps import require_admin
from ..models import AnswerOption, Question, Test, TestAttempt, TestAttemptAnswer, User

router = APIRouter(prefix="/api/admin", tags=["admin-reports"])


def _collect_results(db: Session, test_id: int | None, user_id: int | None):
    query = (
        db.query(
            TestAttempt.user_id,
            User.full_name,
            TestAttempt.test_id,
            Test.title,
            func.max(TestAttempt.score_percent).label("best_score"),
            func.count(TestAttempt.id).label("attempts"),
        )
        .join(User, User.id == TestAttempt.user_id)
        .join(Test, Test.id == TestAttempt.test_id)
        .group_by(TestAttempt.user_id, TestAttempt.test_id, User.full_name, Test.title)
    )
    if test_id:
        query = query.filter(TestAttempt.test_id == test_id)
    if user_id:
        query = query.filter(TestAttempt.user_id == user_id)
    return query.all()


@router.get("/results", response_model=list[schemas.ResultSummary])
def results(
    test_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = _collect_results(db, test_id, user_id)
    data = [
        schemas.ResultSummary(
            user_id=row.user_id,
            user_name=row.full_name,
            test_id=row.test_id,
            test_title=row.title,
            best_score=row.best_score,
            attempts=row.attempts,
            passed=row.best_score >= PASSING_SCORE,
        )
        for row in rows
    ]
    if status == "passed":
        data = [d for d in data if d.passed]
    elif status == "failed":
        data = [d for d in data if not d.passed]
    return data[offset : offset + limit]


@router.get("/results/export")
def export_results(
    test_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = _collect_results(db, test_id, user_id)
    data = []
    for row in rows:
        passed = row.best_score >= PASSING_SCORE
        if status == "passed" and not passed:
            continue
        if status == "failed" and passed:
            continue
        data.append(
            {
                "user_id": row.user_id,
                "user_name": row.full_name,
                "test_id": row.test_id,
                "test_title": row.title,
                "best_score": row.best_score,
                "attempts": row.attempts,
                "passed": "passed" if passed else "failed",
            }
        )
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=["user_id", "user_name", "test_id", "test_title", "best_score", "attempts", "passed"]
    )
    writer.writeheader()
    writer.writerows(data)
    # Excel дружелюбный UTF-8: кодируем как utf-8-sig (с BOM)
    csv_bytes = buffer.getvalue().encode("utf-8-sig")
    return PlainTextResponse(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )


@router.get("/users/{user_id}/attempts", response_model=list[schemas.DetailedAttempt])
def user_attempts(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    attempts = (
        db.query(TestAttempt)
        .filter(TestAttempt.user_id == user_id)
        .order_by(TestAttempt.finished_at.desc())
        .all()
    )
    return attempts


@router.get("/users/{user_id}/attempts/details", response_model=list[schemas.AttemptDetailed])
def user_attempt_details(
    user_id: int,
    test_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    attempts_query = db.query(TestAttempt).filter(TestAttempt.user_id == user_id)
    if test_id:
        attempts_query = attempts_query.filter(TestAttempt.test_id == test_id)
    attempts = attempts_query.order_by(TestAttempt.finished_at.desc()).all()
    if not attempts:
        return []

    attempt_ids = [a.id for a in attempts]
    answers_rows = (
        db.query(
            TestAttemptAnswer.attempt_id,
            TestAttemptAnswer.question_id,
            TestAttemptAnswer.answer_option_id,
            Question.text.label("question_text"),
            AnswerOption.text.label("selected_option_text"),
        )
        .join(Question, Question.id == TestAttemptAnswer.question_id)
        .join(AnswerOption, AnswerOption.id == TestAttemptAnswer.answer_option_id)
        .filter(TestAttemptAnswer.attempt_id.in_(attempt_ids))
        .all()
    )

    question_ids = {row.question_id for row in answers_rows}
    correct_options = (
        db.query(AnswerOption)
        .filter(AnswerOption.question_id.in_(question_ids), AnswerOption.is_correct == True)
        .all()
    )
    correct_map = {opt.question_id: opt for opt in correct_options}

    answers_by_attempt: dict[int, list[schemas.AttemptAnswerDetailed]] = {a.id: [] for a in attempts}
    for row in answers_rows:
        correct = correct_map.get(row.question_id)
        answers_by_attempt[row.attempt_id].append(
            schemas.AttemptAnswerDetailed(
                question_id=row.question_id,
                question_text=row.question_text,
                selected_option_id=row.answer_option_id,
                selected_option_text=row.selected_option_text,
                correct_option_id=correct.id if correct else row.answer_option_id,
                correct_option_text=correct.text if correct else row.selected_option_text,
                is_correct=bool(correct and correct.id == row.answer_option_id),
            )
        )

    result: list[schemas.AttemptDetailed] = []
    for attempt in attempts:
        result.append(
            schemas.AttemptDetailed(
                id=attempt.id,
                test_id=attempt.test_id,
                score_percent=attempt.score_percent,
                passed=attempt.passed,
                finished_at=attempt.finished_at,
                answers=answers_by_attempt.get(attempt.id, []),
            )
        )
    return result

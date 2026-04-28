from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    full_name: str
    username: str
    role: str
    department: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=4)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=4)
    role: Optional[str] = None
    department: Optional[str] = None


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class AnswerOptionBase(BaseModel):
    text: str
    is_correct: bool = False


class AnswerOptionCreate(AnswerOptionBase):
    pass


class AnswerOptionOut(AnswerOptionBase):
    id: int

    class Config:
        orm_mode = True


class AnswerOptionPublic(BaseModel):
    id: int
    text: str

    class Config:
        orm_mode = True


class QuestionBase(BaseModel):
    text: str


class QuestionCreate(QuestionBase):
    answer_options: List[AnswerOptionCreate]


class QuestionOut(QuestionBase):
    id: int
    answer_options: List[AnswerOptionOut]

    class Config:
        orm_mode = True


class QuestionPublic(BaseModel):
    id: int
    text: str
    answer_options: List[AnswerOptionPublic]

    class Config:
        orm_mode = True


class TestBase(BaseModel):
    title: str
    description: Optional[str] = None


class TestCreate(TestBase):
    questions: Optional[List[QuestionCreate]] = None


class TestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class TestOut(TestBase):
    id: int
    created_by: int
    created_at: datetime
    questions: List[QuestionOut] = []

    class Config:
        orm_mode = True


class TestPublic(TestBase):
    id: int
    questions: List[QuestionPublic]

    class Config:
        orm_mode = True


class AssignmentRequest(BaseModel):
    user_ids: List[int]


class SubmitAnswer(BaseModel):
    question_id: int
    answer_option_id: int


class SubmitAttemptRequest(BaseModel):
    answers: List[SubmitAnswer]


class AttemptAnswerOut(BaseModel):
    question_id: int
    answer_option_id: int

    class Config:
        orm_mode = True


class AttemptOut(BaseModel):
    id: int
    test_id: int
    started_at: datetime
    finished_at: datetime
    score_percent: float
    passed: bool
    answers: List[AttemptAnswerOut]

    class Config:
        orm_mode = True


class AttemptAnswerDetailed(BaseModel):
    question_id: int
    question_text: str
    selected_option_id: int
    selected_option_text: str
    correct_option_id: int
    correct_option_text: str
    is_correct: bool


class AttemptDetailed(BaseModel):
    id: int
    test_id: int
    score_percent: float
    passed: bool
    finished_at: datetime
    answers: List[AttemptAnswerDetailed]


class ProgressItem(BaseModel):
    test_id: int
    test_title: str
    best_score: float
    attempts: int
    last_attempt_date: Optional[datetime] = None


class ResultSummary(BaseModel):
    user_id: int
    user_name: str
    test_id: int
    test_title: str
    best_score: float
    attempts: int
    passed: bool


class DetailedAttempt(BaseModel):
    id: int
    test_id: int
    score_percent: float
    passed: bool
    finished_at: datetime

    class Config:
        orm_mode = True

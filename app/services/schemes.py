from pydantic import BaseModel, Field
from typing import List, Optional


class Item(BaseModel):
    id: int = Field(description="id of the subsubject")
    name: str = Field(description="name of the subsubject")
    prerequisites: List[int] = Field(description="ids of the prerequisites subsubdomains")

class Tree(BaseModel):
    main_subject: str = Field(description="name of the subject")
    items: List[Item] = Field("subsubjects of the subject")

class QuestionScheme(BaseModel):
    question_text: str = Field(description="The question itself")
    type: str = "mcq"
    realAnswer: str = Field(description="the real answer")
    options: List[str]
    explanation: str = Field(description="why it is the real answer")

class QuizScheme(BaseModel):
    questions: List[QuestionScheme]

class VideoAnalysis(BaseModel):
    id: str = Field(description="key of the video")
    reason: str = Field(description="courte description de pourquoi c'est la meilleure video")

class VideoResult(BaseModel):
    elements: List[VideoAnalysis]
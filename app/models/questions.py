from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Question:
    id: str
    text: str
    variable_name: str
    required: bool = True


@dataclass
class QuestionSet:
    questions: list[Question] = field(default_factory=list)
    intro_prompt: str = ""

    @classmethod
    def from_yaml(cls, path: Path) -> "QuestionSet":
        with open(path) as f:
            data = yaml.safe_load(f)
        questions = [Question(**q) for q in data.get("questions", [])]
        return cls(
            questions=questions,
            intro_prompt=data.get("intro_prompt", ""),
        )

    def formatted_list(self) -> str:
        return "\n".join(
            f"{i + 1}. {q.text}" for i, q in enumerate(self.questions)
        )

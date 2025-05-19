from typing import Any, Dict, List, TypedDict


class TaskFields(TypedDict):
    name: str
    required: bool


class TaskPattern(TypedDict):
    name: str
    description: str
    fields: List[TaskFields]


class JiraConfig(TypedDict):
    task_patterns: List[TaskPattern]


class GithubConfig(TypedDict):
    repository: str
    base_branch: str
    pr_template: str


class AiderConfig(TypedDict):
    prompt_template: str
    model: str
    temperature: float


class ProjectConfig(TypedDict):
    directory: str
    description: str
    repository: str


class Config(TypedDict):
    jira: JiraConfig
    github: GithubConfig
    aider: AiderConfig
    projects: Dict[str, ProjectConfig]


class Task(TypedDict):
    key: str
    title: str
    description: str
    type: str
    project: str
    fields: Dict[str, Any] 
#!/usr/bin/env python

from typing import Dict, List, Union

from onefuzztypes.enums import ContainerType
from onefuzztypes.models import (
    JobConfig,
    NotificationConfig,
    TaskConfig,
    TaskContainers,
)
from pydantic import BaseModel, root_validator, validator

from .enums import UserFieldOperation, UserFieldType

TEMPLATE_USER_DATA = Union[bool, int, str, Dict[str, str], List[str]]


class UserFieldLocation(BaseModel):
    op: UserFieldOperation
    path: str


class UserField(BaseModel):
    name: str
    type: UserFieldType
    locations: List[UserFieldLocation]

    @validator("locations", allow_reuse=True)
    def check_locations(cls, value: List) -> List:
        if len(value) == 0:
            raise ValueError("must provide at least one location")
        return value


class OnefuzzTemplateNotification(BaseModel):
    container_type: ContainerType
    notification: NotificationConfig


class OnefuzzTemplate(BaseModel):
    job: JobConfig
    tasks: List[TaskConfig]
    notifications: List[OnefuzzTemplateNotification]
    required_fields: List[UserField]
    optional_fields: List[UserField]

    @root_validator()
    def check_task_prereqs(cls, data: Dict) -> Dict:
        for idx, task in enumerate(data["tasks"]):
            # prereq_tasks must refer to previously defined tasks, using the u128
            #  representation of the UUID as an index
            if task.prereq_tasks:
                for prereq in task.prereq_tasks:
                    if prereq.int >= idx:
                        raise Exception(f"invalid task reference: {idx} - {prereq}")
        return data

    @root_validator()
    def check_fields(cls, data: Dict) -> Dict:
        seen = set()
        seen_path = set()

        for entry in (
            TEMPLATE_BASE_FIELDS + data["required_fields"] + data["optional_fields"]
        ):
            # field names, which are sent to the user for filing out, must be specified
            # once and only once
            if entry.name in seen:
                raise Exception(f"duplicate field found: {entry.name}")
            seen.add(entry.name)

            # location.path, the location in the json doc that is modified,
            # must be specified once and only once
            for location in entry.locations:
                if location.path in seen_path:
                    raise Exception(f"duplicate path found: {location.path}")
                seen_path.add(location.path)

        return data


class OnefuzzTemplateRequest(BaseModel):
    template_name: str
    user_fields: Dict[str, TEMPLATE_USER_DATA]
    containers: List[TaskContainers]


class OnefuzzTemplateField(BaseModel):
    name: str
    type: UserFieldType
    required: bool


class OnefuzzTemplateConfig(BaseModel):
    user_fields: List[OnefuzzTemplateField]
    containers: List[ContainerType]


TEMPLATE_BASE_FIELDS = [
    UserField(
        name="project",
        type=UserFieldType.Str,
        locations=[
            UserFieldLocation(
                op=UserFieldOperation.replace,
                path="/job/project",
            ),
        ],
    ),
    UserField(
        name="name",
        type=UserFieldType.Str,
        locations=[
            UserFieldLocation(
                op=UserFieldOperation.replace,
                path="/job/name",
            ),
        ],
    ),
    UserField(
        name="build",
        type=UserFieldType.Str,
        locations=[
            UserFieldLocation(
                op=UserFieldOperation.replace,
                path="/job/build",
            ),
        ],
    ),
]

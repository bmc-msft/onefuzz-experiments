#!/usr/bin/env python

# TODO:
# * enums (StatsFormat)
# * platform discovery?  We auto-differentiate between windows and linux tasks now
#
# Implementation details:
# * job_id in the TaskConfig is can be an arbitrary UUID and is overwritten at template evaluation
# * To support back-referencing tasks, such as in TaskConfig.prereq_tasks, use the a hard-coded
#   u128 representation of the task_id as an index into the task list.
# * To support hard-coding containers (such as 'afl-pp') rather than requiring the request to define
#   the containers is done by "If TaskContainer.name is set, use it.  Else, user must define it"
# * The same container used for two different contexts (inputs in libfuzzer_fuzz and
#   readonly_inputs for libfuzzer_coverage) isn't supported.  As is, this will require extending
#   coverage type tasks to support inputs and readonly_inputs.
#
# Differences between this and `libfuzzer basic template`
# * how do we specify notifications on the CLI rather than as part of the template?

from jsonpatch import apply_patch
import json
from typing import Dict, Any, List, Union
from uuid import UUID
from pydantic import BaseModel, root_validator, validator
from onefuzz.api import Onefuzz
from onefuzztypes.enums import ContainerType, TaskType
from onefuzztypes.models import (
    NotificationConfig,
    JobConfig,
    TaskConfig,
    TeamsTemplate,
    TaskDetails,
    TaskPool,
    TaskContainers,
)
from enum import Enum


USER_DATA = Union[bool, int, str, Dict[str, str], List[str]]


class UserFieldOperation(Enum):
    add = "add"
    replace = "replace"


class UserFieldType(Enum):
    Bool = "Bool"
    Int = "Int"
    Str = "Str"
    DictStr = "DictStr"
    ListStr = "ListStr"


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

        for entry in BASE_FIELDS + data["required_fields"] + data["optional_fields"]:
            # field names, which are sent to the user for filing out, must be specified
            # once and only once
            if entry.name in seen:
                raise Exception(f"duplicate field found: {entry.name}")
            seen.add(entry.name)

            # location.path, the location in the json doc that is modified, must be specified
            # once and only once
            for location in entry.locations:
                if location.path in seen_path:
                    raise Exception(f"duplicate path found: {location.path}")
                seen_path.add(location.path)

        return data


class OnefuzzTemplateRequest(BaseModel):
    template_name: str
    user_fields: Dict[str, USER_DATA]
    containers: List[TaskContainers]


class OnefuzzTemplateField(BaseModel):
    name: str
    type: UserFieldType
    required: bool


class OnefuzzTemplateConfig(BaseModel):
    user_fields: List[OnefuzzTemplateField]
    containers: List[ContainerType]


BASE_FIELDS = [
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


def template_container_types(template: OnefuzzTemplate) -> List[ContainerType]:
    return list(set(y.type for x in template.tasks for y in x.containers if not y.name))


def build_input_config(template: OnefuzzTemplate) -> OnefuzzTemplateConfig:
    user_fields = [
        OnefuzzTemplateField(name=x.name, type=x.type, required=True)
        for x in BASE_FIELDS + template.required_fields
    ] + [
        OnefuzzTemplateField(name=x.name, type=x.type, required=False)
        for x in template.optional_fields
    ]
    containers = template_container_types(template)

    return OnefuzzTemplateConfig(
        user_fields=user_fields,
        containers=containers,
    )


def build_patches(data: USER_DATA, field: UserField) -> List[Dict[str, USER_DATA]]:
    patches = []

    if field.type == UserFieldType.Bool and not isinstance(data, bool):
        raise Exception("invalid bool field")
    if field.type == UserFieldType.Int and not isinstance(data, int):
        raise Exception("invalid int field")
    if field.type == UserFieldType.Str and not isinstance(data, str):
        raise Exception("invalid str field")
    if field.type == UserFieldType.DictStr and not isinstance(data, dict):
        raise Exception("invalid DictStr field")
    if field.type == UserFieldType.ListStr and not isinstance(data, list):
        raise Exception("invalid ListStr field")

    for location in field.locations:
        patches.append(
            {
                "op": location.op.name,
                "path": location.path,
                "value": data,
            }
        )

    return patches


def render(
    request: OnefuzzTemplateRequest, template: OnefuzzTemplate
) -> OnefuzzTemplate:
    patches = []
    seen = set()

    for name in request.user_fields:
        for field in BASE_FIELDS + template.required_fields + template.optional_fields:
            if field.name == name:
                if name in seen:
                    raise ValueError(f"duplicate specification: {name}")
                seen.add(name)

        if name not in seen:
            raise ValueError(f"extra field: {name}")

    for field in BASE_FIELDS + template.required_fields:
        if field.name not in request.user_fields:
            raise ValueError(f"missing required field: {field.name}")
        patches += build_patches(request.user_fields[field.name], field)

    for field in template.optional_fields:
        if field.name not in request.user_fields:
            continue
        patches += build_patches(request.user_fields[field.name], field)

    raw = json.loads(template.json())
    updated = apply_patch(raw, patches)
    rendered = OnefuzzTemplate.parse_obj(updated)

    used_containers = []
    for task in rendered.tasks:
        for task_container in task.containers:
            if task_container.name:
                continue

            for entry in request.containers:
                if entry.type != task_container.type:
                    continue
                task_container.name = entry.name
                used_containers.append(entry)

            if not task_container.name:
                raise Exception(f"missing container definition {task_container.type}")

    for entry in request.containers:
        if entry not in used_containers:
            raise Exception(f"unused container in request: {entry}")

    return rendered


TEMPLATES = {
    "libfuzzer_basic": OnefuzzTemplate(
        job=JobConfig(project="", name="", build="", duration=1),
        tasks=[
            TaskConfig(
                job_id=UUID(int=0),
                task=TaskDetails(
                    type=TaskType.libfuzzer_fuzz,
                    duration=1,
                    target_exe="",
                    target_env={},
                    target_options=[],
                ),
                pool=TaskPool(count=1, pool_name=""),
                containers=[
                    TaskContainers(name="", type=ContainerType.setup),
                    TaskContainers(name="", type=ContainerType.crashes),
                    TaskContainers(name="", type=ContainerType.inputs),
                ],
                tags={},
            ),
            TaskConfig(
                job_id=UUID(int=0),
                prereq_tasks=[UUID(int=0)],
                task=TaskDetails(
                    type=TaskType.libfuzzer_crash_report,
                    duration=1,
                    target_exe="",
                    target_env={},
                    target_options=[],
                ),
                pool=TaskPool(count=1, pool_name=""),
                containers=[
                    TaskContainers(name="", type=ContainerType.setup),
                    TaskContainers(name="", type=ContainerType.crashes),
                    TaskContainers(name="", type=ContainerType.no_repro),
                    TaskContainers(name="", type=ContainerType.reports),
                    TaskContainers(name="", type=ContainerType.unique_reports),
                ],
                tags={},
            ),
            TaskConfig(
                job_id=UUID(int=0),
                prereq_tasks=[UUID(int=0)],
                task=TaskDetails(
                    type=TaskType.libfuzzer_coverage,
                    duration=1,
                    target_exe="",
                    target_env={},
                    target_options=[],
                ),
                pool=TaskPool(count=1, pool_name=""),
                containers=[
                    TaskContainers(name="", type=ContainerType.setup),
                    TaskContainers(name="", type=ContainerType.readonly_inputs),
                    TaskContainers(name="", type=ContainerType.coverage),
                ],
                tags={},
            ),
        ],
        notifications=[
            # OnefuzzTemplateNotification(
            #     container_type=ContainerType.unique_reports,
            #     notification=NotificationConfig(config=TeamsTemplate(url="foo")),
            # )
        ],
        required_fields=[
            UserField(
                name="pool_name",
                type=UserFieldType.Str,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/pool/pool_name",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/pool/pool_name",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/pool/pool_name",
                    ),
                ],
            ),
            UserField(
                name="target_exe",
                type=UserFieldType.Str,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/target_exe",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/target_exe",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/task/target_exe",
                    ),
                ],
            ),
        ],
        optional_fields=[
            UserField(
                name="duration",
                type=UserFieldType.Int,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/duration",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/duration",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/task/duration",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace, path="/job/duration"
                    ),
                ],
            ),
            UserField(
                name="target_workers",
                type=UserFieldType.Int,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/target_workers",
                    ),
                ],
            ),
            UserField(
                name="vm_count",
                type=UserFieldType.Int,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/pool/count",
                    ),
                ],
            ),
            UserField(
                name="target_options",
                type=UserFieldType.ListStr,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/target_options",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/target_options",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/task/target_options",
                    ),
                ],
            ),
            UserField(
                name="target_env",
                type=UserFieldType.ListStr,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/target_env",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/target_env",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/task/target_env",
                    ),
                ],
            ),
            UserField(
                name="reboot_after_setup",
                type=UserFieldType.Bool,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/0/task/reboot_after_setup",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/reboot_after_setup",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/2/task/reboot_after_setup",
                    ),
                ],
            ),
            UserField(
                name="check_retry_count",
                type=UserFieldType.Int,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/check_retry_count",
                    ),
                ],
            ),
            UserField(
                name="target_timeout",
                type=UserFieldType.Int,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.replace,
                        path="/tasks/1/task/target_timeout",
                    ),
                ],
            ),
            UserField(
                name="tags",
                type=UserFieldType.DictStr,
                locations=[
                    UserFieldLocation(
                        op=UserFieldOperation.add,
                        path="/tasks/0/tags",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.add,
                        path="/tasks/1/tags",
                    ),
                    UserFieldLocation(
                        op=UserFieldOperation.add,
                        path="/tasks/2/tags",
                    ),
                ],
            ),
        ],
    )
}


def execute(request: OnefuzzTemplateRequest, config: OnefuzzTemplate) -> None:
    # This is intended to emulate what the service would execute, which assumes
    # the storage containers have been created and content uploaded to them.

    o = Onefuzz()

    for template_notification in config.notifications:
        for task_container in request.containers:
            if task_container.type == template_notification.container_type:
                o.notifications.create(
                    task_container.name, template_notification.notification
                )

    job = o.jobs.create_with_config(config.job)
    tasks = []
    for task_config in config.tasks:
        task_config.job_id = job.job_id
        if task_config.prereq_tasks:
            # the model checker verifies prereq_tasks in u128 form are index refs to
            # previously generated tasks
            task_config.prereq_tasks = [
                tasks[x.int].task_id for x in task_config.prereq_tasks
            ]
        tasks.append(o.tasks.create_with_config(task_config))


def main():
    import logging

    logging.basicConfig(level=logging.DEBUG)
    template = TEMPLATES["libfuzzer_basic"]
    # print("template:\n", template.json(indent=4))

    for_cli = build_input_config(template)
    print("fields for CLI:", for_cli.json(indent=4))

    request = OnefuzzTemplateRequest(
        template_name="libfuzzer",
        user_fields={
            "project": "my project name",
            "name": "my target name",
            "build": "build # here",
            "pool_name": "windows",
            "target_exe": "fuzz.exe",
        },
        containers=[
            {"name": "mynorepro", "type": "no_repro"},
            {"name": "mysetup", "type": "setup"},
            {"name": "myreports", "type": "reports"},
            {"name": "myuniq", "type": "unique_reports"},
            {"name": "mycrashes", "type": "crashes"},
            {"name": "mycoverage", "type": "coverage"},
            {"name": "myinputs", "type": "inputs"},
            {"name": "myinputs", "type": "readonly_inputs"},
        ],
    )

    print("request:\n", request.json(indent=4))

    rendered = render(request, template)
    assert rendered.job.project == "my project name"

    for entry in rendered.tasks:
        assert entry.task.target_exe == "fuzz.exe"

        for container in entry.containers:
            if container.type == ContainerType.setup:
                assert container.name == "mysetup"
            assert container.name != "", f"container name is empty {container}"

    execute(request, rendered)


if __name__ == "__main__":
    main()
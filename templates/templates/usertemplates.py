from typing import Optional
from uuid import UUID

from onefuzztypes.enums import ContainerType, TaskType
from onefuzztypes.models import (
    JobConfig,
    TaskConfig,
    TaskContainers,
    TaskDetails,
    TaskPool,
)

from .enums import UserFieldOperation, UserFieldType
from .models import OnefuzzTemplate, UserField, UserFieldLocation

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
                type=UserFieldType.DictStr,
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


def get_template(name: str) -> Optional[OnefuzzTemplate]:
    return TEMPLATES.get(name)

#!/usr/bin/env python

from onefuzz.api import Onefuzz

from templates.models import OnefuzzTemplate, OnefuzzTemplateRequest
from templates.template import build_input_config, render
from templates.usertemplates import get_template


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


def check(config: OnefuzzTemplate) -> None:
    assert config.job.project == "my project name"

    for entry in config.tasks:
        assert entry.task.target_exe == "fuzz.exe"

        for container in entry.containers:
            if container.type.name == "setup":
                assert container.name == "mysetup"
            assert container.name != "", f"container name is empty {container}"


def main() -> None:
    import logging

    logging.basicConfig(level=logging.DEBUG)
    template = get_template("libfuzzer_basic")
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
    check(rendered)
    execute(request, rendered)


if __name__ == "__main__":
    main()

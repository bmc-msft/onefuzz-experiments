# Declarative Job Templates

Provide the ability to maintain job templates, akin to `onefuzz template libfuzzer basic` at the service level.

This feature will enable maintaining job templates with user-customizable data alteration.

A declarative job template includes:
* a Job (JobConfig, as used by `onefuzz jobs create`)
* a list of Tasks (TaskConfig, which is used by `onefuzz tasks create`)
* a list of Notifications (NotificationConfig + container type, akin to what is used by `onefuzz notifications create`)
* a list of required and optional form fields used to update the aforementioned JobConfig, TaskConfig, and NotificationConfig entries at runtime.

The form fields allow for 'add' or 'replace' of basic field data using [jsonpatch](http://jsonpatch.com) semantics.

## Example form fields

This following field named `target_workers`, which is required to be an 'int', will replace the `target_workers` value of in the first task in the template.

```python
UserField(
    name="target_workers",
    type=UserFieldType.Int,
    locations=[
        UserFieldLocation(
            op=UserFieldOperation.replace,
            path="/tasks/0/task/target_workers",
        ),
    ],
)
```

## Allowed Data Types
As of right now, the data types allowed in configuring arbitrary components in the JobTemplate are:

* bool
* int
* str
* Dict\[str, str\]
* List\[str\]

## Referring to Tasks

The mechanism to refer to pre-existing tasks, such as how `libfuzzer_crash_report` requires `libfuzzer_fuzz` as a prerequisite, is done via specifying the prerequisite task_id.

To support such a reference in `OnefuzzTemplate`, specify the prerequisite TASK by the `u128` representation index in to the list of tasks.  Example, to refer to the first task, use:

```python
TaskConfig(
    prereq_tasks=[UUID(int=0)],
    ...
)
```

## Hardcoded verses Runtime-specified container names

To support differentiating `always use "afl-linux" for tools` verses `ask what container to use for setup`, if the container name is blank in the template, it will be provided as part of the `OnefuzzTemplateConfig` and in the resulting `OnefuzzTemplateRequest`.

## Specifying Notifications in the Template

The existing templates support adding a notification config on the command line, via `--notification_config`, but the templates themselves include default notifications by default.

Declarative job templates include optional support to configure notifications as part of the template, rather than requiring the user provide the configuration.

Example declarative job template that specifies using the aforementioned NotificationConfig for the `unique_reports` containers used in the Job.

```python
OnefuzzTemplateNotification(
    container_type=ContainerType.unique_reports,
    notification=NotificationConfig(config=TeamsTemplate(url="https://contoso.com/webhook-url-here")),
)
```


## Implementation Notes

### TODO
* enums (StatsFormat)
* platform discovery?  We auto-differentiate between windows and linux tasks
  now

### Implementation details
* job\_id in the TaskConfig is can be an arbitrary UUID and is overwritten at
  template evaluation

### Differences between this and `libfuzzer basic template`
* While this can be used to define notifications as part of a template, the SDK will need to support adding additional notifications at runtime, similar to how `--notification_config` works today.

## Items of note in the implementation
* [templates/usertemplates.py](templates/usertemplates.py): This implements the 'onefuzz template libfuzzer basic'
* [templates/models.py](templates/models.py): This implements the basic pydantic models used by this feature
* [templates/template.py](templates/template.py): This builds the "what do I ask the user to provide" (OnefuzzTemplateRequest) and "Evaluate the template, given the OnefuzzTemplateRequest)"
* [main.py](main.py) this emulates what will be done first by the SDK, then later by the service

## Output

This is the `OnefuzzTemplateConfig` for `libfuzzer_basic` template, which the CLI will need to turn into an argparse-based wrapper to generate `OnefuzzTemplateRequest` seen below.
```json
{
    "user_fields": [
        {
            "name": "project",
            "type": "Str",
            "required": true
        },
        {
            "name": "name",
            "type": "Str",
            "required": true
        },
        {
            "name": "build",
            "type": "Str",
            "required": true
        },
        {
            "name": "pool_name",
            "type": "Str",
            "required": true
        },
        {
            "name": "target_exe",
            "type": "Str",
            "required": true
        },
        {
            "name": "duration",
            "type": "Int",
            "required": false
        },
        {
            "name": "target_workers",
            "type": "Int",
            "required": false
        },
        {
            "name": "vm_count",
            "type": "Int",
            "required": false
        },
        {
            "name": "target_options",
            "type": "ListStr",
            "required": false
        },
        {
            "name": "target_env",
            "type": "ListStr",
            "required": false
        },
        {
            "name": "reboot_after_setup",
            "type": "Bool",
            "required": false
        },
        {
            "name": "check_retry_count",
            "type": "Int",
            "required": false
        },
        {
            "name": "target_timeout",
            "type": "Int",
            "required": false
        },
        {
            "name": "tags",
            "type": "DictStr",
            "required": false
        }
    ],
    "containers": [
        "inputs",
        "no_repro",
        "readonly_inputs",
        "reports",
        "coverage",
        "setup",
        "unique_reports",
        "crashes"
    ]
}
```

This is the a sample filled in `OnefuzzTemplateRequest` for said form
```json
{
    "template_name": "libfuzzer",
    "user_fields": {
        "project": "my project name",
        "name": "my target name",
        "build": "build # here",
        "pool_name": "windows",
        "target_exe": "fuzz.exe"
    },
    "containers": [
        {
            "type": "no_repro",
            "name": "mynorepro"
        },
        {
            "type": "setup",
            "name": "mysetup"
        },
        {
            "type": "reports",
            "name": "myreports"
        },
        {
            "type": "unique_reports",
            "name": "myuniq"
        },
        {
            "type": "crashes",
            "name": "mycrashes"
        },
        {
            "type": "coverage",
            "name": "mycoverage"
        },
        {
            "type": "inputs",
            "name": "myinputs"
        },
        {
            "type": "readonly_inputs",
            "name": "myinputs"
        }
    ]
}
```

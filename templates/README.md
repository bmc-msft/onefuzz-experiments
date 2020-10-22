# TODO
* enums (StatsFormat)
* platform discovery?  We auto-differentiate between windows and linux tasks
  now

# Implementation details
* job\_id in the TaskConfig is can be an arbitrary UUID and is overwritten at
  template evaluation
* To support back-referencing tasks, such as in TaskConfig.prereq\_tasks, use
  the a hard-coded u128 representation of the task\_id as an index into the
  task list.
* To support hard-coding containers (such as 'afl-pp') rather than requiring
  the request to define the containers is done by "If TaskContainer.name is
  set, use it.  Else, user must define it"
* The same container used for two different contexts (inputs in
  libfuzzer\_fuzz and readonly\_inputs for libfuzzer\_coverage) isn't supported.
  As is, this will require extending coverage type tasks to support inputs
  and readonly\_inputs.

# Differences between this and `libfuzzer basic template`
* how do we specify notifications on the CLI rather than as part of the template?


# Things to look at
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

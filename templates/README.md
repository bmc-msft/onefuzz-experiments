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

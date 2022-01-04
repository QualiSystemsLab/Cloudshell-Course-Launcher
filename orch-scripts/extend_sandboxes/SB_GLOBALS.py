EXTEND_SANDBOXES_DURATION_PARAM = "duration_minutes"

# USER GLOBAL INPUTS
TARGET_BLUEPRINT_INPUT = "Blueprint Course"
PARTICIPANTS_LIST_INPUT = "Participants List"
CLOUDSHELL_GROUP_INPUT = "Cloudshell Group"
DEPLOY_CONCURRENTLY_BOOL_INPUT = "Deploy Sandboxes Concurrently"
CONCURRENT_DEPLOY_LIMIT_INPUT = "Concurrent Deploy Limit"
HEALTH_CHECK_SANDBOX_INPUT = "Health Check First Sandbox"
GLOBAL_INPUTS_INPUT = "Sandbox Global Inputs"

# SANDBOX CONTROLLER SERVICE
SANDBOX_CONTROLLER_MODEL = "Sandbox Controller"

# SANDBOX CONTROLLER ATTRIBUTE NAMES
TARGET_BLUEPRINT_ATTR = "{}.Blueprint Name".format(SANDBOX_CONTROLLER_MODEL)
SANDBOX_OWNER_ATTR = "{}.Sandbox Owner".format(SANDBOX_CONTROLLER_MODEL)
GLOBAL_INPUTS_ATTR = "{}.Global Inputs".format(SANDBOX_CONTROLLER_MODEL)
SANDBOX_ID_ATTR = "{}.Sandbox Id".format(SANDBOX_CONTROLLER_MODEL)

# SANDBOX SHELL COMMAND NAMES
START_SANDBOX_COMMAND = "start_sandbox"
END_SANDBOX_COMMAND = "end_sandbox"
EXTEND_SANDBOX_COMMAND = "extend_sandbox"
SYNC_REMAINING_TIME_COMMAND = "sync_remaining_time"
START_SANDBOX_DURATION_PARAM = "duration_minutes"

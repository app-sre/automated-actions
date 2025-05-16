package authz

default allow := false

users := data.users
roles := data.roles

# Passen Sie diese URL an, falls Ihr API-Server unter einer anderen Adresse läuft.
default action_api_url := "http://automated-actions:8080/v1/actions"

action_api_url := opa.runtime().env.OPA_ACTION_API_URL if {
	opa.runtime().env.OPA_ACTION_API_URL != null
}

default action_api_token := ""

action_api_token := opa.runtime().env.OPA_ACTION_API_TOKEN if {
	opa.runtime().env.OPA_ACTION_API_TOKEN != null
}

default max_age_minutes := "60"

max_age_minutes := opa.runtime().env.MAX_AGE_MINUTES if {
	opa.runtime().env.MAX_AGE_MINUTES != null
}

# METADATA
# description: Allow access to an action if the user has the required permissions and the max_ops limit is not exceeded.
# entrypoint: true
# scope: document
allow if { # regal ignore:messy-rule
	# Check if the user has specific roles
	user_roles := users[input.username]
	some role_name in user_roles
	check_role_permissions(roles[role_name], input.username, input.obj, input.params)
}

allow if {
	# Check if there are default roles for all users
	default_roles := users["*"]
	some role_name in default_roles
	check_role_permissions(roles[role_name], input.username, input.obj, input.params)
}

check_role_permissions(role_permissions, username, current_input_obj, current_input_params) if {
	some permission in role_permissions
	object_matches(permission.obj, current_input_obj)
	valid_params(permission.params, current_input_params)
	max_ops_limit_not_exceeded(current_input_obj, permission.max_ops, username)
}

# Match any input if permission_obj is "*"
object_matches("*", _) := true

object_matches(permission_obj, input_obj) if {
	permission_obj == input_obj
}

valid_params(expected, provided) if {
	# Check that null values in expected mean that the key should not be present in provided
	null_keys := {k | expected[k] == null}
	every k in null_keys {
		not provided[k]
	}

	# For non-null values, ensure they match using regex
	non_null_keys := {k | expected[k] != null}
	every k in non_null_keys {
		regex.match(sprintf("(?i)%s", [expected[k]]), provided[k])
	}
}

handle_response(api_url, username, response) if {
	# Print a log message if the response is not 200
	response.status_code == 0
	print("error connecting to server:", response)
	false # regal ignore:constant-condition
}

handle_response(api_url, username, response) if {
	# Print a log message if the response is not 200
	response.status_code >= 300
	print(
		"ERROR: HTTP call to", api_url, "for user", username,
		"FAILED. Status:", response.status_code, "Raw Body:", response.raw_body,
	)
	false # regal ignore:constant-condition
}

handle_response(api_url, username, response) if {
	response.status_code == 200
}

handle_max_ops(username, current_obj_attempt, relevant_actions_count, max_ops) if {
	# Print a log message if the max_ops limit is exceeded
	relevant_actions_count >= max_ops
	print(
		"User", username, "has exceeded max_ops for action", current_obj_attempt,
		"Current count:", relevant_actions_count, "Max ops:", max_ops,
	)
	false # regal ignore:constant-condition
}

handle_max_ops(username, current_obj_attempt, relevant_actions_count, max_ops) if {
	relevant_actions_count < max_ops
}

# If max_ops is not defined, allow the action.
max_ops_limit_not_exceeded(current_obj_attempt, max_ops, username) if {
	not is_number(max_ops)
}

# Check if the max_ops limit is not exceeded for the given action and user.
max_ops_limit_not_exceeded(current_obj_attempt, max_ops, username) if {
	is_number(max_ops)

	# Prepare the API URL for the action list.
	api_url := sprintf("%s/actions?action_user=%s&max_age_minutes=%s", [action_api_url, username, max_age_minutes])

	response := http.send({
		"method": "GET",
		"url": api_url,
		"headers": {
			"Content-Type": "application/json",
			"Authorization": sprintf("Bearer %s", [action_api_token]),
		},
		"raise_error": false,
	})

	# Handle the response from the API.
	handle_response(api_url, username, response)

	# Count the number of actions that match the current object attempt and are not cancelled
	relevant_actions_count := count([
	action |
		some action in response.body
		action.name == current_obj_attempt
		action.status != "CANCELLED"
	])

	# Check if the max_ops limit is not exceeded for the given action and user.
	handle_max_ops(username, current_obj_attempt, relevant_actions_count, max_ops)
}

package authz

default within_rate_limits := false

# METADATA
# description: Allow access to an action if the user has the max_ops limit not exceeded.
# entrypoint: true
# scope: document
within_rate_limits if {
	# Check if the user has specific roles
	user_roles := data.users[input.username]
	some role_name in user_roles
	check_rate_limits(data.roles[role_name], input.username, input.obj)
}

within_rate_limits if {
	# Check if there are default roles for all users
	default_roles := data.users["*"]
	some role_name in default_roles
	check_rate_limits(data.roles[role_name], input.username, input.obj)
}

check_rate_limits(role_permissions, username, current_obj) if {
	some permission in role_permissions
	object_matches(permission.obj, current_obj)
	max_ops_limit_not_exceeded(current_obj, permission.max_ops, username)
}

# Match any input if permission_obj is "*"
object_matches("*", _) := true

object_matches(permission_obj, input_obj) if {
	permission_obj == input_obj
}

# If max_ops is not defined, allow the action.
max_ops_limit_not_exceeded(current_obj, max_ops, username) if {
	not is_number(max_ops)
}

# max_ops == 0 means no limit
max_ops_limit_not_exceeded(_, 0, _) := true

# Check if the max_ops limit is not exceeded for the given action and user.
max_ops_limit_not_exceeded(current_obj, max_ops, username) if {
	is_number(max_ops)

	action_api_url := opa.runtime().env.OPA_ACTION_API_URL
	action_api_token := opa.runtime().env.OPA_ACTION_API_TOKEN
	max_age_minutes := opa.runtime().env.OPA_MAX_AGE_MINUTES

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
		action.name == current_obj
		action.status != "CANCELLED"
	])

	# Check if the max_ops limit is not exceeded for the given action and user.
	handle_max_ops(username, current_obj, relevant_actions_count, max_ops)
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

handle_max_ops(username, current_obj, relevant_actions_count, max_ops) if {
	# Print a log message if the max_ops limit is exceeded
	relevant_actions_count >= max_ops
	print(
		"User", username, "has exceeded max_ops for action", current_obj,
		"Current count:", relevant_actions_count, "Max ops:", max_ops,
	)
	false # regal ignore:constant-condition
}

handle_max_ops(username, current_obj, relevant_actions_count, max_ops) if {
	relevant_actions_count < max_ops
}

package authz_test

import data.authz

_test_users_max_ops := {
	"user_max_ops_limited": ["role_max_ops_3"],
	"user_admin_max_ops": ["role_admin_max_ops_2"],
	"user_no_max_ops_def": ["role_no_max_ops_def"],
	"user_invalid_max_ops_type": ["role_max_ops_invalid_type"],
}

_test_roles_max_ops := {
	"role_max_ops_3": [{
		"obj": "limited-action",
		"max_ops": 3,
		"params": {"p1": "v1"},
	}],
	"role_admin_max_ops_2": [{
		"obj": "*",
		"max_ops": 2,
		"params": {},
	}],
	"role_no_max_ops_def": [{
		"obj": "unlimited-action",
		# no max_ops defined
		"params": {},
	}],
	"role_max_ops_invalid_type": [{
		"obj": "action-invalid-maxops",
		"max_ops": "not-a-number", # max_ops is not a number
		"params": {},
	}],
}

mock_runtime_with_env := {"env": {
	"OPA_ACTION_API_URL": "http://fake-api.example.com",
	"OPA_ACTION_API_TOKEN": "fake-token",
	"OPA_MAX_AGE_MINUTES": "30",
}}

mock_send_empty_actions(request) := response if {
	_ = request
	response := {"status_code": 200, "body": []} # No existing actions
}

# Scenario 1: Specific action ("limited-action") with max_ops = 3
test_max_ops_specific_action_count_0_allowed if {
	authz.within_rate_limits with input as {
		"username": "user_max_ops_limited",
		"obj": "limited-action",
		"params": {"p1": "v1"},
	}
		with http.send as mock_send_empty_actions
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

mock_send_count_2_relevant_actions(request) := response if {
	_ = request
	response := {"status_code": 200, "body": [
		{"name": "limited-action", "status": "COMPLETED"},
		{"name": "limited-action", "status": "RUNNING"},
		# Total 2 relevant actions
	]}
}

test_max_ops_specific_action_count_2_allowed if {
	authz.within_rate_limits with input as {
		"username": "user_max_ops_limited",
		"obj": "limited-action",
		"params": {"p1": "v1"},
	}
		with http.send as mock_send_count_2_relevant_actions
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

mock_send_count_3_relevant_actions(request) := response if {
	_ = request
	response := {"status_code": 200, "body": [
		{"name": "limited-action", "status": "COMPLETED"},
		{"name": "limited-action", "status": "RUNNING"},
		{"name": "limited-action", "status": "COMPLETED"},
		# Total 3 relevant actions, limit is 3, so count >= limit
	]}
}

test_max_ops_specific_action_count_3_denied if {
	not authz.within_rate_limits with input as {
		"username": "user_max_ops_limited",
		"obj": "limited-action",
		"params": {"p1": "v1"},
	}
		with http.send as mock_send_count_3_relevant_actions
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

# 2 relevant actions, 1 CANCELLED (ignored), 1 other obj (ignored)
# max_ops = 3. Relevant count is 2. 2 < 3, so allowed.
mock_send_mixed_status_and_obj(request) := response if {
	_ = request
	response := {"status_code": 200, "body": [
		{"name": "limited-action", "status": "COMPLETED"}, # Relevant
		{"name": "limited-action", "status": "RUNNING"}, # Relevant
		{"name": "limited-action", "status": "CANCELLED"}, # Ignored (status)
		{"name": "other-action", "status": "COMPLETED"}, # Ignored (obj)
	]}
}

test_max_ops_specific_action_count_2_plus_ignored_allowed if {
	authz.within_rate_limits with input as {
		"username": "user_max_ops_limited",
		"obj": "limited-action",
		"params": {"p1": "v1"},
	}
		with http.send as mock_send_mixed_status_and_obj
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

# Scenario 2: Admin role with obj: "*" and max_ops = 2
mock_send_admin_action_a_count_1(request) := response if {
	_ = request # request.url for user_admin_max_ops

	# 1 relevant for "admin-action-A"
	response := {"status_code": 200, "body": [{"name": "admin-action-A", "status": "COMPLETED"}]}
}

test_max_ops_admin_action_a_count_1_allowed if {
	authz.within_rate_limits with input as {
		"username": "user_admin_max_ops",
		"obj": "admin-action-A",
		"params": {},
	}
		with http.send as mock_send_admin_action_a_count_1
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

mock_send_admin_action_a_count_2(request) := response if {
	_ = request
	response := {"status_code": 200, "body": [
		{"name": "admin-action-A", "status": "COMPLETED"},
		{"name": "admin-action-A", "status": "RUNNING"},
		# 2 relevant for "admin-action-A", limit is 2, so count >= limit
	]}
}

test_max_ops_admin_action_a_count_2_denied if {
	not authz.within_rate_limits with input as {
		"username": "user_admin_max_ops",
		"obj": "admin-action-A",
		"params": {},
	}
		with http.send as mock_send_admin_action_a_count_2
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

mock_send_admin_action_a_at_limit(request) := response if {
	_ = request
	response := {"status_code": 200, "body": [
		{"name": "admin-action-A", "status": "COMPLETED"},
		{"name": "admin-action-A", "status": "RUNNING"},
		# No "admin-action-B" actions
	]}
}

test_max_ops_admin_action_b_allowed_while_action_a_at_limit if {
	# Count for "admin-action-A" is 2 (at limit for that action).
	# Current attempt is for "admin-action-B", count for "admin-action-B" is 0.
	# Should be allowed as max_ops is per specific action obj.
	authz.within_rate_limits with input as {
		"username": "user_admin_max_ops",
		"obj": "admin-action-B", # Attempting a different action
		"params": {},
	}
		with http.send as mock_send_admin_action_a_at_limit
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

# max_ops is defined but is not a number
test_max_ops_not_a_number_results_in_allowed if {
	# is_number(permission.max_ops) will be false for "not-a-number".
	authz.within_rate_limits with input as {
		"username": "user_invalid_max_ops_type",
		"obj": "action-invalid-maxops",
		"params": {},
	}
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
		# No 'with http.send as ...' needed.
with 		opa.runtime as mock_runtime_with_env
}

# API call to action-list fails
mock_send_api_error(request) := response if {
	_ = request
	response := {"status_code": 500, "body": {"error": "Internal Server Error"}}
}

test_max_ops_api_error_results_in_deny if {
	# This tests that "fail-open" behavior for the max_ops check part.
	not authz.within_rate_limits with input as {
		"username": "user_max_ops_limited",
		"obj": "limited-action",
		"params": {"p1": "v1"},
	}
		with http.send as mock_send_api_error
		with opa.runtime as mock_runtime_with_env
		with data.users as _test_users_max_ops
		with data.roles as _test_roles_max_ops
}

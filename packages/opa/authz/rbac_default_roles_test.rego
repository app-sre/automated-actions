package authz_test

import data.authz

test_default_me if {
	authz.authorized with input as {
		"username": "random-user",
		"obj": "me",
		"params": {},
	}
}

test_default_action_list if {
	authz.authorized with input as {
		"username": "random-user",
		"obj": "action-list",
		"params": {},
	}
}

test_default_action_list_action_user_param_not_allowed if {
	not authz.authorized with input as {
		"username": "random-user",
		"obj": "action-list",
		"params": {"action_user": "some-user"},
	}
}

test_default_action_detail_owner_match_allowed if {
	authz.authorized with input as {
		"username": "random-user",
		"obj": "action-detail",
		"params": {"owner": "random-user"},
	}
}

# FIND-005: the default role must not let a user view another user's action.
test_default_action_detail_owner_mismatch_denied if {
	not authz.authorized with input as {
		"username": "random-user",
		"obj": "action-detail",
		"params": {"owner": "someone-else"},
	}
}

test_default_action_cancel_owner_match_allowed if {
	authz.authorized with input as {
		"username": "random-user",
		"obj": "action-cancel",
		"params": {"owner": "random-user"},
	}
}

# FIND-005: the default role must not let a user cancel another user's action.
test_default_action_cancel_owner_mismatch_denied if {
	not authz.authorized with input as {
		"username": "random-user",
		"obj": "action-cancel",
		"params": {"owner": "someone-else"},
	}
}

test_default_action_list_action_user_param_is_allowed_for_opa if {
	authz.authorized with input as {
		"username": "open-policy-agent",
		"obj": "action-list",
		"params": {"action_user": "some-user"},
	}
}

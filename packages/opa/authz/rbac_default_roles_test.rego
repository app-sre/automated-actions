package authz_test

import data.authz

test_default_me if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "me",
		"params": {},
	}
}

test_default_action_list if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "action-list",
		"params": {},
	}
}

test_default_action_list_action_user_param_not_allowed if {
	not authz.allow with input as {
		"username": "random-user",
		"obj": "action-list",
		"params": {"action_user": "some-user"},
	}
}

test_default_action_detail if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "action-detail",
		"params": {},
	}
}

test_default_action_cancel if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "action-cancel",
		"params": {},
	}
}

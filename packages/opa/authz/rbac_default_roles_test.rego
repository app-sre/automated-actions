package authz_test

import data.authz

test_default_me if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "me",
		"params": {},
	}
}

test_default_task_list if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "task-list",
		"params": {},
	}
}

test_default_task_detail if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "task-detail",
		"params": {},
	}
}

test_default_task_cancel if {
	authz.allow with input as {
		"username": "random-user",
		"obj": "task-cancel",
		"params": {},
	}
}

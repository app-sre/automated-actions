package authz_test

import data.authz

test_user_objects if {
	objects := authz.objects with input as {"username": "user1"}
	expected := {"restart", "me", "task-cancel", "task-detail", "task-list"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

test_admin_objects if {
	objects := authz.objects with input as {"username": "admin-user"}
	expected := {"*", "me", "task-cancel", "task-detail", "task-list"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

test_unknown_user_objects if {
	objects := authz.objects with input as {"username": "unknown"}
	expected := {"me", "task-cancel", "task-detail", "task-list"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

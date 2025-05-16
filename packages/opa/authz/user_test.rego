package authz_test

import data.authz

_user_test_users := {
	"*": ["default"],
	"user1": ["test-team", "another-team"],
	"admin-user": ["admin"],
}

_user_test_roles := {
	"default": [{
		"obj": "default-action",
		"max_ops": null,
		"params": {},
	}],
	"test-team": [{
		"obj": "restart",
		"max_ops": null,
		"params": {
			"cluster": "^cluster-1$",
			"namespace": "example",
			"kind": "pod",
			"name": "^foobar.*",
		},
	}],
	"admin": [{
		"obj": "*",
		"max_ops": null,
		"params": {},
	}],
}

test_user_objects if {
	objects := authz.objects with input as {"username": "user1"}
		with data.users as _user_test_users
		with data.roles as _user_test_roles

	expected := {"default-action", "restart"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

test_admin_objects if {
	objects := authz.objects with input as {"username": "admin-user"}
		with data.users as _user_test_users
		with data.roles as _user_test_roles

	expected := {"*", "default-action"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

test_unknown_user_objects if {
	objects := authz.objects with input as {"username": "unknown"}
		with data.users as _user_test_users
		with data.roles as _user_test_roles

	expected := {"default-action"}
	every obj in expected {
		obj in objects
	}
	every obj in objects {
		obj in expected
	}
}

package authz_test

import data.authz

test_admin_allowed if {
	authz.allow with input as {
		"username": "admin-user",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
			"extra": "extra-value",
		},
	}
}

test_user_allowed if {
	authz.allow with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
}

test_user_allowed_extra_param if {
	authz.allow with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
			"extra": "extra-value",
		},
	}
}

test_user_denied_user if {
	not authz.allow with input as {
		"username": "another-user",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
}

test_user_denied_obj if {
	not authz.allow with input as {
		"username": "user1",
		"obj": "delete",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
}

test_user_denied_params if {
	not authz.allow with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "another-cluster",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
}

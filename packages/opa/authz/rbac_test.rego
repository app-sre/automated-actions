package authz_test

import data.authz

_test_users := {
	"user1": ["test-team", "another-team"],
	"admin-user": ["admin"],
}

_test_roles := {
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

test_admin_allowed if {
	authz.authorized with input as {
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
		with http.send as mock_send_empty_actions
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_allowed if {
	authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_case_insensitive if {
	authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "exaMPle",
			"kind": "POD",
			"name": "FOObar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_allowed_extra_param if {
	authz.authorized with input as {
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
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_denied_user if {
	not authz.authorized with input as {
		"username": "another-user",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_denied_obj if {
	not authz.authorized with input as {
		"username": "user1",
		"obj": "delete",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_denied_params if {
	not authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "another-cluster",
			"namespace": "example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

# A param pattern must match the whole value, not just a substring of it.
test_user_denied_namespace_substring_suffix if {
	not authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "example-prod",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

test_user_denied_namespace_substring_prefix if {
	not authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {
			"cluster": "cluster-1",
			"namespace": "other-example",
			"kind": "pod",
			"name": "foobar-123",
		},
	}
		with data.users as _test_users
		with data.roles as _test_roles
}

_test_roles_alternation := {"alt-team": [{
	"obj": "restart",
	"max_ops": null,
	"params": {"kind": "Pod|Deployment"},
}]}

test_user_alternation_pattern_exact_match_allowed if {
	authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {"kind": "Deployment"},
	}
		with data.users as {"user1": ["alt-team"]}
		with data.roles as _test_roles_alternation
}

# Each alternative in a "a|b" pattern must be anchored, not just the pattern as
# a whole: naively wrapping as "^(?i)a|b$" anchors "a" only at the start and "b"
# only at the end, so "XDeployment" would still match "b$" without a start anchor.
test_user_alternation_pattern_denied_partial_match if {
	not authz.authorized with input as {
		"username": "user1",
		"obj": "restart",
		"params": {"kind": "XDeployment"},
	}
		with data.users as {"user1": ["alt-team"]}
		with data.roles as _test_roles_alternation
}

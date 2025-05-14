package authz

default allow := false

users := data.users

roles := data.roles

allow if { # regal ignore:messy-rule
	# Check if the user has specific roles
	user_roles := users[input.username]
	some role in user_roles
	check_role_permissions(role)
}

allow if {
	# Check if there are default roles for all users
	default_roles := users["*"]
	some role in default_roles
	check_role_permissions(role)
}

check_role_permissions(role) if {
	permissions := roles[role] # regal ignore:external-reference
	some permission in permissions
	object_matches(permission.obj, input.obj) # regal ignore:external-reference
	valid_params(permission.params, input.params) # regal ignore:external-reference
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

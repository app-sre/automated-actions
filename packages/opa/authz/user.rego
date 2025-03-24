package authz

users := data.users

roles := data.roles

objects contains obj if {
	some role in users[input.username]
	some permission in roles[role]
	obj := permission.obj
}

objects contains obj if {
	some role in users["*"]
	some permission in roles[role]
	obj := permission.obj
}

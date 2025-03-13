import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

import yaml
from casbin import Enforcer
from casbin.model import Model
from casbin.persist.adapter import Adapter
from fastapi import Depends, HTTPException, Request

from automated_actions.config import settings

from .dependencies import UserDep

log = logging.getLogger(__name__)

CASBIN_MODEL = """
[request_definition]
r = sub, obj, params

[policy_definition]
p = sub, obj, params

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = (p.sub == "*" || g(r.sub, p.sub)) && (r.obj == p.obj) && (r.params == p.params)
"""

# TODO @cassing: Discuss with Rafa what the default policy should be.
# APPSRE-11601
DEFAULT_POLICY = {
    "p": [
        {"sub": "*", "obj": "me", "params": {}},
        {"sub": "*", "obj": "task-list", "params": {}},
        {"sub": "*", "obj": "task-detail", "params": {}},
        {"sub": "*", "obj": "task-cancel", "params": {}},
    ]
}


class CasbinAuthZ:
    def __init__(self, enforcer: Enforcer) -> None:
        self.enforcer = enforcer

    async def __call__(self, request: Request, user: UserDep) -> None:
        log.debug(f"Checking authorization for {user.email}: {request.url.path}")
        if not self.enforcer.enforce(
            user.username,
            request["route"].operation_id,
            request["path_params"],
        ):
            raise HTTPException(status_code=403, detail="Forbidden")


class YamlAdapter(Adapter):
    """Yaml file adapter for Casbin."""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    @staticmethod
    def _get_role_rules(policy: dict) -> list:
        """Compile casbin role rules from the yaml policy.

        Unfortunately, we can't use variables (e.g. 'g = user, role') in the role definition.
        Therefore, we have to hardcode the yaml keys here.
        """
        return [(rule["user"], rule["role"]) for rule in policy["g"]]

    @staticmethod
    def _get_policy_rules(policy: dict, key: str, values: Iterable[str]) -> list:
        """Compile casbin policy rules from the yaml policy.

        For example:

        [policy_definition]
        p = sub, obj, params

        Will create casbin rules like:

        [
            [yaml["sub"], yaml["obj"], yaml["params"]]
            ...
            [yaml["sub"], yaml["obj"], yaml["params"]]
        ]

        The order of the yaml values is determined by the order of the values in the policy_definition.
        """
        return [[rule[v] for v in values] for rule in policy[key]]

    def load_policy(self, model: Model) -> None:
        policy_file = Path(self._file_path)
        if not policy_file.exists():
            log.warning(
                f"Policy file {policy_file} does not exist. Using default policy."
            )
            policy = DEFAULT_POLICY
        else:
            policy = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            policy["p"] += DEFAULT_POLICY["p"]

        model.add_policies("g", "g", self._get_role_rules(policy))

        # policies. map the policy_definition variables to the actual yaml values
        for key in model["p"]:
            # get the policy values from the model
            values = [i.strip() for i in model["p"][key].value.split(",")]
            model.add_policies(
                "p",
                key,
                self._get_policy_rules(policy, key, values),
            )


def initialize_authz() -> CasbinAuthZ:
    """Initialize the casbin authorization module."""
    model = Model()
    model.load_model_from_text(CASBIN_MODEL)
    adapter = YamlAdapter(str(settings.policy_file))
    enforcer = Enforcer(model=model, adapter=adapter)
    return CasbinAuthZ(enforcer=enforcer)


async def get_authz(request: Request, user: UserDep) -> CasbinAuthZ:
    return await request.app.state.authz(request, user)


AuthZDep = Annotated[CasbinAuthZ, Depends(get_authz)]

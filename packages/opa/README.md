# `opa` Package - Authorization Policies 🛡️⚖️

Welcome, developer, to the `opa` package! This directory houses all the **Open Policy Agent (OPA) Rego policies** that define the authorization logic for the Automated Actions system. These policies determine *who* can do *what* under *which conditions*.

## 🎯 Overview

The Automated Actions API server queries an OPA instance (loaded with these policies) to make authorization decisions before allowing an action to be enqueued or executed. The policies are written in **Rego**, OPA's declarative policy language.

This package contains policies covering several aspects of authorization:

1. **Role-Based Access Control (RBAC):** Defining roles and the permissions associated with them.
2. **User Allowed Actions/Objects:** Determining which specific actions a user (based on their roles or other attributes) is permitted to trigger.
3. **Rate Limiting:** Enforcing limits on how frequently users or services can perform certain actions (though the primary state for rate limiting might be in DynamoDB, OPA can enforce decisions based on this data).
4. **Default Roles/Permissions:** Establishing baseline access rights.

Each set of policies is typically accompanied by its own **Rego tests** to ensure correctness and prevent regressions.

## 🏛️ Conceptual Overview

The OPA policies in this package are not evaluated in a vacuum. They work in concert with the `automated-actions` API server and configurations derived from `app-interface`.

### Policy Evaluation Flow

1. **API Request:** A user or system makes a request to the `automated-actions` API server to perform an action.
2. **Input Assembly:** Before making an authorization decision, the API server assembles an `input` document for OPA. This document contains:
    * User information (e.g., from the OIDC token).
    * Details of the requested action.
    * Relevant action parameters, e.g., resource identifiers.
3. **OPA Query:** The API server queries its configured OPA instance, sending the assembled `input` document.
4. **Policy Evaluation by OPA:**
    * **RBAC Policies:** OPA evaluates RBAC rules (e.g., `user_has_role`, `role_has_permission`) directly based on the user information in the `input` and the policy definitions within this package.
    * **Rate Limit Policies:**
        * The Rego policies for rate limiting retrieves the user's action history via a separate API call `action-list` to the `automated-actions` server.
        * They compare the count or frequency of past actions against `maxOps` (maximum operations). These thresholds (`maxOps`) are typically defined in `app-interface` and passed to OPA as part of the policies.
        * OPA then decides if the current request would exceed the rate limit.
    * **Allowed Actions:** Policies determine if the user, with their roles and permissions, is allowed to perform the specific requested action on the target resource.
5. **Decision:** OPA returns an authorization decision to the `automated-actions` API server.
6. **Enforcement:** The API server enforces OPA's decision. If allowed, the action proceeds; otherwise, it's rejected.

### Policy Generation from `app-interface`

A key aspect of this system is that parts of the authorization logic, particularly configurations like action definitions, role assignments, or rate limit thresholds (`maxOps`), are managed declaratively in `app-interface`.

* The [qontract-reconcile automated-actions-config integration](https://github.com/app-sre/qontract-reconcile/blob/4236821459c9d1bb833a1fc68c773cec53a781b1/reconcile/automated_actions/config/integration.py) plays a crucial role here.
* This integration reads settings from `app-interface` (e.g., which user groups get which roles, what are the `maxOps` for a specific action).
* It then **generates OPA-compatible data files (e.g., `data.json`) or even parts of Rego policies**. These generated files are then loaded into OPA alongside the static policies defined in this package.
* This allows for dynamic and centralized management of authorization configurations without needing to directly modify the core Rego policies for every configuration change. The static Rego policies in this package are designed to *consume* this generated data.

## 🧑‍💻 Development & Testing Policies

### Writing Rego

* Familiarize yourself with the [Rego language documentation](https://www.openpolicyagent.org/docs/latest/policy-language/).
* Use the [OPA VS Code extension](https://www.google.com/search?client=safari&rls=en&q=open+policy+agent+vscode&ie=UTF-8&oe=UTF-8) for syntax highlighting and evaluation.

### Testing Policies

* **OPA Test Framework:** OPA provides a built-in test framework. Test files end with `_test.rego`.
* **Running Tests:**

    ```bash
    # Test all policies in the current directory and subdirectories
    opa test .

    # Test policies in a specific directory
    opa test authz
    ```

## 🤝 Contributing

* When adding or modifying policies, always write corresponding tests.
* Keep policies modular and organized. Use helper functions in `lib/` for common logic.
* Ensure policy decisions are clear and auditable.
* Consider the performance implications of complex rules.

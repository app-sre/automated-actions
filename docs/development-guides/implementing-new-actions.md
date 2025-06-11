# Implementing New Actions in Automated Actions 🚀

Welcome to the guide on implementing new actions within the Automated Actions system! This document will walk you through the necessary steps to create a new action, from setting up the AWS interface to writing integration tests.

## Checklist for Implementing a New Action

- [ ] Define the 3rd party interface(s) in `automated-actions-utils`.
- [ ] Expose the action through FastAPI in `automated-actions`.
- [ ] Implement the Celery task for the action.
- [ ] Write unit tests for the action logic.
- [ ] Write integration tests for the new action.
- [ ] Regenerate the `automated-actions-client` using `make generate-client`.
- [ ] Update the action documentation in `actions.md`.
- [ ] Update the [automated-actions-config](https://github.com/app-sre/qontract-reconcile/blob/master/reconcile/automated_actions/config/integration.py) integrattion and the [/app-sre/automated-action-1.yml schema](https://github.com/app-sre/qontract-schemas/blob/main/schemas/app-sre/automated-action-1.yml)
- [ ] Configure the integration tests in app-interface to  allow and include the new action.
- [ ] Update the app-interface documentation to include the new action.

## Example Action: Reboot an RDS Instance

Please refer to the [:sparkles: [automated-actions] external-resource-rds-reboot action](https://github.com/app-sre/automated-actions/pull/95) PR for a detailed example of how to implement a new action that reboots an RDS instance. This PR serves as a comprehensive guide, showcasing the entire process from AWS setup to FastAPI endpoint creation and Celery task implementation.

## 🛠️ Steps to Implement a New Action

### automated-actions-utils - 3rd party interface(s)

Start by defining the 3rd party interface for your new action, e.g. additional AWS API methods.

### automated-actions- Define the Endpoints

Next, you need to expose your action through the FastAPI server. Follow these steps:

- **Create a New Router:** In the `automated_actions/api/v1/views` directory, create a new router file (e.g., `new_action.py`).
- **Define the Endpoint:** Use FastAPI decorators to define the HTTP method (GET, POST, etc.) and the endpoint path. Ensure to include request validation using Pydantic models.
- **Implement the Logic:** In the endpoint function, call the necessary Celery task methods to execute the action.

The [no-op](/packages/automated_actions/automated_actions/api/v1/views/no_op.py) action serves as a good starting point for understanding how to structure your new action's endpoint.

### Implement Celery Tasks

For actions that require asynchronous processing, implement a Celery task:

- **Create a New Task File:** In the `automated_actions/celery/<ACTION_NAME>/tasks.py` file, define a new task function.
- **Use the Interface:** Within the task, call the required 3rd party interface to perform the action.

A good example of a Celery task can be found in the [no-op](/packages/automated_actions/automated_actions/celery/external_resource/tasks.py) action.

### Write Tests

Testing is crucial to ensure your new action works as expected. You need to implement both unit tests for the action logic and integration tests for the FastAPI endpoint.

Use unit tests to verify the functionality of your API endpoint, the Celery task and the 3rd party interface.

For integration tests, follow these steps:

- **Create a Test File:** In the `integration_tests/tests/actions` directory, create a new test file (e.g., `test_new_action.py`).
- **Use Test Clients:** Utilize FastAPI's test client to simulate requests to your new endpoint.
- **Assert Responses:** Check that the responses are as expected and that the action is executed correctly.

Please refer to the already existing integration tests in the [integration_tests/tests/actions](/packages/integration_tests/tests/actions/) directory for examples of how to structure your tests.

### Regenerate the `automated-actions-client`

As you may know, the `automated-actions-client` is generated from the FastAPI OpenAPI schema. After implementing your new action, you need to regenerate the client:

```sh
make generate-client
```

### qontract-reconcile/qontract-schemas - Update the Integration

Next, you need to update the [automated-actions-config](https://github.com/app-sre/qontract-reconcile/blob/master/reconcile/automated_actions/config/integration.py) `qontract-reconcile` integration and the [/app-sre/automated-action-1.yml schema](https://github.com/app-sre/qontract-schemas/blob/main/schemas/app-sre/automated-action-1.yml) to include the new action and its arguments. See this [automated-actions-config PR](https://github.com/app-sre/qontract-reconcile/pull/5020) and this [automated-action-1.yml PR](https://github.com/app-sre/qontract-schemas/pull/838) for examples of how to update the integration and the schema.

### app-interface - Configure Integration Tests

To ensure your new action is configured in the integration tests, you need to update the app-interface integration test configuration. For example, [[automated-actions] configure RDS reboot integration test](https://gitlab.cee.redhat.com/service/app-interface/-/merge_requests/145517)

### Documentation

- Update the [action documentation](/actions.md) to include your new action.
- Update the [app-interface documentation](https://gitlab.cee.redhat.com/service/app-interface/-/blob/master/docs/app-sre/automated-actions/users/actions.md) to reflect the new action.

## 🚀 Conclusion

By following these steps, you can successfully implement a new action within the Automated Actions system. Ensure to adhere to coding standards and write comprehensive tests to maintain the integrity of the system. Happy coding!

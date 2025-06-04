# Implementing New Actions in Automated Actions 🚀

Welcome to the guide on implementing new actions within the Automated Actions system! This document will walk you through the necessary steps to create a new action, from setting up the AWS interface to writing integration tests.

## Example Action: Reboot an RDS Instance

Please refer to the [:sparkles: [automated-actions] external-resource-rds-reboot action](https://github.com/app-sre/automated-actions/pull/95) PR for a detailed example of how to implement a new action that reboots an RDS instance. This PR serves as a comprehensive guide, showcasing the entire process from AWS setup to FastAPI endpoint creation and Celery task implementation.

## 🛠️ Steps to Implement a New Action

### 1. automated-actions-utils - 3rd party interface(s)

Start by defining the 3rd party interface for your new action, e.g. additional AWS API methods.

### 2. automated-actions- Define the Endpoints

Next, you need to expose your action through the FastAPI server. Follow these steps:

- **Create a New Router:** In the `automated_actions/api/v1/views` directory, create a new router file (e.g., `new_action.py`).
- **Define the Endpoint:** Use FastAPI decorators to define the HTTP method (GET, POST, etc.) and the endpoint path. Ensure to include request validation using Pydantic models.
- **Implement the Logic:** In the endpoint function, call the necessary Celery task methods to execute the action.

The [no-op](/packages/automated_actions/automated_actions/api/v1/views/no_op.py) action serves as a good starting point for understanding how to structure your new action's endpoint.

### 3. Implement Celery Tasks

For actions that require asynchronous processing, implement a Celery task:

- **Create a New Task File:** In the `automated_actions/celery/<ACTION_NAME>/tasks.py` file, define a new task function.
- **Use the Interface:** Within the task, call the required 3rd party interface to perform the action.

A good example of a Celery task can be found in the [no-op](/packages/automated_actions/automated_actions/celery/external_resource/tasks.py) action.

### 4. Write Tests

Testing is crucial to ensure your new action works as expected. You need to implement both unit tests for the action logic and integration tests for the FastAPI endpoint.

Use unit tests to verify the functionality of your API endpoint, the Celery task and the 3rd party interface.

For integration tests, follow these steps:

- **Create a Test File:** In the `integration_tests/tests/actions` directory, create a new test file (e.g., `test_new_action.py`).
- **Use Test Clients:** Utilize FastAPI's test client to simulate requests to your new endpoint.
- **Assert Responses:** Check that the responses are as expected and that the action is executed correctly.

Please refer to the already existing integration tests in the [integration_tests/tests/actions](/packages/integration_tests/tests/actions/) directory for examples of how to structure your tests.

### 5. Regenerate the `automated-actions-client`

As you may know, the `automated-actions-client` is generated from the FastAPI OpenAPI schema. After implementing your new action, you need to regenerate the client:

```sh
make generate-client
```

### 6. Update Documentation

Finally, update the [action documentation](/actions.md) to include your new action.

## 🚀 Conclusion

By following these steps, you can successfully implement a new action within the Automated Actions system. Ensure to adhere to coding standards and write comprehensive tests to maintain the integrity of the system. Happy coding!

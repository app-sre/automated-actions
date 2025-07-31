# Unit Test Creation Request

Please create a test for this action: $ARGUMENTS

Test requirements:

- Use pytest framework
- Use pytest fixtures for setup
- Ensure test is isolated and does not depend on external state
- Use mock objects only where necessary and avoid over-mocking
- Validate both success and failure scenarios
- Use realistic inputs and expected outputs
- Follow the coding best practices outlined in the project documentation
- Ensure test is idempotent and can be run multiple times without side effects
- Document the test with clear descriptions of what it covers
- Test all major functionality
- Aim for high code coverage
- Always cover all involved packages and modules, e.g. `automated_actions_utils`
- Include dedicated integration tests for end-to-end workflows. See `packages/integration_tests/tests/` for examples.

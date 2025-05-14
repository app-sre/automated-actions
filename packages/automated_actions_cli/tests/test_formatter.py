from automated_actions_cli.formatter import JsonFormatter, YamlFormatter


def test_formatter_json() -> None:
    def check_output(output: str) -> None:
        assert output.replace("\n", "") == '{"key": "value"}'

    formatter = JsonFormatter(printer=check_output, indent=0)
    formatter({"key": "value"})


def test_formatter_json_str() -> None:
    def check_output(output: str) -> None:
        assert output == '"testtest"'

    formatter = JsonFormatter(printer=check_output, indent=0)
    formatter("testtest")


def test_formatter_yaml() -> None:
    def check_output(output: str) -> None:
        assert output == "---\nkey: value\n"

    formatter = YamlFormatter(printer=check_output, indent=0)
    formatter({"key": "value"})


def test_formatter_yaml_string() -> None:
    def check_output(output: str) -> None:
        assert output == "--- testtest\n...\n"

    formatter = YamlFormatter(printer=check_output, indent=0)
    formatter("testtest")

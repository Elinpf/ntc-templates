import os
from copy import deepcopy
from io import StringIO
from unittest.mock import patch

import development_script
import pytest
from ruamel.yaml.compat import StringIO


@pytest.fixture(scope="module")
def yaml_comments_file():
    with open("tests/mocks/load/yaml_comments.yml", encoding="utf-8") as fh:
        return development_script.YAML_OBJECT.load(fh)


@pytest.fixture
def copy_yaml_comments(yaml_comments_file):
    return deepcopy(yaml_comments_file)


@pytest.fixture
def teardown_normalize_file():
    filepaths = {}

    def _teardown_normalize_file(filepath):
        with open(filepath, encoding="utf-8") as fh:
            contents = fh.read()

        filepaths[filepath] = contents

    yield _teardown_normalize_file

    for filepath, contents in filepaths.items():
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(contents)


@pytest.fixture(scope="module")
def expected_file():
    expected_path = "tests/mocks/expected/parsed_sample.yml"
    with open(expected_path, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def expected_mac_file():
    expected_path = "tests/mocks/expected/show_mac.yml"
    with open(expected_path, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def teardown_delete_file():
    filepaths = []

    def _teardown_delete_file(filepath):
        filepaths.append(filepath)

    yield _teardown_delete_file

    for file in filepaths:
        os.remove(file)


def test_ensure_spacing_for_multiline_comment():
    remark = "comment 11\n#        comment 12\n#comment 13\n"
    remark_formatted = development_script.ensure_spacing_for_multiline_comment(remark)
    assert remark_formatted == "comment 11\n# comment 12\n# comment 13"


def test_ensure_space_after_octothorpe(copy_yaml_comments):
    comment = copy_yaml_comments.ca.items["b"][2]
    development_script.ensure_space_after_octothorpe(comment)
    assert comment.value == "# comment 2\n# comment 3\n"


def test_ensure_space_comments(copy_yaml_comments):
    comments = copy_yaml_comments.ca.items
    comment_values = comments.values()
    development_script.ensure_space_comments(comment_values)
    assert comments["a"][2].value == "# comment 1\n"
    assert comments["b"][2].value == "# comment 2\n# comment 3\n"
    assert comments["d"][3][0].value == "# comment 7\n"


def test_update_yaml_comments(copy_yaml_comments):
    development_script.update_yaml_comments(copy_yaml_comments)
    string_yaml = StringIO()
    development_script.YAML_OBJECT.dump(copy_yaml_comments, string_yaml)
    actual = string_yaml.getvalue()
    with open("tests/mocks/expected/yaml_comments.yml", encoding="utf-8") as fh:
        expected = fh.read()
    assert actual == expected


def test_ensure_yaml_standards(teardown_normalize_file, expected_file):
    load_file = "tests/mocks/load/parsed_sample.yml"
    teardown_normalize_file(load_file)
    with open(load_file, encoding="utf-8") as fh:
        load_yaml = development_script.YAML_OBJECT.load(fh)

    development_script.ensure_yaml_standards(load_yaml, load_file)
    with open(load_file, encoding="utf-8") as actual:
        assert actual.read() == expected_file


def test_upper_value():
    textfsm = """
Value Interface (MEth\d+\/\d+\/\d+)
Value Ip_Address (\S+)
Value Physical (\S+)
Value PROTOCOL (\S+)

Start
  ^${Interface}\s+${Ip_Address}\s+${Physical}\s+${PROTOCOL} -> Record
    """

    expected = """
Value INTERFACE (MEth\d+\/\d+\/\d+)
Value IP_ADDRESS (\S+)
Value PHYSICAL (\S+)
Value PROTOCOL (\S+)

Start
  ^${INTERFACE}\s+${IP_ADDRESS}\s+${PHYSICAL}\s+${PROTOCOL} -> Record
    """

    res = development_script.upper_values(textfsm)
    assert res == expected


def test_print_index_file_command():
    expected = 'hp_comware_display_ip_routing-table_statistics.textfsm, .*, hp_comware, dis[[play]] ip routi[[ng-table]] s[[tatistics]]'

    with patch('sys.stdout', new=StringIO()) as fake_out:
        development_script.print_index_file_command(
            'hp_comware', 'display ip routing-table statistics', 0, 'dis ip routi s'
        )
        assert fake_out.getvalue().replace('\n', '') == expected

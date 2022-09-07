import numbers
import os
import re
from argparse import ArgumentParser
from typing import Dict, Iterator, List, Tuple

from rich import print
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ
from textfsm import TextFSM
from tests.test_index_order import OS_CHOICES

YAML_OBJECT = YAML()
YAML_OBJECT.explicit_start = True
YAML_OBJECT.indent(sequence=4, offset=2)
YAML_OBJECT.block_style = True
RE_MULTILINE_REMARK = re.compile(r"(.*\n\s*#)(.*)")

VALUE_REG = r"^Value.*\s(?P<name>\S+)(?=\s+\()"


def ensure_spacing_for_multiline_comment(remark):
    """
    Finds all comments and ensures a single space after "#" symbol.

    Args:
        remark (str): The remark of a comment from a ``ruamel.yaml.token.CommentToken``.

    Returns:
        str: The ``remark`` formatted with a single space after comment start, "#"

    Example:
        >>> remark = "comment 11\n#        comment 12\n#comment 13\n"
        >>> remark_formatted = ensure_spacing_for_multiline_comment(remark)
        >>> # Formatting has normalized each comment to have a single space after the "#"
        >>> remark_formatted
        'comment 11\n# comment 12\n# comment 13'
        >>>
    """
    remarks = re.findall(RE_MULTILINE_REMARK, remark)
    # remarks that don't have a subsequent comment are not captured by regex
    if not remarks:
        remarks = (("", remark),)
    # Example remarks: [('comment \n#', '      comment2 '), ('\n  #', 'comment3 # 9')]
    remark_formatted = "".join([entry[0] + " " + entry[1].strip() for entry in remarks])
    return remark_formatted


def ensure_space_after_octothorpe(comment):
    """
    Ensures a single space is between the "#" and first letter of a comment.

    Args:
        comment (ruamel.yaml.token.CommentToken): The comment to update.

    Returns:
        None: The comment is updated in place.

    Example:
        >>> yml = ruamel.yaml.YAML()
        >>> with open("test.yml", encoding="utf-8") as fh:
        ...     print(fh.read())
        ...     fh.seek(0)
        ...     data = yml.load(fh)
        ...
        ---
        a: 5 # comment 1
        b: 6 #comment 2
        #comment 3
        c:
          - 7 #comment 4
        #comment 5
          - 8
        #comment 6
        d:
          #comment 7
          e: a #comment 8
          f:
            - 9
            #comment 9
            - 10
            - a:
                a: 8
                #comment 10
                b: 1
            - b: 1
            - 9
        #comment 11
        #        comment 12
        #comment 13

        >>> type(data)
        <class 'ruamel.yaml.comments.CommentedMap'>
        >>> comment = data.ca.items["b"][2]
        >>> comment
        CommentToken('#comment 2\n#comment 3\n', line: 2, col: 5)
        >>> ensure_space_after_octothorpe(comment)
        >>> # Both comments within the CommentToken object
        >>> # now have a space between the "#" and the first symbol
        >>> comment
        CommentToken('# comment 2\n# comment 3\n', line: 2, col: 5)
        >>>
    """
    if comment is not None:
        # Comments can start with whitespace,
        # so partition is used to preserve that in the final result
        space, octothorpe, remark = comment.value.partition("#")
        remark_formatted = ensure_spacing_for_multiline_comment(remark)
        comment.value = f"{space}# {remark_formatted.lstrip()}\n"


def ensure_space_comments(comments):
    """
    Ensures there is a space after the "#" in comments.

    Args:
        comments (iter): The comments from ruamel.yaml.YAML() object.

    Returns:
         None: Comments are update in place.

    Example:
        >>> yml = ruamel.yaml.YAML()
        >>> with open("test.yml", encoding="utf-8") as fh:
        ...     print(fh.read())
        ...     fh.seek(0)
        ...     data = yml.load(fh)
        ...
        ---
        a: 5 # comment 1
        b: 6 #comment 2
        #comment 3
        c:
          - 7 #comment 4
        #comment 5
          - 8
        #comment 6
        d:
          #comment 7
          e: a #comment 8
          f:
            - 9
            #comment 9
            - 10
            - a:
                a: 8
                #comment 10
                b: 1
            - b: 1
            - 9
        #comment 11
        #        comment 12
        #comment 13

        >>> type(data)
        <class 'ruamel.yaml.comments.CommentedMap'>
        >>> comments = data.ca.items.values()
        >>> comments
        dict_values([
            [None, None, CommentToken('# comment 1\n', line: 1, col: 5), None],
            [None, None, CommentToken('#comment 2\n#comment 3\n', line: 2, col: 5), None],
            [None, None, None, [CommentToken('#comment 7\n', line: 10, col: 2)]]
        ])
        >>> ensure_space_comments(comments)
        >>> # Every comment now has a space between the "#" and the first symbol
        >>> comments
        dict_values([
            [None, None, CommentToken('# comment 1\n', line: 1, col: 5), None],
            [None, None, CommentToken('# comment 2\n# comment 3\n', line: 2, col: 5), None],
            [None, None, None, [CommentToken('# comment 7\n', line: 10, col: 2)]]
        ])
        >>>
    """
    comment_objects = (comment for comment_list in comments for comment in comment_list)
    for comment in comment_objects:
        # Some comments are nested inside an additional list
        if not isinstance(comment, list):
            ensure_space_after_octothorpe(comment)
        else:
            for cmt in comment:
                ensure_space_after_octothorpe(cmt)


def update_yaml_comments(yaml_object):
    """
    Ensures comments have a space after the "#" on itself and its entries

    Args:
        yaml_object (ruamel.yaml.comments.CommentedMap | ruamel.yaml.comments.CommentedSeq): The list or dict object.

    Returns:
        None: Comments are updated in place.

    Example:
        >>> yml = ruamel.yaml.YAML()
        >>> with open("test.yml", encoding="utf-8") as fh:
        ...     print(fh.read())
        ...     fh.seek(0)
        ...     data = yml.load(fh)
        ...
        ---
        a: 5 # comment 1
        b: 6 #comment 2
        #comment 3
        c:
          - 7 #comment 4
        #comment 5
          - 8
        #comment 6
        d:
          #comment 7
          e: a #comment 8
          f:
            - 9
            #comment 9
            - 10
            - a:
                a: 8
                #comment 10
                b: 1
            - b: 1
            - 9
        #comment 11
        #        comment 12
        #comment 13

        >>> type(data)
        <class 'ruamel.yaml.comments.CommentedMap'>
        >>> update_yaml_comments(data)
        >>> with open("test.yml", "w", encoding="utf-8") as fh
        ...     yml.dump(data, fh)
        ...
        >>>
        # Notice that comments now have a space between the hash and first symbol.
        >>> with open("test.yml", encoding="utf-8") as fh:
        ...     print(fh.read())
        ...
        a: 5 # comment 1
        b: 6 # comment 2
        #comment 3
        c:
        - 7   # comment 4
        #comment 5
        - 8
        # comment 6
        d:
          # comment 7
          e: a # comment 8
          f:
          - 9
            # comment 9
          - 10
          - a:
              a: 8
                # comment 10
              b: 1
          - b: 1
          - 9
        # comment 11
        # comment 12
        # comment 13

        >>>
    """
    comments = yaml_object.ca.items.values()
    ensure_space_comments(comments)
    try:
        yaml_object_values = yaml_object.values()
    except AttributeError:
        yaml_object_values = yaml_object

    for entry in yaml_object_values:
        if isinstance(entry, dict) or isinstance(entry, list):
            update_yaml_comments(entry)


def ensure_yaml_standards(parsed_object, output_path):
    """
    Ensures YAML files adhere to yamllint config as defined in this project.

    Args:
        parsed_object (dict): The TextFSM/CliTable data converted to a list of dicts.
            The list of dicts must be the value of a dictionary key, ``parsed_sample``.
        output_path (str): The filepath to write the ``parsed_object`` to.

    Returns:
        None: File I/O is performed to write ``parsed_object`` to ``output_path``.
    """
    for entry in parsed_object["parsed_sample"]:
        # TextFSM conversion will allways be a list of dicts
        for key, value in entry.items():
            # TextFSM capture groups always return strings or lists
            # This also accounts for numbers incase the YAML was done by hand
            if isinstance(value, (str, numbers.Number)):
                entry[key] = DQ(value)
            else:
                entry[key] = [DQ(val) for val in value]
    try:
        update_yaml_comments(parsed_object)
    except AttributeError:
        pass

    with open(output_path, "w", encoding="utf-8") as parsed_file:
        YAML_OBJECT.dump(parsed_object, parsed_file)


def _textfsm_reslut_to_dict(header: list, reslut: list) -> List[Dict[str, str]]:
    """将 TextFSM 的结果与header结合转化为dict"""
    objs = []
    for row in reslut:
        temp_dict = {}
        for index, element in enumerate(row):
            temp_dict[header[index].lower()] = element
        objs.append(temp_dict)

    return objs


def get_test_files(vendor_os: str, command: str, index: int) -> Tuple[str, str]:
    """获取测试文件路径"""
    base_name = vendor_os + "_" + command.replace(" ", "_")

    raw_base_name = base_name + str(index) if index > 1 else base_name

    raw_file = os.path.join(
        "tests", vendor_os, command.replace(" ", "_"), raw_base_name + ".raw"
    )
    template_file = os.path.join("ntc_templates", "templates", base_name + ".textfsm")
    return (raw_file, template_file)


def get_test_files_iter(
    vendor_os: str, command: str, index: int
) -> Iterator[Tuple[str, str]]:
    test_raw_list = []
    template_file = ""
    if not args.index:
        raw_file, template_file = get_test_files(vendor_os, command, 1)
        raw_file_dir = os.path.dirname(raw_file)
        for file in os.listdir(raw_file_dir):
            if file.endswith(".raw"):
                test_raw_list.append(os.path.join(raw_file_dir, file))

    else:
        raw_file, template_file = get_test_files(vendor_os, command, index)
        test_raw_list.append(raw_file)

    for raw_file in test_raw_list:
        yield raw_file, template_file


def main(raw_file: str, template_file: str) -> List[Dict]:
    """for test"""

    template = TextFSM(open(template_file))
    stream = open(raw_file, "r").read()

    res = template.ParseText(stream)

    output = _textfsm_reslut_to_dict(template.header, res)
    print(output)
    return output


def generate_file(vendor_os: str, command: str, index: int):
    raw_file, template_file = get_test_files(vendor_os, command, index)
    if not os.path.exists(raw_file):
        # 创建raw文件夹
        if not os.path.exists(os.path.dirname(raw_file)):
            os.mkdir(os.path.dirname(raw_file))
        open(raw_file, "w").write("")
        print("generate raw file: {}".format(raw_file))

    if not os.path.exists(template_file):
        open(template_file, "w").write("")
        print("generate template file: {}".format(template_file))


def reg_blank_sub(text: str) -> str:
    """对文件进行空格替换"""

    final_text = []
    for line in text.splitlines():
        if not line.startswith("  ^"):
            final_text.append(line)
            continue

        line = line[2:]
        end = ""
        match_end = re.search(r"( -> .*)$", line)
        if match_end:
            end = match_end.group(1)
            line = line[: -len(end)]

        tmp = " ".join(line.split())
        tmp = tmp.replace(" ", "\s+")  # noqa: W605
        tmp = f"  {tmp}{end}"
        final_text.append(tmp)

    return "\n".join(final_text)


def upper_values(text: str) -> str:
    """将值转化为大写"""

    wait_for_upper_value = []
    final_text = []

    for line in text.splitlines():
        if line.startswith("Value"):
            match = re.search(VALUE_REG, line)
            if match:
                name = match.group("name")
                if name != name.upper():
                    upper_line = line.replace(name, name.upper())
                    final_text.append(upper_line)
                    wait_for_upper_value.append(name)
                    continue
                else:
                    final_text.append(line)
                    continue

        else:
            for name in wait_for_upper_value:
                line = re.sub("\${" + name + "}", "${" + name.upper() + "}", line)

            final_text.append(line)

    return "\n".join(final_text)


def print_index_file_command(vendor_os: str, command: str, index: int, short: str):
    textfsm_file = get_test_files(vendor_os, command, index)[1]

    res_cmd = []
    cmd_e = command.split()
    for index, short_cmd_e in enumerate(short.split()):
        last = cmd_e[index].replace(short_cmd_e, "")
        if last == "":
            res_cmd.append(short_cmd_e)
        else:
            res_cmd.append(f"{short_cmd_e}\[\[{last}]]")  # noqa: W605

    res_cmd = " ".join(res_cmd)
    print()
    print(f"{os.path.basename(textfsm_file)}, .*, {vendor_os}, {res_cmd}")
    print()


def get_vendor_command_from_file_name(file_name: str) -> Tuple[str, str]:
    """获取vendor_os和command"""
    file_name = file_name.replace(".testfsm", "")
    split_list = file_name.split("_")
    vendor_os = "_".join(split_list[:2])
    if vendor_os not in OS_CHOICES:
        raise ValueError(f"{vendor_os} is not a valid vendor_os")

    command = " ".join(split_list[2:])
    return vendor_os, command


def parse_args():
    parser = ArgumentParser(description="自动生成textfsm和所需raw文件, 方便对textfsm进行测试")
    parser.add_argument("-v", "--vendor", help="设备厂商", required=False)
    parser.add_argument("-c", "--command", help="设备命令", required=False)
    parser.add_argument("-f", "--file", help="设备命令文件", required=False)
    parser.add_argument("-g", "--generate", help="生成测试文件", action="store_true")
    parser.add_argument("-i", "--index", help="多raw文件的索引，从2开始", type=int, required=False)
    parser.add_argument("-b", "--blank", help="对textfsm文件进行空格替换", action="store_true")
    parser.add_argument("-t", "--test", help="对textfsm进行测试", action="store_true")
    parser.add_argument("-y", "--yml", help="生成yml文件", action="store_true")
    parser.add_argument("-s", "--short", help="通过短命令生成index文件需要的条目", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    index = args.index or 1

    if args.file:
        vendor_os, command = get_vendor_command_from_file_name(args.file)

    if args.vendor:
        vendor_os = args.vendor
    if args.command:
        command = args.command

    if args.generate:
        generate_file(vendor_os, command, index)
        exit()

    if args.blank:
        textfsm_file = get_test_files(vendor_os, command, index)[1]
        with open(textfsm_file) as f:
            text = f.read()

        text = reg_blank_sub(text)
        text = upper_values(text)

        with open(textfsm_file, "w") as f:
            f.write(text)
        exit()

    if args.yml:
        """生成yml文件"""
        index = args.index or 0
        count = 0
        for raw_file, template_file in get_test_files_iter(vendor_os, command, index):
            yml_file = raw_file.replace(".raw", ".yml")
            if os.path.exists(yml_file):
                os.remove(yml_file)
            ret = main(raw_file, template_file)
            ensure_yaml_standards({"parsed_sample": ret}, yml_file)
            print("generate yml file:", yml_file)
            print()
            count += 1

        print(f"generate yml {count} file done")
        exit()

    if args.short:
        short = input("input shortest cmd: ")
        print_index_file_command(vendor_os, command, index, short)
        exit()

    if args.test:
        index = args.index or 0
        for raw_file, template_file in get_test_files_iter(vendor_os, command, index):
            print("raw_file:", raw_file)
            main(raw_file, template_file)
            print()

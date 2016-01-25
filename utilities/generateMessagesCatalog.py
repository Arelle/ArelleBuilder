"""
Created on Aug 26, 2012

@author: Mark V Systems Limited
(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
"""

import ast
import io
import os
import time

import arelle


ARELLE_MESSAGES_XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="unqualified"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <xs:element name="messages">
    <xs:complexType>
      <xs:sequence>
        <xs:element maxOccurs="unbounded" name="message">
          <xs:complexType>
            <xs:simpleContent>
              <xs:extension base="xs:string">
                <xs:attribute name="code" use="required" type="xs:normalizedString"/>
                <xs:attribute name="level" use="required" type="xs:token"/>
                <xs:attribute name="module" type="xs:normalizedString"/>
                <xs:attribute name="line" type="xs:integer"/>
                <xs:attribute name="args" type="xs:NMTOKENS"/>
              </xs:extension>
            </xs:simpleContent>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
      <xs:attribute name="variablePrefix" type="xs:string"/>
      <xs:attribute name="variableSuffix" type="xs:string"/>
      <xs:attribute name="variablePrefixEscape" type="xs:string"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

ARELLE_MESSAGES_XML = """<?xml version="1.0" encoding="utf-8"?>
<messages
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="messagesCatalog.xsd"
    variablePrefix="%("
    variableSuffix=")s"
    variablePrefixEscape="" >
<!--
This file contains Arelle messages text.   Each message has a code
that corresponds to the message code in the log file, level (severity),
args (available through log file), and message replacement text.

(Messages with dynamically composed error codes or text content
(such as ValidateXbrlDTS.py line 158 or lxml parser messages)
are reported as "(dynamic)".)

-->

"""

DOC_DIRECTORY = os.sep.join([
    os.path.split(os.path.dirname(__file__))[0],
    "arelle", "doc"
])


def _log_function(item):
    """
    Handler function for log message types.

    :param item: ast object being inspected for certain properties
    :type item: :class:`~ast.AST`
    :return: Returns the descriptor and arg offset of the item.
    :rtype: tuple (str, int)
    """
    level_arg = item.args[0]
    if isinstance(level_arg, ast.Str):
        level = level_arg.s.lower()
    else:
        any_call_or_name_elements = any(
            isinstance(element, (ast.Call, ast.Name))
            for element in ast.walk(level_arg)
        )
        if any_call_or_name_elements:
            level = "(dynamic)"
        else:
            level = ', '.join(
                element.s.lower()
                for element in ast.walk(level_arg)
                if isinstance(element, ast.Str)
            )
    integer_arg_offset = 1
    return level, integer_arg_offset


FUNC_HANDLER = {
    "info": ("info", 0),
    "warning": ("warning", 0),
    "error": ("error", 0),
    "exception": ("exception", 0),
    "log": _log_function
}


def entityEncode(arg):
    """ Be sure it's a string, vs int, etc, and encode &, <, ". """
    return str(arg).replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')


def _is_callable(item):
    """
    Helper function to determine if the item from the ast.walk() function is
    callable and in the list of handled types.

    :param item: ast object being checked to see if it is an executable object.
    :type item: :class:`~ast.AST`
    :return: True if the object is callable and has either an attr or id, and
        that value is in the FUNC_HANDLER map.
    :rtype: bool
    """
    valid_type_list = FUNC_HANDLER.keys()
    if not isinstance(item, ast.Call):
        return False
    function = getattr(item.func, "attr", '') or getattr(item.func, "id", '')
    if function in valid_type_list:
        return True
    else:
        return False


def _build_id_messages(python_package, package_root):
    """
    Helper function to build the messages for a given python modules out of a
    python arelle sub-package.

    :param python_package: Sub-package of Arelle to build messages from.
    :type python_package: iterable
    :param package_root: Base path of the root of the package being parsed.
    :type package_root: str
    :return:
    :rtype: list
    """
    id_messages = []
    file_count = 0
    for python_module in python_package:
        file_count += 1
        full_filename_path = os.path.join(package_root, python_module)
        refFilename = (
            full_filename_path[len(package_root) + 1:].replace("\\", "/")
        )
        with open(full_filename_path, encoding="utf-8") as module_file:
            tree = ast.parse(module_file.read(), filename=python_module)
            callables = filter(_is_callable, ast.walk(tree))
            for item in callables:
                try:
                    # imported function could be by id instead of attr
                    handler = FUNC_HANDLER.get(
                            item.func.attr, lambda x:  ("", 0)
                    )
                    if isinstance(handler, tuple):
                        level, args_offset = handler
                    else:
                        level, args_offset = handler(item)

                    msgCodeArg = item.args[0 + args_offset]  # str or tuple
                    if isinstance(msgCodeArg,ast.Str):
                        msgCodes = (msgCodeArg.s,)
                    else:
                        if any(isinstance(element, (ast.Call, ast.Name))
                               for element in ast.walk(msgCodeArg)):
                            msgCodes = ("(dynamic)",)
                        else:
                            msgCodes = [
                                element.s for element in ast.walk(msgCodeArg)
                                if isinstance(element, ast.Str)
                            ]
                    msgArg = item.args[1 + args_offset]
                    if isinstance(msgArg, ast.Str):
                        msg = msgArg.s
                    elif ((isinstance(msgArg, ast.Call) and
                           getattr(msgArg.func, "id", '') == '_')):
                        msg = msgArg.args[0].s
                    elif ((any(isinstance(element, (ast.Call,ast.Name))
                           for element in ast.walk(msgArg)))):
                        msg = "(dynamic)"
                    else:
                        continue # not sure what to report
                    keywords = []
                    for keyword in item.keywords:
                        if keyword.arg == 'modelObject':
                            pass
                        elif keyword.arg == 'messageCodes':
                            msgCodeArg = keyword.value
                            if ((any(isinstance(element, (ast.Call, ast.Name))
                                 for element in ast.walk(msgCodeArg)))):
                                pass  # dynamic
                            else:
                                msgCodes = [
                                    element.s
                                    for element in ast.walk(msgCodeArg)
                                    if isinstance(element, ast.Str)
                                ]
                        else:
                            keywords.append(keyword.arg)
                    for msgCode in msgCodes:
                        id_messages.append(
                            {
                                'message_code': msgCode,
                                'message': entityEncode(msg),
                                'level': level,
                                'keyword_arguments': entityEncode(
                                    " ".join(keywords)
                                ),
                                'reference_filename': refFilename,
                                'line_number': item.lineno
                            }
                        )
                except (AttributeError, IndexError):
                    pass
    return id_messages, file_count


def _build_message_elements(id_messages):
    """
    Helper function to build the messages into a list XML elements in the form
    of string literals.

    :param id_messages: The list of message dictionaries to go through to
        assemble the XML from.
    :type id_messages: iterable
    :return: Returns the list of string'ified XML entries to be written to
        the messagesCatalog.xml file.
    :rtype: list [str]
    """
    lines = []
    for id_message in id_messages:
        try:
            lines.append(
                '<message code="{message_code}"\n'
                '         level="{level}"\n'
                '         module="{reference_filename}" line="{line_number}"\n'
                '         args="{keyword_arguments}">\n'
                '{message}\n'
                '</message>'
                .format(**id_message)
            )
        except Exception as ex:
            print(ex)
    return lines


def _write_message_files(lines):
    """
    Helper function to write the messagesCatalog.xml and messagesCatalog.xsd
    as part of the build process.

    :param lines: XML entries to be written into the xml file.
    :type lines: list [str]
    :return: No direct return, but writes two files to disk.
    :rtype: None
    """
    os.makedirs(os.path.join(DOC_DIRECTORY), exist_ok=True)
    messages_file_name = os.path.join(DOC_DIRECTORY, "messagesCatalog.xml")
    with io.open(messages_file_name, 'wt', encoding='utf-8') as message_file:
        message_file.write(ARELLE_MESSAGES_XML)
        message_file.write("\n\n".join(sorted(lines)))
        message_file.write("\n\n</messages>")

    xsd_file_name = os.path.join(DOC_DIRECTORY, "messagesCatalog.xsd")
    with io.open(xsd_file_name, 'wt', encoding='utf-8') as message_schema:
        message_schema.write(ARELLE_MESSAGES_XSD)


def _arelle_location_list():
    """
    Yield function to specify the locations to traverse when building messages.

    :return: Yields a list of path locations of packages to walk using the ast
        library's :func:`~ast.walk` function.
    :rtype: iterable
    """
    arelle_src_path = os.path.dirname(arelle.__file__)
    arelle_locations = [
        arelle_src_path,
        os.path.join(arelle_src_path, "plugin"),
        os.path.join(arelle_src_path, "plugin", "xbrlDB")
    ]
    for location in arelle_locations:
        yield location


if __name__ == "__main__":
    startedAt = time.time()
    id_messages = []
    num_arelle_src_files = 0

    for arelle_src_dir in _arelle_location_list():
        # TODO: It might be better to pull this filtering all the way up into the location list helper function.
        python_modules = [
            module_filename if module_filename.endswith(".py")
            else None
            for module_filename in os.listdir(arelle_src_dir)
        ]
        python_modules = filter(None, python_modules)
        new_id_messages, file_count = _build_id_messages(
                python_modules, arelle_src_dir
        )
        id_messages.extend(new_id_messages)
        num_arelle_src_files += file_count

    # Convert the id_messages into xml lines to be written.
    lines = _build_message_elements(id_messages)
    # Write the XML Lines into a file, as well as creating the XSD file.
    _write_message_files(lines)

    print(
        "Arelle messages catalog {0:.2f} secs, "
        "{1} formula files, {2} messages".format(
            time.time() - startedAt,
            num_arelle_src_files,
            len(id_messages)
        )
    )

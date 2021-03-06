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
import pkutils



PLUGINS_FILE = "../requirements_plugins.txt"
NON_LIBRARY_PLUGINS = "../non_library_plugins"
DOC_DIRECTORY = os.sep.join([
    os.path.split(os.path.dirname(__file__))[0],
    "arelle", "doc"
])
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
    "info": lambda x: ("info", 0),
    "warning": lambda x: ("warning", 0),
    "error": lambda x: ("error", 0),
    "exception": lambda x: ("exception", 0),
    "log": _log_function
}


def entity_encode(arg):
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


def _find_modules_and_directories(top_level_directory):
    """
    Recursive helper function to find all python files included in top level
    package. This will recurse down the directory paths of any package to find
    all modules and subpackages in order to create an exhaustive list of all
    python files within a given package.

    :param top_level_directory: Path to the top level of a python package.
    :type top_level_directory: str
    :return: Returns a list of paths to all python files within that package.
    :rtype: list [str]
    """
    modules = []
    directories = []

    for item in os.listdir(top_level_directory):
        if item.endswith(".py"):
            modules.append(os.path.join(top_level_directory, item))
        elif os.path.isdir(os.path.join(top_level_directory, item)):
            directories.append(os.path.join(top_level_directory, item))

    for directory in directories:
        modules.extend(_find_modules_and_directories(directory))

    return modules


def generate_locations():
    """
    Utility function to generate the file locations for Arelle's core, pip
    installed plugins, and non-installable plugins which have been copied to
    the non_library_plugins folder. These locations represent a list of the
    locations for the message generation to begin ast walks in order to find
    and generate messages for the catalog.

    :return: Returns a list of strings representing module locations
    :rtype: list [str]
    """
    arelle_modules = []

    arelle_src_path = os.path.dirname(arelle.__file__)
    arelle_component_locations = [
        arelle_src_path,
        os.path.join(os.path.dirname(__file__), NON_LIBRARY_PLUGINS)
    ]

    arelle_component_locations.extend(_find_plugin_locations())

    for location in arelle_component_locations:
        arelle_modules.extend(_find_modules_and_directories(location))

    return arelle_modules


def _find_plugin_locations():
    """
    Helper utility to introspect the plugin file then find a list of all the
    source directory of each plugin to be passed to the list of roots to use
    during the AST.walk for message inspection

    :return: Return is a list of strings representing the paths to the install
        locations of each plugin in the plugin requirements file.
    :rtype: list [str]
    """
    plugin_locations = []
    plugin_list = list(pkutils.parse_requirements(PLUGINS_FILE))
    for plugin_requirement in plugin_list:
        # Checking for a pinned requirement in the file to remove the extra
        # information to prevent issues with the __import__ statement.
        pin_separation_index = plugin_requirement.find("=")
        if pin_separation_index > 0:
            plugin_name_only = plugin_requirement[:pin_separation_index]
        else:
            plugin_name_only = plugin_requirement
        plugin = __import__(plugin_name_only, globals(), locals(), [], 0)
        plugin_location = os.path.dirname(plugin.__file__)
        del plugin
        plugin_locations.append(plugin_location)
    return plugin_locations


def _build_id_messages(python_module):
    """
    Helper function to build the messages for a given python modules out of a
    python arelle sub-package.

    :param python_module: Module location to be walked and introspected for
        messages to build.
    :type python_module: str
    :return: A listing, in dictionary format, of all the messages of the
        specified module which can then be used to generate the XML list.
    :rtype: list [dict]
    """
    id_messages = []
    ref_module_name = os.path.basename(python_module)
    with open(python_module, encoding="utf-8") as module_file:
        tree = ast.parse(module_file.read(), filename=python_module)
        callables = filter(_is_callable, ast.walk(tree))
        for item in callables:
            # imported function could be by id instead of attr
            try:
                handler = FUNC_HANDLER.get(
                    item.func.attr, lambda x: ("", 0)
                )
                level, args_offset = handler(item)
            except AttributeError:
                # func has no attribute 'attr'
                continue
            try:
                msgCodeArg = item.args[0 + args_offset]  # str or tuple
                msg_arg = item.args[1 + args_offset]
            except IndexError:
                # can't proceed when the args are not present.
                continue
            msg = _get_validation_message(msg_arg)
            if not msg:
                continue  # not sure what to report
            msgCodes = _get_message_codes(msgCodeArg)
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
                        'message': entity_encode(msg),
                        'level': level,
                        'keyword_arguments': entity_encode(
                            " ".join(keywords)
                        ),
                        'reference_filename': ref_module_name,
                        'line_number': item.lineno
                    }
                )
    return id_messages


def _get_message_codes(msg_code_arg):
    """
    Get the correct message codes based on instance type of msgCodeArg

    :param msg_code_arg: the current arg to pull msgCodes from
    :type msg_code_arg: :class:`~ast.AST`
    :return: the correct message code to use
    :rtype: tuple
    """
    msg_codes = None
    if isinstance(msg_code_arg, ast.Str):
        msg_codes = (msg_code_arg.s,)
    else:
        if any(isinstance(element, (ast.Call, ast.Name))
               for element in ast.walk(msg_code_arg)):
            msg_codes = ('(dynamic)',)
        else:
            msg_codes = tuple([
                element.s for element in ast.walk(msg_code_arg)
                if isinstance(element, ast.Str)
            ])
    return msg_codes


def _get_validation_message(msg_arg):
    """
    Helper function to get the validation message from the message arg.

    :param msg_arg: ast object being checked to see if it is an
         executable object.
    :type msg_arg: :class:`~ast.AST`
    :return: msg_arg's string value, the string value of its first argument,
         (dynamic), or None
    :rtype: str
    """
    if isinstance(msg_arg, ast.Str):
        return msg_arg.s
    elif _is_translatable(msg_arg):
        return msg_arg.args[0].s
    elif ((any(isinstance(element, (ast.Call, ast.Name))
           for element in ast.walk(msg_arg)))):
        return "(dynamic)"
    return None


def _is_translatable(msg_arg):
    """
    Helper function to encapusalte the check for whether the message 
    has a translate (_) call.

    :param msg_arg: ast object being checked to see if it is an
         executable object named '_'.
    :type msg_arg: :class:`~ast.AST`
    :return: True if msg_arg is an `ast.Call`, named '_'.  False otherwise.
    :rtype: bool
    """
    return (isinstance(msg_arg, ast.Call) and 
        getattr(msg_arg.func, "id", '') == '_')


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
    arelle_files = generate_locations()

    for module in arelle_files:
        id_messages.extend(_build_id_messages(module))


    # Convert the id_messages into xml lines to be written.
    lines = _build_message_elements(id_messages)
    # Write the XML Lines into a file, as well as creating the XSD file.
    _write_message_files(lines)

    print(
        "Arelle messages catalog {0:.2f} secs, "
        "{1} formula files, {2} messages".format(
            time.time() - startedAt,
            len(arelle_files),
            len(id_messages)
        )
    )

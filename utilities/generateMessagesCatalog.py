"""
Created on Aug 26, 2012

@author: Mark V Systems Limited
(c) Copyright 2012 Mark V Systems Limited, All rights reserved.
"""

import ast
import io
import os
import time


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
    return str(arg).replace("&","&amp;").replace("<","&lt;").replace('"','&quot;')


def _is_callable(item):
    """

    :param item:
    :type item:
    :return:
    :rtype: bool
    """
    valid_type_list = ("info", "warning", "log", "error", "exception")
    if not isinstance(item, ast.Call):
        return False
    function = getattr(item.func, "attr", '') or getattr(item.func, "id", '')
    if function in valid_type_list:
        return True
    else:
        return False


if __name__ == "__main__":
    startedAt = time.time()

    idMsg = []
    num_arelle_src_files = 0
    arelle_src_path = os.sep.join([
        (os.path.dirname(__file__) or os.curdir), "arelle"
    ])
    arelle_locations = [
        arelle_src_path,
        os.sep.join([arelle_src_path, "plugin"]),
        os.sep.join([arelle_src_path, "plugin", "xbrlDB"])
    ]
    for arelle_src_dir in arelle_locations:
        python_modules = [
            module_filename if module_filename.endswith(".py")
            else None
            for module_filename in os.listdir(arelle_src_dir)
        ]
        python_modules = filter(None, python_modules)
        for module_filename in python_modules:
            num_arelle_src_files += 1
            full_filename_path = os.sep.join([arelle_src_dir, module_filename])
            refFilename = full_filename_path[len(arelle_src_path) + 1:].replace("\\", "/")
            with open(full_filename_path, encoding="utf-8") as module_file:
                tree = ast.parse(module_file.read(), filename=module_filename)
                for item in ast.walk(tree):
                    try:
                        # imported function could be by id instead of attr
                        if _is_callable(item):
                            handler = FUNC_HANDLER.get(
                                    item.func.attr, lambda x:  ("", 0)
                            )
                            if isinstance(tuple, handler):
                                level, iArgOffset = handler
                            else:
                                level, iArgOffset = handler(item)

                            msgCodeArg = item.args[0 + iArgOffset]  # str or tuple
                            if isinstance(msgCodeArg,ast.Str):
                                msgCodes = (msgCodeArg.s,)
                            else:
                                if any(isinstance(elt, (ast.Call, ast.Name))
                                       for elt in ast.walk(msgCodeArg)):
                                    msgCodes = ("(dynamic)",)
                                else:
                                    msgCodes = [elt.s
                                                for elt in ast.walk(msgCodeArg)
                                                if isinstance(elt, ast.Str)]
                            msgArg = item.args[1 + iArgOffset]
                            if isinstance(msgArg, ast.Str):
                                msg = msgArg.s
                            elif isinstance(msgArg, ast.Call) and getattr(msgArg.func, "id", '') == '_':
                                msg = msgArg.args[0].s
                            elif any(isinstance(elt, (ast.Call,ast.Name))
                                     for elt in ast.walk(msgArg)):
                                msg = "(dynamic)"
                            else:
                                continue # not sure what to report
                            keywords = []
                            for keyword in item.keywords:
                                if keyword.arg == 'modelObject':
                                    pass
                                elif keyword.arg == 'messageCodes':
                                    msgCodeArg = keyword.value
                                    if any(isinstance(elt, (ast.Call, ast.Name))
                                           for elt in ast.walk(msgCodeArg)):
                                        pass # dynamic
                                    else:
                                        msgCodes = [
                                            elt.s
                                            for elt in ast.walk(msgCodeArg)
                                            if isinstance(elt, ast.Str)
                                        ]
                                else:
                                    keywords.append(keyword.arg)
                            for msgCode in msgCodes:
                                idMsg.append((msgCode, msg, level, keywords, refFilename, item.lineno))
                    except (AttributeError, IndexError):
                        pass

    lines = []
    for id,msg,level,args,module,line in idMsg:
        try:
            lines.append(
                "<message code=\"{0}\"\n"
                "         level=\"{3}\"\n"
                "         module=\"{4}\" line=\"{5}\"\n"
                "         args=\"{2}\">\n"
                "{1}\n"
                "</message>"
                .format(
                    id,
                    entityEncode(msg),
                    entityEncode(" ".join(args)),
                    level,
                    module,
                    line
                )
            )
        except Exception as ex:
            print(ex)

    os.makedirs(arelle_src_path + os.sep + "doc", exist_ok=True)
    with io.open(arelle_src_path + os.sep + "doc" + os.sep + "messagesCatalog.xml", 'wt', encoding='utf-8') as module_file:
        module_file.write(ARELLE_MESSAGES_XML)
        module_file.write("\n\n".join(sorted(lines)))
        module_file.write("\n\n</messages>")
        
    with io.open(os.sep.join([arelle_src_path, "doc", "messagesCatalog.xsd"]), 'wt', encoding='utf-8') as module_file:
        module_file.write(ARELLE_MESSAGES_XSD)
    
    print("Arelle messages catalog {0:.2f} secs, {1} formula files, {2} messages".format( time.time() - startedAt, num_arelle_src_files, len(idMsg)))
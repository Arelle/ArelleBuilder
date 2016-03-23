"""
Test file for utilities/generate_messages_catalog.py
"""
from unittest import mock
import unittest
import ast

from utilities import generate_messages_catalog


class TestUtilties(unittest.TestCase):

    @mock.patch(
        'utilities.generate_messages_catalog.os.path.dirname', autospec=True
    )
    @mock.patch(
        'utilities.generate_messages_catalog._find_plugin_locations',
        autospec=True
    )
    @mock.patch(
        'utilities.generate_messages_catalog._find_modules_and_directories',
        autospec=True
    )
    def test_generate_locations(self, find_modules, find_plugins, dirname):
        """Checks to make sure the correct calls are made by location gen"""
        dirname.side_effect = ['arelle', 'root']
        find_plugins.return_value = ['plugin']
        _ = generate_messages_catalog.generate_locations()
        call_list = [
            mock.call('arelle'),
            mock.call('root/' + generate_messages_catalog.NON_LIBRARY_PLUGINS),
            mock.call('plugin')
        ]
        find_modules.assert_has_calls(call_list, any_order=True)
        self.assertEqual(
            len(call_list), find_modules.call_count,
            "Incorrect number of calls to _find_modules_and_directories"
        )

    def test_get_validation_message_str(self):
        """Checks that _get_validation_message works when msgArg is an ast.Str"""
        msgArg = mock.Mock(spec=ast.Str)
        msgArg.s = "page"
        result = generate_messages_catalog._get_validation_message(msgArg)
        self.assertEqual("page", result)

    def test_get_validation_message_call(self):
        """Checks that _get_validation_message works when msgArg is an ast.Call"""
        msgArg = mock.Mock(spec=ast.Call)
        func = mock.Mock()
        func.id = "_"
        msgArg.func = func
        mock_arg = mock.Mock()
        mock_arg.s = "trey"
        msgArg.args = [mock_arg]
        result = generate_messages_catalog._get_validation_message(msgArg)
        self.assertEqual("trey", result)

    @mock.patch(
        'ast.walk',
        return_value=[mock.Mock(spec=ast.Call)]
    )
    def test_get_validation_message_walk_call(self, _):
        """Checks that _get_validation_message works when ast.walk is used, returning a Call"""
        result = generate_messages_catalog._get_validation_message(None)
        self.assertEqual(result, '(dynamic)')

    @mock.patch(
        'ast.walk',
        return_value=[mock.Mock(spec=ast.Name)]
    )
    def test_get_validation_message_walk_name(self, _):
        """Checks that _get_validation_message works when ast.walk is used, returning a Name"""
        result = generate_messages_catalog._get_validation_message(None)
        self.assertEqual(result, '(dynamic)')

    @mock.patch(
        'ast.walk',
        return_value=[mock.Mock()]
    )
    def test_get_validation_message_returns_None(self, _):
        """Checks that _get_validation_message returns None when all else fails."""
        result = generate_messages_catalog._get_validation_message(None)
        self.assertEqual(result, None)

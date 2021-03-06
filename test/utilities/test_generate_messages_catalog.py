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
        """Checks that _get_validation_message works when msg_arg is an ast.Str"""
        msg_arg = mock.Mock(spec=ast.Str)
        msg_arg.s = "page"
        result = generate_messages_catalog._get_validation_message(msg_arg)
        self.assertEqual("page", result)

    def test_get_validation_message_call(self):
        """Checks that _get_validation_message works when msg_arg is an ast.Call"""
        msg_arg = mock.Mock(spec=ast.Call)
        func = mock.Mock()
        func.id = "_"
        msg_arg.func = func
        mock_arg = mock.Mock()
        mock_arg.s = "trey"
        msg_arg.args = [mock_arg]
        result = generate_messages_catalog._get_validation_message(msg_arg)
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

    def test_is_translatable_good(self):
        """Checks that _is_translatable returns the proper value for a translate call"""
        msg_arg = mock.Mock(spec=ast.Call)
        func = mock.Mock()
        func.id = "_"
        msg_arg.func = func
        mock_arg = mock.Mock()
        msg_arg.args = [mock_arg]
        self.assertTrue(generate_messages_catalog._is_translatable(msg_arg))

    def test_is_translatable_bad(self):
        """Checks that _is_translatable returns the proper value for a translate call"""
        msg_arg = mock.Mock(spec=ast.Call)
        func = mock.Mock()
        func.id = "page"
        msg_arg.func = func
        mock_arg = mock.Mock()
        msg_arg.args = [mock_arg]
        self.assertFalse(generate_messages_catalog._is_translatable(msg_arg))

    def test_is_translatable_bad_noncall(self):
        """Checks that _is_translatable returns the proper value for a translate call"""
        msg_arg = mock.Mock(spec=ast.Name)
        func = mock.Mock()
        func.id = "_"
        msg_arg.func = func
        mock_arg = mock.Mock()
        msg_arg.args = [mock_arg]
        self.assertFalse(generate_messages_catalog._is_translatable(msg_arg))

    @mock.patch('ast.walk')
    def test_get_message_codes_good(self, mock_walk):
        """Checks for proper returns for the three accepted input types"""
        my_msg_arg = mock.Mock(spec=ast.Str, s='foo')
        codes = generate_messages_catalog._get_message_codes(my_msg_arg)
        self.assertEqual(codes, ('foo',))

        my_msg_arg = None
        mock_walk.return_value = [
            mock.Mock(spec=ast.Str, s='foo'),
            mock.Mock(spec=ast.Call),
            mock.Mock(spec=ast.Name)
        ]
        codes = generate_messages_catalog._get_message_codes(my_msg_arg)
        self.assertEqual(codes, ('(dynamic)',))

        mock_walk.return_value = [
            mock.Mock(spec=ast.Str, s='foo'), mock.Mock(spec=ast.Str, s='bar')
        ]
        codes = generate_messages_catalog._get_message_codes(my_msg_arg)
        self.assertEqual(codes, ('foo', 'bar'))

    @mock.patch('ast.walk')
    def test_get_message_codes_bad(self, mock_walk):
        """Checks for proper returns of nonsupported input"""
        my_msg_arg = mock.Mock(spec=ast.Call)
        mock_walk.return_value = [
            mock.Mock(spec=ast.Num), mock.Mock(spec=ast.Subscript)
        ]
        codes = generate_messages_catalog._get_message_codes(my_msg_arg)
        self.assertEqual(codes, ())

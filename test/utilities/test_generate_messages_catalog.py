"""
Test file for utilities/generate_messages_catalog.py
"""
from unittest import mock
import unittest

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

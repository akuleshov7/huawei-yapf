# -*- coding: utf-8
"""
Function: test FORCE_LONG_LINES_WRAPPING configuration paramenter
Copyright Information: Huawei Technologies Co., Ltd. All Rights Reserved © 2010-2019
Change History: 2019-12-02 Created
"""

import textwrap

from yapf.yapflib import style, reformatter
from yapf.yapflib.style import StyleConfigError
from yapftests import yapf_test_helper


class RunMainTest(yapf_test_helper.YAPFTest):
    def __setup(self, name):
        style.SetGlobalStyle(
            style.CreateStyleFromConfig(
                f'{{based_on_style: huawei, '
                f'check_func_naming_style: {name}}}'))

    def test_pascal_case(self):
        self.__setup('PascalCase')
        self.assertEqual(style.Get('CHECK_FUNC_NAMING_STYLE'), 'PASCALCASE')

    def test_camel_case(self):
        self.__setup('camelCase')
        self.assertEqual(style.Get('CHECK_FUNC_NAMING_STYLE'), 'CAMELCASE')

    def test_snake_case(self):
        self.__setup('snake_case')
        self.assertEqual(style.Get('CHECK_FUNC_NAMING_STYLE'), 'SNAKECASE')

    def test_unknown_name(self):
        with self.assertRaises(StyleConfigError):
            self.__setup('unknown_name')

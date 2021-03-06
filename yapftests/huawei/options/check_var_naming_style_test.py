# -*- coding: utf-8
"""
Function: test FORCE_LONG_LINES_WRAPPING configuration paramenter
Copyright Information: Huawei Technologies Co., Ltd. All Rights Reserved © 2010-2019
Change History: 2019-12-02 Created
"""

import textwrap

from yapf.yapflib import style
from yapf.yapflib.style import StyleConfigError
from yapf.yapflib.yapf_api import FormatCode
import yapf.yapflib.warnings.warnings_utils as warns

from yapftests.huawei.options import testbase


class RunMainTest(testbase.WarnTestBase):
    def __setup(self, name):
        style.SetGlobalStyle(
            style.CreateStyleFromConfig(
                f'{{based_on_style: pep8, '
                f'check_var_naming_style: {name}}}'))

    def test_pascal_case(self):
        self.__setup('PascalCase')
        self.assertEqual(style.Get('CHECK_VAR_NAMING_STYLE'), 'PASCALCASE')

    def test_camel_case(self):
        self.__setup('camelCase')
        self.assertEqual(style.Get('CHECK_VAR_NAMING_STYLE'), 'CAMELCASE')

    def test_snake_case(self):
        self.__setup('snake_case')
        self.assertEqual(style.Get('CHECK_VAR_NAMING_STYLE'), 'SNAKECASE')

    def test_unknown_name(self):
        with self.assertRaises(StyleConfigError):
            self.__setup('unknown_name')

    def test_var_naming(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            CONSTANT_VAR = 0
            PascalCaseVar = 1
            camelCaseVar = 2
            snake_case_var = 3
            __SpecialVar__ = 4
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'PascalCaseVar')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'camelCaseVar')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_local_vars(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn():
                CONSTANT_VAR = 0
                PascalCaseVar = 1
                camelCaseVar = 2
                snake_case_var = 4
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'PascalCaseVar')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'camelCaseVar')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_func_args(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn(first_arg, secondArg, ThirdArg):
                pass
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'secondArg')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'ThirdArg')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_func_capital_argname(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn(ARG):
                pass
        """)
        FormatCode(input_source)

        # `ARG` is treated here as if it was a constant definition
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 0)

    def test_class_fields(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            class Class:
                PascalCaseStatic = 0
                snake_case_static = 1

                def __init__(self):
                    self.camelCase = 2
                    self.snake_case = 3
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'PascalCaseStatic')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'camelCase')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_placeholder(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            _, a = fn()
        """)
        FormatCode(input_source)

        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 0)

    def test_bare_star(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn(*, var): pass
        """)
        FormatCode(input_source)

        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 0)

    def test_variable_params(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn(*Args, **Kwargs): pass
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Args')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Kwargs')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_inner_comments(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            def fn(arg1,
                arg2, # comment
                ):
                pass
        """)
        FormatCode(input_source)

        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 0)

    def test_func_calls(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            Func(Arg) = 1
        """)
        FormatCode(input_source)

        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 0)

    def test_chains(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            Object.Value1 = 1
            self.Value2 = 1
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Value2')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 1)

    def test_true_power(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            Var1 = 2**2**2
            Var2 = Var1**Var1
        """)
        FormatCode(input_source)

        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Var1')
        self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Var2')
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 2)

    def test_assignmets(self):
        self.__setup('snake_case')

        input_source = textwrap.dedent("""\
            Var01 = 1
            Var02 += 1
            Var03 += 1
            Var04 *= 1
            Var05 /= 1
            Var06 //= 1
            Var07 %= 1
            Var08 **= 1
            Var09 >>= 1
            Var10 <<= 1
            Var11 &= True
            Var12 |= True
            Var13 ^= True
            Var14 @= True
        """)
        FormatCode(input_source)

        for i in range(1, 15):
            self.assertWarnMessage(warns.Warnings.VAR_NAMING_STYLE, 'Var%02d' % i)
        self.assertWarnCount(warns.Warnings.VAR_NAMING_STYLE, 14)

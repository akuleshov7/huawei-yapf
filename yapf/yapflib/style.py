# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python formatting style settings."""

import os
import re
import textwrap

from yapf.yapflib import errors
from yapf.yapflib import py3compat


class StyleConfigError(errors.YapfError):
  """Raised when there's a problem reading the style configuration."""
  pass


def Get(setting_name):
  """Get a style setting."""
  return _style[setting_name]


def Set(setting_name, value):
  """Set a style setting."""
  _style[setting_name] = value


def Help():
  """Return dict mapping style names to help strings."""
  return _STYLE_HELP


def SetGlobalStyle(style):
  """Set a style dict."""
  global _style
  global _GLOBAL_STYLE_FACTORY
  factory = _GetStyleFactory(style)
  if factory:
    _GLOBAL_STYLE_FACTORY = factory
  _style = style


_STYLE_HELP = dict(
    AGGRESSIVELY_MOVE_ALL_IMPORTS_TO_HEAD=textwrap.dedent("""\
      If enabled (True) will find all imports used in code and move it right to
      the beginning of the file. It would be added after all
      comments/doc strings from the beginning of the file.
      Note! It won't move indented imports from code blocks (functions/classes).
    """),
    AGGRESSIVELY_MOVE_COPYRIGHT_TO_HEAD=textwrap.dedent("""\
    If enabled (True) will find a doc string with copyright information
     (Copyright Information:) and move it before imports (after other comments)
     in the beginning of the file
    """),
    ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT=textwrap.dedent("""\
      Align closing bracket with visual indentation."""),
    ALLOW_MULTILINE_LAMBDAS=textwrap.dedent("""\
      Allow lambdas to be formatted on more than one line."""),
    ALLOW_MULTILINE_DICTIONARY_KEYS=textwrap.dedent("""\
      Allow dictionary keys to exist on multiple lines. For example:

        x = {
            ('this is the first element of a tuple',
             'this is the second element of a tuple'):
                 value,
        }"""),
    ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS=textwrap.dedent("""\
      Allow splitting before a default / named assignment in an argument list.
      """),
    ALLOW_SPLIT_BEFORE_DICT_VALUE=textwrap.dedent("""\
      Allow splits before the dictionary value."""),
    ARITHMETIC_PRECEDENCE_INDICATION=textwrap.dedent("""\
      Let spacing indicate operator precedence. For example:

        a = 1 * 2 + 3 / 4
        b = 1 / 2 - 3 * 4
        c = (1 + 2) * (3 - 4)
        d = (1 - 2) / (3 + 4)
        e = 1 * 2 - 3
        f = 1 + 2 + 3 + 4

    will be formatted as follows to indicate precedence:

        a = 1*2 + 3/4
        b = 1/2 - 3*4
        c = (1+2) * (3-4)
        d = (1-2) / (3+4)
        e = 1*2 - 3
        f = 1 + 2 + 3 + 4

      """),
    BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=textwrap.dedent("""\
      Insert a blank line before a 'def' or 'class' immediately nested
      within another 'def' or 'class'. For example:

        class Foo:
                           # <------ this blank line
          def method():
            ..."""),
    BLANK_LINE_BEFORE_CLASS_DOCSTRING=textwrap.dedent("""\
      Insert a blank line before a class-level docstring."""),
    BLANK_LINE_BEFORE_MODULE_DOCSTRING=textwrap.dedent("""\
      Insert a blank line before a module docstring."""),
    BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION=textwrap.dedent("""\
      Number of blank lines surrounding top-level function and class
      definitions."""),
    BLANK_LINES_AFTER_INDENTED_BLOCKS=textwrap.dedent("""\
      Insert a blank line after each and every indented objects."""),
    CHECK_CLASS_NAMING_STYLE=textwrap.dedent("""\
      Warn when class definitions do not fit a given naming convention.
      It can be set to one of 'PascalCase', 'camelCase', 'snake_case', or None.
      In the last case this check is disabled."""),
    CHECK_FUNC_NAMING_STYLE=textwrap.dedent("""\
      Warn when function definitions do not fit a given naming convention.
      It can be set to one of 'PascalCase', 'camelCase', 'snake_case', or None.
      In the last case this check is disabled."""),
    CHECK_MODULE_NAMING_STYLE=textwrap.dedent("""\
      Warn when module names do not fit a given naming convention.
      It can be set to one of 'PascalCase', 'camelCase', 'snake_case', or None.
      In the last case this check is disabled."""),
    CHECK_SCRIPT_CODE_ENCAPSULATION=textwrap.dedent("""\
      Top-level code should be encapsulated into functions or classes.
      It is recommended that `if __name__ == '__main__'` be checked in scripts.

          def main():
              pass

          if __name__ == '__main__':
              main()
      """),
    CHECK_VAR_NAMING_STYLE=textwrap.dedent("""\
      Warn when variable definitions or function arguments do not fit
      a given naming convention.
      It can be set to one of 'PascalCase', 'camelCase', 'snake_case', or None.
      In the last case this check is disabled."""),
    COALESCE_BRACKETS=textwrap.dedent("""\
      Do not split consecutive brackets. Only relevant when
      dedent_closing_brackets is set. For example:

         call_func_that_takes_a_dict(
             {
                 'key1': 'value1',
                 'key2': 'value2',
             }
         )

      would reformat to:

         call_func_that_takes_a_dict({
             'key1': 'value1',
             'key2': 'value2',
         })"""),
    COLUMN_LIMIT=textwrap.dedent("""\
      The column limit. Never split / merge lines if set to 0."""),
    CONTINUATION_ALIGN_STYLE=textwrap.dedent("""\
      The style for continuation alignment. Possible values are:

      - SPACE: Use spaces for continuation alignment. This is default behavior.
      - FIXED: Use fixed number (CONTINUATION_INDENT_WIDTH) of columns
        (ie: CONTINUATION_INDENT_WIDTH/INDENT_WIDTH tabs) for continuation
        alignment.
      - VALIGN-RIGHT: Vertically align continuation lines with indent
        characters. Slightly right (one more indent character) if cannot
        vertically align continuation lines with indent characters.

      For options FIXED, and VALIGN-RIGHT are only available when USE_TABS is
      enabled."""),
    CONTINUATION_INDENT_WIDTH=textwrap.dedent("""\
      Indent width used for line continuations."""),
    COPYRIGHT_PATTERN=textwrap.dedent("""\
      A pattern used to detect the copyright docsring."""),
    DEDENT_CLOSING_BRACKETS=textwrap.dedent("""\
      Put closing brackets on a separate line, dedented, if the bracketed
      expression can't fit in a single line. Applies to all kinds of brackets,
      including function definitions and calls. For example:

        config = {
            'key1': 'value1',
            'key2': 'value2',
        }        # <--- this bracket is dedented and on a separate line

        time_series = self.remote_client.query_entity_counters(
            entity='dev3246.region1',
            key='dns.query_latency_tcp',
            transform=Transformation.AVERAGE(window=timedelta(seconds=60)),
            start_ts=now()-timedelta(days=3),
            end_ts=now(),
        )        # <--- this bracket is dedented and on a separate line"""),
    INDENT_CLOSING_BRACKETS=textwrap.dedent("""\
      Put closing brackets on a separate line, indented, if the bracketed
      expression can't fit in a single line. Applies to all kinds of brackets,
      including function definitions and calls. For example:

        config = {
            'key1': 'value1',
            'key2': 'value2',
            }        # <--- this bracket is indented and on a separate line

        time_series = self.remote_client.query_entity_counters(
            entity='dev3246.region1',
            key='dns.query_latency_tcp',
            transform=Transformation.AVERAGE(window=timedelta(seconds=60)),
            start_ts=now()-timedelta(days=3),
            end_ts=now(),
            )        # <--- this bracket is indented and on a separate line"""),
    DISABLE_ALL_WARNINGS=textwrap.dedent("""\
       Disable all static checks and warning messages."""),
    DISABLE_ENDING_COMMA_HEURISTIC=textwrap.dedent("""\
      Disable the heuristic which places each list element on a separate line
      if the list is comma-terminated."""),
    DISABLE_SPLITTING_BY_SEMICOLON=textwrap.dedent("""\
      Never split lines by semicolon"""),
    EACH_DICT_ENTRY_ON_SEPARATE_LINE=textwrap.dedent("""\
      Place each dictionary entry onto its own line."""),
    I18N_COMMENT=textwrap.dedent("""\
      The regex for an i18n comment. The presence of this comment stops
      reformatting of that line, because the comments are required to be
      next to the string they translate."""),
    I18N_FUNCTION_CALL=textwrap.dedent("""\
      The i18n function call names. The presence of this function stops
      reformattting on that line, because the string it has cannot be moved
      away from the i18n comment."""),
    INDENT_DICTIONARY_VALUE=textwrap.dedent("""\
      Indent the dictionary value if it cannot fit on the same line as the
      dictionary key. For example:

        config = {
            'key1':
                'value1',
            'key2': value1 +
                    value2,
        }"""),
    INDENT_WIDTH=textwrap.dedent("""\
      The number of columns to use for indentation."""),
    INDENT_BLANK_LINES=textwrap.dedent("""\
      Indent blank lines."""),
    INSERT_SPACE_AFTER_HASH_CHAR=textwrap.dedent("""\
      Insert a missing space after the # char."""),
    FIX_SHEBANG_HEADER=textwrap.dedent("""\
      Changing shebang to a more accurate format:
         !#/usr/bin/pythonX -> !#/usr/bin/env pythonX
    """),
    FORCE_LONG_LINES_WRAPPING=textwrap.dedent("""\
      Enclose long lines in parentheses in order to make them wrappable:

          # input
          if with > 10 ... and height > 10:
              ...

          # output
          if (with > 10 ... and height > 10):
              ...
      """),
    FORMAT_COPYRIGHT_DOC_STRING=textwrap.dedent("""\
      Replacing indents (lstrip) for a doc string at the top of the source file   
    """),
    FORMAT_LAST_QUOTE_DOC_STRING=textwrap.dedent("""\
      Move last quote to the newline if docstring has length more than 1 line 
    """),
    JOIN_MULTIPLE_LINES=textwrap.dedent("""\
      Join short lines into one line. E.g., single line 'if' statements."""),
    NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS=textwrap.dedent("""\
      Do not include spaces around selected binary operators. For example:

        1 + 2 * 3 - 4 / 5

      will be formatted as follows when configured with "*,/":

        1 + 2*3 - 4/5
      """),
    SAVE_INITIAL_BLANKLINES=textwrap.dedent("""\
      Preserve the original spaces between lines."""),
    SAVE_INITIAL_INDENTS_FORMATTING=textwrap.dedent("""\
      This option will allow to prevent formatting of indents """),
    SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET=textwrap.dedent("""\
      Insert a space between the ending comma and closing bracket of a list,
      etc."""),
    SHOULD_HAVE_ENCODING_HEADER=textwrap.dedent("""\
      This option will enable warning that forces to use encoding in the
       beginning of the file"""),
    SHOULD_NOT_HAVE_WILDCARD_IMPORTS=textwrap.dedent("""\
      This option will enable warning that forces not to use wildcard imports
      (from module import *)"""),
    SPACES_AROUND_POWER_OPERATOR=textwrap.dedent("""\
      Use spaces around the power operator."""),
    SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN=textwrap.dedent("""\
      Use spaces around default or named assigns."""),
    SPACES_BEFORE_COMMENT=textwrap.dedent("""\
      The number of spaces required before a trailing comment.
      This can be a single value (representing the number of spaces
      before each trailing comment) or list of values (representing
      alignment column values; trailing comments within a block will
      be aligned to the first column value that is greater than the maximum
      line length within the block). For example:

      With spaces_before_comment=5:

        1 + 1 # Adding values

      will be formatted as:

        1 + 1     # Adding values <-- 5 spaces between the end of the statement and comment

      With spaces_before_comment=15, 20:

        1 + 1 # Adding values
        two + two # More adding

        longer_statement # This is a longer statement
        short # This is a shorter statement

        a_very_long_statement_that_extends_beyond_the_final_column # Comment
        short # This is a shorter statement

      will be formatted as:

        1 + 1          # Adding values <-- end of line comments in block aligned to col 15
        two + two      # More adding

        longer_statement    # This is a longer statement <-- end of line comments in block aligned to col 20
        short               # This is a shorter statement

        a_very_long_statement_that_extends_beyond_the_final_column  # Comment <-- the end of line comments are aligned based on the line length
        short                                                       # This is a shorter statement

      """),
    SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED=textwrap.dedent("""\
      Split before arguments if the argument list is terminated by a
      comma."""),
    SPLIT_ALL_COMMA_SEPARATED_VALUES=textwrap.dedent("""\
      Split before arguments"""),
    SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES=textwrap.dedent("""\
      Split before arguments, but do not split all subexpressions recursively
      (unless needed)."""),
    SPLIT_BEFORE_ARITHMETIC_OPERATOR=textwrap.dedent("""\
      Set to True to prefer splitting before '+', '-', '*', '/', '//', or '@'
      rather than after."""),
    SPLIT_BEFORE_BITWISE_OPERATOR=textwrap.dedent("""\
      Set to True to prefer splitting before '&', '|' or '^' rather than
      after."""),
    SPLIT_BEFORE_CLOSING_BRACKET=textwrap.dedent("""\
      Split before the closing bracket if a list or dict literal doesn't fit on
      a single line."""),
    SPLIT_BEFORE_DICT_SET_GENERATOR=textwrap.dedent("""\
      Split before a dictionary or set generator (comp_for). For example, note
      the split before the 'for':

        foo = {
            variable: 'Hello world, have a nice day!'
            for variable in bar if variable != 42
        }"""),
    SPLIT_BEFORE_DOT=textwrap.dedent("""\
      Split before the '.' if we need to split a longer expression:

        foo = ('This is a really long string: {}, {}, {}, {}'.format(a, b, c, d))

      would reformat to something like:

        foo = ('This is a really long string: {}, {}, {}, {}'
               .format(a, b, c, d))
      """),
    SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN=textwrap.dedent("""\
      Split after the opening paren which surrounds an expression if it doesn't
      fit on a single line.
      """),
    SPLIT_BEFORE_FIRST_ARGUMENT=textwrap.dedent("""\
      If an argument / parameter list is going to be split, then split before
      the first argument."""),
    SPLIT_BEFORE_LOGICAL_OPERATOR=textwrap.dedent("""\
      Set to True to prefer splitting before 'and' or 'or' rather than
      after."""),
    SPLIT_BEFORE_NAMED_ASSIGNS=textwrap.dedent("""\
      Split named assignments onto individual lines."""),
    SPLIT_COMPLEX_COMPREHENSION=textwrap.dedent("""\
      Set to True to split list comprehensions and generators that have
      non-trivial expressions and multiple clauses before each of these
      clauses. For example:

        result = [
            a_long_var + 100 for a_long_var in xrange(1000)
            if a_long_var % 10]

      would reformat to something like:

        result = [
            a_long_var + 100
            for a_long_var in xrange(1000)
            if a_long_var % 10]
      """),
    SPLIT_PENALTY_AFTER_OPENING_BRACKET=textwrap.dedent("""\
      The penalty for splitting right after the opening bracket."""),
    SPLIT_PENALTY_AFTER_UNARY_OPERATOR=textwrap.dedent("""\
      The penalty for splitting the line after a unary operator."""),
    SPLIT_PENALTY_ARITHMETIC_OPERATOR=textwrap.dedent("""\
      The penalty of splitting the line around the '+', '-', '*', '/', '//',
      ``%``, and '@' operators."""),
    SPLIT_PENALTY_BEFORE_IF_EXPR=textwrap.dedent("""\
      The penalty for splitting right before an if expression."""),
    SPLIT_PENALTY_BITWISE_OPERATOR=textwrap.dedent("""\
      The penalty of splitting the line around the '&', '|', and '^'
      operators."""),
    SPLIT_PENALTY_COMPREHENSION=textwrap.dedent("""\
      The penalty for splitting a list comprehension or generator
      expression."""),
    SPLIT_PENALTY_EXCESS_CHARACTER=textwrap.dedent("""\
      The penalty for characters over the column limit."""),
    SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=textwrap.dedent("""\
      The penalty incurred by adding a line split to the unwrapped line. The
      more line splits added the higher the penalty."""),
    SPLIT_PENALTY_IMPORT_NAMES=textwrap.dedent("""\
      The penalty of splitting a list of "import as" names. For example:

        from a_very_long_or_indented_module_name_yada_yad import (long_argument_1,
                                                                  long_argument_2,
                                                                  long_argument_3)

      would reformat to something like:

        from a_very_long_or_indented_module_name_yada_yad import (
            long_argument_1, long_argument_2, long_argument_3)
      """),
    SPLIT_PENALTY_LOGICAL_OPERATOR=textwrap.dedent("""\
      The penalty of splitting the line around the 'and' and 'or'
      operators."""),
    SPLIT_SINGLE_LINE_IMPORTS=textwrap.dedent("""\
        Format import statements so that there is always a single
        imported module per line.

            import a, b

        will be coverted to

            import a
            import b
        """),
    USE_TABS=textwrap.dedent("""\
      Use the Tab character for indentation."""),
    WARN_BARE_EXCEPT_CLAUSES=textwrap.dedent("""\
      Warn when when no exception type is specified in an except clause.
      """),
    WARN_INCORRECT_COMPARISON_WITH_NONE=textwrap.dedent("""\
      Operator `is` should be used when compare with None."""),
    WARN_LOST_EXCEPTIONS=textwrap.dedent("""\
      Warn if `return` or `break` statements are used in a `finally` block,
      since they may silently swallow an exception."""),
    WARN_MISSING_COPYRIGHT=textwrap.dedent("""\
      Warn if a copyriht string is missing in a module"""),
    WARN_MISPLACED_BARE_RAISE=textwrap.dedent("""\
      Warn if a bare raise is used outside an exception statement"""),
    WARN_NOT_COMMENTED_GLOBAL_VARS=textwrap.dedent("""\
      Warn when a global variable definition is not accompanied by a
      commentary"""),
    WARN_REDEFINITION=textwrap.dedent("""\
      Warn if a function / class / method is redefined."""),
    # BASED_ON_STYLE='Which predefined style this style is based on',
)


def CreatePEP8Style():
  return dict(
      AGGRESSIVELY_MOVE_ALL_IMPORTS_TO_HEAD=False,
      AGGRESSIVELY_MOVE_COPYRIGHT_TO_HEAD=False,
      ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT=True,
      ALLOW_MULTILINE_LAMBDAS=False,
      ALLOW_MULTILINE_DICTIONARY_KEYS=False,
      ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS=True,
      ALLOW_SPLIT_BEFORE_DICT_VALUE=True,
      ARITHMETIC_PRECEDENCE_INDICATION=False,
      BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=False,
      BLANK_LINE_BEFORE_CLASS_DOCSTRING=False,
      BLANK_LINE_BEFORE_MODULE_DOCSTRING=False,
      BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION=2,
      BLANK_LINES_AFTER_INDENTED_BLOCKS=False,
      CHECK_CLASS_NAMING_STYLE=None,
      CHECK_FUNC_NAMING_STYLE=None,
      CHECK_MODULE_NAMING_STYLE=None,
      CHECK_SCRIPT_CODE_ENCAPSULATION=False,
      CHECK_VAR_NAMING_STYLE=None,
      COALESCE_BRACKETS=False,
      COLUMN_LIMIT=79,
      CONTINUATION_ALIGN_STYLE='SPACE',
      CONTINUATION_INDENT_WIDTH=4,
      COPYRIGHT_PATTERN='',
      DEDENT_CLOSING_BRACKETS=False,
      INDENT_CLOSING_BRACKETS=False,
      DISABLE_ALL_WARNINGS=False,
      DISABLE_ENDING_COMMA_HEURISTIC=False,
      DISABLE_SPLITTING_BY_SEMICOLON=False,
      EACH_DICT_ENTRY_ON_SEPARATE_LINE=True,
      FIX_SHEBANG_HEADER=False,
      FORCE_LONG_LINES_WRAPPING=False,
      FORMAT_COPYRIGHT_DOC_STRING=False,
      FORMAT_LAST_QUOTE_DOC_STRING=False,
      I18N_COMMENT='',
      I18N_FUNCTION_CALL='',
      INDENT_DICTIONARY_VALUE=False,
      INDENT_WIDTH=4,
      INDENT_BLANK_LINES=False,
      INSERT_SPACE_AFTER_HASH_CHAR=False,
      JOIN_MULTIPLE_LINES=True,
      NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS=set(),
      SAVE_INITIAL_BLANKLINES=False,
      SAVE_INITIAL_INDENTS_FORMATTING=False,
      SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET=True,
      SPACES_AROUND_POWER_OPERATOR=False,
      SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN=False,
      SPACES_BEFORE_COMMENT=2,
      SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED=False,
      SPLIT_ALL_COMMA_SEPARATED_VALUES=False,
      SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES=False,
      SPLIT_BEFORE_ARITHMETIC_OPERATOR=False,
      SPLIT_BEFORE_BITWISE_OPERATOR=True,
      SPLIT_BEFORE_CLOSING_BRACKET=True,
      SPLIT_BEFORE_DICT_SET_GENERATOR=True,
      SPLIT_BEFORE_DOT=False,
      SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN=False,
      SPLIT_BEFORE_FIRST_ARGUMENT=False,
      SPLIT_BEFORE_LOGICAL_OPERATOR=True,
      SPLIT_BEFORE_NAMED_ASSIGNS=True,
      SPLIT_COMPLEX_COMPREHENSION=False,
      SPLIT_PENALTY_AFTER_OPENING_BRACKET=300,
      SPLIT_PENALTY_AFTER_UNARY_OPERATOR=10000,
      SPLIT_PENALTY_ARITHMETIC_OPERATOR=300,
      SPLIT_PENALTY_BEFORE_IF_EXPR=0,
      SPLIT_PENALTY_BITWISE_OPERATOR=300,
      SPLIT_PENALTY_COMPREHENSION=80,
      SPLIT_PENALTY_EXCESS_CHARACTER=7000,
      SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=30,
      SPLIT_PENALTY_IMPORT_NAMES=0,
      SPLIT_PENALTY_LOGICAL_OPERATOR=300,
      SPLIT_SINGLE_LINE_IMPORTS=False,
      USE_TABS=False,
      SHOULD_HAVE_ENCODING_HEADER=False,
      SHOULD_NOT_HAVE_WILDCARD_IMPORTS=False,
      WARN_BARE_EXCEPT_CLAUSES=False,
      WARN_INCORRECT_COMPARISON_WITH_NONE=False,
      WARN_LOST_EXCEPTIONS=False,
      WARN_MISSING_COPYRIGHT=False,
      WARN_MISPLACED_BARE_RAISE=False,
      WARN_NOT_COMMENTED_GLOBAL_VARS=False,
      WARN_REDEFINITION=False,
  )


def CreateGoogleStyle():
  style = CreatePEP8Style()
  style['ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT'] = False
  style['BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'] = True
  style['COLUMN_LIMIT'] = 80
  style['INDENT_DICTIONARY_VALUE'] = True
  style['INDENT_WIDTH'] = 4
  style['I18N_COMMENT'] = r'#\..*'
  style['I18N_FUNCTION_CALL'] = ['N_', '_']
  style['JOIN_MULTIPLE_LINES'] = False
  style['SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET'] = False
  style['SPLIT_BEFORE_BITWISE_OPERATOR'] = False
  style['SPLIT_BEFORE_DICT_SET_GENERATOR'] = False
  style['SPLIT_BEFORE_LOGICAL_OPERATOR'] = False
  style['SPLIT_COMPLEX_COMPREHENSION'] = True
  style['SPLIT_PENALTY_COMPREHENSION'] = 2100
  return style


def CreateHuaweiStyle():
  style = CreateGoogleStyle()
  style['AGGRESSIVELY_MOVE_ALL_IMPORTS_TO_HEAD'] = True
  style['AGGRESSIVELY_MOVE_COPYRIGHT_TO_HEAD'] = True
  style['FORMAT_COPYRIGHT_DOC_STRING'] = True
  style['FORMAT_LAST_QUOTE_DOC_STRING'] = True
  style['SHOULD_HAVE_ENCODING_HEADER'] = True
  style['NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS'] = '*'
  style['SPLIT_SINGLE_LINE_IMPORTS'] = True
  style['BLANK_LINES_AFTER_INDENTED_BLOCKS'] = True
  style['SAVE_INITIAL_INDENTS_FORMATTING'] = False
  style['COLUMN_LIMIT'] = 80
  style['COPYRIGHT_PATTERN'] = 'Copyright Information: Huawei'
  style['FORCE_LONG_LINES_WRAPPING'] = True
  style['INSERT_SPACE_AFTER_HASH_CHAR'] = True
  style['SHOULD_NOT_HAVE_WILDCARD_IMPORTS'] = True
  style['WARN_BARE_EXCEPT_CLAUSES'] = True
  style['WARN_INCORRECT_COMPARISON_WITH_NONE'] = True
  style['WARN_LOST_EXCEPTIONS'] = True
  style['WARN_MISSING_COPYRIGHT'] = True
  style['WARN_MISPLACED_BARE_RAISE'] = True
  style['WARN_NOT_COMMENTED_GLOBAL_VARS'] = True
  style['WARN_REDEFINITION'] = True
  style['FIX_SHEBANG_HEADER'] = True
  style['CHECK_CLASS_NAMING_STYLE'] = 'PASCALCASE'
  style['CHECK_FUNC_NAMING_STYLE'] = 'SNAKECASE'
  style['CHECK_MODULE_NAMING_STYLE'] = 'SNAKECASE'
  style['CHECK_VAR_NAMING_STYLE'] = 'SNAKECASE'
  style['CHECK_SCRIPT_CODE_ENCAPSULATION'] = True
  return style


def CreateChromiumStyle():
  style = CreateGoogleStyle()
  style['ALLOW_MULTILINE_DICTIONARY_KEYS'] = True
  style['ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS'] = False
  style['INDENT_DICTIONARY_VALUE'] = True
  style['INDENT_WIDTH'] = 2
  style['SPLIT_BEFORE_BITWISE_OPERATOR'] = True
  style['SPLIT_BEFORE_DOT'] = True
  style['SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN'] = True
  return style


def CreateFacebookStyle():
  style = CreatePEP8Style()
  style['ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT'] = False
  style['COLUMN_LIMIT'] = 80
  style['DEDENT_CLOSING_BRACKETS'] = True
  style['INDENT_CLOSING_BRACKETS'] = False
  style['INDENT_DICTIONARY_VALUE'] = True
  style['JOIN_MULTIPLE_LINES'] = False
  style['SPACES_BEFORE_COMMENT'] = 2
  style['SPLIT_PENALTY_AFTER_OPENING_BRACKET'] = 0
  style['SPLIT_PENALTY_BEFORE_IF_EXPR'] = 30
  style['SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT'] = 30
  style['SPLIT_BEFORE_LOGICAL_OPERATOR'] = False
  style['SPLIT_BEFORE_BITWISE_OPERATOR'] = False
  return style


_STYLE_NAME_TO_FACTORY = dict(
    pep8=CreatePEP8Style,
    chromium=CreateChromiumStyle,
    google=CreateGoogleStyle,
    facebook=CreateFacebookStyle,
    huawei=CreateHuaweiStyle
)

_DEFAULT_STYLE_TO_FACTORY = [
    (CreateChromiumStyle(), CreateChromiumStyle),
    (CreateFacebookStyle(), CreateFacebookStyle),
    (CreateGoogleStyle(), CreateGoogleStyle),
    (CreatePEP8Style(), CreatePEP8Style),
    (CreateHuaweiStyle(), CreateHuaweiStyle)
]


def _GetStyleFactory(style):
  for def_style, factory in _DEFAULT_STYLE_TO_FACTORY:
    if style == def_style:
      return factory
  return None


def _ContinuationAlignStyleStringConverter(s):
  """Option value converter for a continuation align style string."""
  accepted_styles = ('SPACE', 'FIXED', 'VALIGN-RIGHT')
  if s:
    r = s.strip('"\'').replace('_', '-').upper()
    if r not in accepted_styles:
      raise ValueError('unknown continuation align style: %r' % (s,))
  else:
    r = accepted_styles[0]
  return r


def _StringListConverter(s):
  """Option value converter for a comma-separated list of strings."""
  return [part.strip() for part in s.split(',')]


def _StringSetConverter(s):
  """Option value converter for a comma-separated set of strings."""
  if len(s) > 2 and s[0] in '"\'':
    s = s[1:-1]
  return set(part.strip() for part in s.split(','))


def _BoolConverter(s):
  """Option value converter for a boolean."""
  return py3compat.CONFIGPARSER_BOOLEAN_STATES[s.lower()]


def _IntListConverter(s):
  """Option value converter for a comma-separated list of integers."""
  s = s.strip()
  if s.startswith('[') and s.endswith(']'):
    s = s[1:-1]

  return [int(part.strip()) for part in s.split(',') if part.strip()]


def _IntOrIntListConverter(s):
  """Option value converter for an integer or list of integers."""
  if len(s) > 2 and s[0] in '"\'':
    s = s[1:-1]
  return _IntListConverter(s) if ',' in s else int(s)


def _NamingStyleStringConverter(s):
    accepted_styles = {'PASCALCASE', 'CAMELCASE', 'SNAKECASE', 'NONE'}

    if s:
        s = s.strip('"\'').replace('_', '').replace('-', '').upper()

        if s not in accepted_styles:
            raise ValueError('unknown naming style: %s' % s)
        if s != 'NONE':
            return s

    return None

def _SimpleStringConverter(s):
    return s

# Different style options need to have their values interpreted differently when
# read from the config file. This dict maps an option name to a "converter"
# function that accepts the string read for the option's value from the file and
# returns it wrapper in actual Python type that's going to be meaningful to
# yapf.
#
# Note: this dict has to map all the supported style options.
_STYLE_OPTION_VALUE_CONVERTER = dict(
    AGGRESSIVELY_MOVE_ALL_IMPORTS_TO_HEAD=_BoolConverter,
    AGGRESSIVELY_MOVE_COPYRIGHT_TO_HEAD=_BoolConverter,
    ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT=_BoolConverter,
    ALLOW_MULTILINE_LAMBDAS=_BoolConverter,
    ALLOW_MULTILINE_DICTIONARY_KEYS=_BoolConverter,
    ALLOW_SPLIT_BEFORE_DEFAULT_OR_NAMED_ASSIGNS=_BoolConverter,
    ALLOW_SPLIT_BEFORE_DICT_VALUE=_BoolConverter,
    ARITHMETIC_PRECEDENCE_INDICATION=_BoolConverter,
    BLANK_LINES_AFTER_INDENTED_BLOCKS=_BoolConverter,
    BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF=_BoolConverter,
    BLANK_LINE_BEFORE_CLASS_DOCSTRING=_BoolConverter,
    BLANK_LINE_BEFORE_MODULE_DOCSTRING=_BoolConverter,
    BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION=int,
    CHECK_CLASS_NAMING_STYLE=_NamingStyleStringConverter,
    CHECK_FUNC_NAMING_STYLE=_NamingStyleStringConverter,
    CHECK_MODULE_NAMING_STYLE=_NamingStyleStringConverter,
    CHECK_SCRIPT_CODE_ENCAPSULATION=_BoolConverter,
    CHECK_VAR_NAMING_STYLE=_NamingStyleStringConverter,
    COALESCE_BRACKETS=_BoolConverter,
    COLUMN_LIMIT=int,
    CONTINUATION_ALIGN_STYLE=_ContinuationAlignStyleStringConverter,
    CONTINUATION_INDENT_WIDTH=int,
    COPYRIGHT_PATTERN=_SimpleStringConverter,
    DEDENT_CLOSING_BRACKETS=_BoolConverter,
    INDENT_CLOSING_BRACKETS=_BoolConverter,
    DISABLE_ALL_WARNINGS=_BoolConverter,
    DISABLE_ENDING_COMMA_HEURISTIC=_BoolConverter,
    DISABLE_SPLITTING_BY_SEMICOLON=_BoolConverter,
    EACH_DICT_ENTRY_ON_SEPARATE_LINE=_BoolConverter,
    I18N_COMMENT=str,
    I18N_FUNCTION_CALL=_StringListConverter,
    INDENT_DICTIONARY_VALUE=_BoolConverter,
    INDENT_WIDTH=int,
    INDENT_BLANK_LINES=_BoolConverter,
    FORCE_LONG_LINES_WRAPPING=_BoolConverter,
    INSERT_SPACE_AFTER_HASH_CHAR=_BoolConverter,
    JOIN_MULTIPLE_LINES=_BoolConverter,
    NO_SPACES_AROUND_SELECTED_BINARY_OPERATORS=_StringSetConverter,
    SAVE_INITIAL_BLANKLINES=_BoolConverter,
    SAVE_INITIAL_INDENTS_FORMATTING=_BoolConverter,
    FIX_SHEBANG_HEADER=_BoolConverter,
    FORMAT_COPYRIGHT_DOC_STRING=_BoolConverter,
    FORMAT_LAST_QUOTE_DOC_STRING=_BoolConverter,
    SHOULD_HAVE_ENCODING_HEADER=_BoolConverter,
    SHOULD_NOT_HAVE_WILDCARD_IMPORTS=_BoolConverter,
    SPACE_BETWEEN_ENDING_COMMA_AND_CLOSING_BRACKET=_BoolConverter,
    SPACES_AROUND_POWER_OPERATOR=_BoolConverter,
    SPACES_AROUND_DEFAULT_OR_NAMED_ASSIGN=_BoolConverter,
    SPACES_BEFORE_COMMENT=_IntOrIntListConverter,
    SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED=_BoolConverter,
    SPLIT_ALL_COMMA_SEPARATED_VALUES=_BoolConverter,
    SPLIT_ALL_TOP_LEVEL_COMMA_SEPARATED_VALUES=_BoolConverter,
    SPLIT_BEFORE_ARITHMETIC_OPERATOR=_BoolConverter,
    SPLIT_BEFORE_BITWISE_OPERATOR=_BoolConverter,
    SPLIT_BEFORE_CLOSING_BRACKET=_BoolConverter,
    SPLIT_BEFORE_DICT_SET_GENERATOR=_BoolConverter,
    SPLIT_BEFORE_DOT=_BoolConverter,
    SPLIT_BEFORE_EXPRESSION_AFTER_OPENING_PAREN=_BoolConverter,
    SPLIT_BEFORE_FIRST_ARGUMENT=_BoolConverter,
    SPLIT_BEFORE_LOGICAL_OPERATOR=_BoolConverter,
    SPLIT_BEFORE_NAMED_ASSIGNS=_BoolConverter,
    SPLIT_COMPLEX_COMPREHENSION=_BoolConverter,
    SPLIT_PENALTY_AFTER_OPENING_BRACKET=int,
    SPLIT_PENALTY_AFTER_UNARY_OPERATOR=int,
    SPLIT_PENALTY_ARITHMETIC_OPERATOR=int,
    SPLIT_PENALTY_BEFORE_IF_EXPR=int,
    SPLIT_PENALTY_BITWISE_OPERATOR=int,
    SPLIT_PENALTY_COMPREHENSION=int,
    SPLIT_PENALTY_EXCESS_CHARACTER=int,
    SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT=int,
    SPLIT_PENALTY_IMPORT_NAMES=int,
    SPLIT_PENALTY_LOGICAL_OPERATOR=int,
    SPLIT_SINGLE_LINE_IMPORTS=_BoolConverter,
    USE_TABS=_BoolConverter,
    WARN_BARE_EXCEPT_CLAUSES=_BoolConverter,
    WARN_INCORRECT_COMPARISON_WITH_NONE=_BoolConverter,
    WARN_LOST_EXCEPTIONS=_BoolConverter,
    WARN_MISSING_COPYRIGHT=_BoolConverter,
    WARN_MISPLACED_BARE_RAISE=_BoolConverter,
    WARN_NOT_COMMENTED_GLOBAL_VARS=_BoolConverter,
    WARN_REDEFINITION=_BoolConverter,
)


def CreateStyleFromConfig(style_config):
  """Create a style dict from the given config.

  Arguments:
    style_config: either a style name or a file name. The file is expected to
      contain settings. It can have a special BASED_ON_STYLE setting naming the
      style which it derives from. If no such setting is found, it derives from
      the default style. When style_config is None, the _GLOBAL_STYLE_FACTORY
      config is created.

  Returns:
    A style dict.

  Raises:
    StyleConfigError: if an unknown style option was encountered.
  """

  def GlobalStyles():
    for style, _ in _DEFAULT_STYLE_TO_FACTORY:
      yield style

  def_style = False
  if style_config is None:
    for style in GlobalStyles():
      if _style == style:
        def_style = True
        break
    if not def_style:
      return _style
    return _GLOBAL_STYLE_FACTORY()

  if isinstance(style_config, dict):
    config = _CreateConfigParserFromConfigDict(style_config)
  elif isinstance(style_config, py3compat.basestring):
    style_factory = _STYLE_NAME_TO_FACTORY.get(style_config.lower())
    if style_factory is not None:
      return style_factory()
    if style_config.startswith('{'):
      # Most likely a style specification from the command line.
      config = _CreateConfigParserFromConfigString(style_config)
    else:
      # Unknown config name: assume it's a file name then.
      config = _CreateConfigParserFromConfigFile(style_config)
  return _CreateStyleFromConfigParser(config)


def _CreateConfigParserFromConfigDict(config_dict):
  config = py3compat.ConfigParser()
  config.add_section('style')
  for key, value in config_dict.items():
    config.set('style', key, str(value))
  return config


def _CreateConfigParserFromConfigString(config_string):
  """Given a config string from the command line, return a config parser."""
  if config_string[0] != '{' or config_string[-1] != '}':
    raise StyleConfigError(
        "Invalid style dict syntax: '{}'.".format(config_string))
  config = py3compat.ConfigParser()
  config.add_section('style')
  for key, value, _ in re.findall(
      r'([a-zA-Z0-9_]+)\s*[:=]\s*'
      r'(?:'
      r'((?P<quote>[\'"]).*?(?P=quote)|'
      r'[a-zA-Z0-9_]+)'
      r')', config_string):  # yapf: disable
    config.set('style', key, value)
  return config


def _CreateConfigParserFromConfigFile(config_filename):
  """Read the file and return a ConfigParser object."""
  if not os.path.exists(config_filename):
    # Provide a more meaningful error here.
    raise StyleConfigError(
        '"{0}" is not a valid style or file path'.format(config_filename))
  with open(config_filename) as style_file:
    config = py3compat.ConfigParser()
    config.read_file(style_file)
    if config_filename.endswith(SETUP_CONFIG):
      if not config.has_section('yapf'):
        raise StyleConfigError(
            'Unable to find section [yapf] in {0}'.format(config_filename))
    elif config_filename.endswith(LOCAL_STYLE):
      if not config.has_section('style'):
        raise StyleConfigError(
            'Unable to find section [style] in {0}'.format(config_filename))
    else:
      if not config.has_section('style'):
        raise StyleConfigError(
            'Unable to find section [style] in {0}'.format(config_filename))
    return config


def _CreateStyleFromConfigParser(config):
  """Create a style dict from a configuration file.

  Arguments:
    config: a ConfigParser object.

  Returns:
    A style dict.

  Raises:
    StyleConfigError: if an unknown style option was encountered.
  """
  # Initialize the base style.
  section = 'yapf' if config.has_section('yapf') else 'style'
  if config.has_option('style', 'based_on_style'):
    based_on = config.get('style', 'based_on_style').lower()
    base_style = _STYLE_NAME_TO_FACTORY[based_on]()
  elif config.has_option('yapf', 'based_on_style'):
    based_on = config.get('yapf', 'based_on_style').lower()
    base_style = _STYLE_NAME_TO_FACTORY[based_on]()
  else:
    base_style = _GLOBAL_STYLE_FACTORY()

  # Read all options specified in the file and update the style.
  for option, value in config.items(section):
    if option.lower() == 'based_on_style':
      # Now skip this one - we've already handled it and it's not one of the
      # recognized style options.
      continue
    option = option.upper()
    if option not in _STYLE_OPTION_VALUE_CONVERTER:
      raise StyleConfigError('Unknown style option "{0}"'.format(option))
    try:
      base_style[option] = _STYLE_OPTION_VALUE_CONVERTER[option](value)
    except ValueError:
      raise StyleConfigError("'{}' is not a valid setting for {}.".format(
          value, option))
  return base_style


# The default style - used if yapf is not invoked without specifically
# requesting a formatting style.
DEFAULT_STYLE = 'pep8'
DEFAULT_STYLE_FACTORY = CreatePEP8Style
_GLOBAL_STYLE_FACTORY = CreatePEP8Style

# The name of the file to use for global style definition.
GLOBAL_STYLE = (
    os.path.join(
        os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'yapf',
        'style'))

# The name of the file to use for directory-local style definition.
LOCAL_STYLE = '.style.yapf'

# Alternative place for directory-local style definition. Style should be
# specified in the '[yapf]' section.
SETUP_CONFIG = 'setup.cfg'

# TODO(eliben): For now we're preserving the global presence of a style dict.
# Refactor this so that the style is passed around through yapf rather than
# being global.
_style = None
SetGlobalStyle(_GLOBAL_STYLE_FACTORY())

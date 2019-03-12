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
"""Decide what the format for the code should be.

The `unwrapped_line.UnwrappedLine`s are now ready to be formatted.
UnwrappedLines that can be merged together are. The best formatting is returned
as a string.

  Reformat(): the main function exported by this module.
"""

from __future__ import unicode_literals
import collections
import heapq
import re

from lib2to3 import pytree
from lib2to3.pgen2 import token

from yapf.yapflib import format_decision_state
from yapf.yapflib import format_token
from yapf.yapflib import line_joiner
from yapf.yapflib import pytree_utils
from yapf.yapflib import style
from yapf.yapflib import verifier


def Reformat(uwlines, verify=False, lines=None):
  """Reformat the unwrapped lines.

  Arguments:
    uwlines: (list of unwrapped_line.UnwrappedLine) Lines we want to format.
    verify: (bool) True if reformatted code should be verified for syntax.
    lines: (set of int) The lines which can be modified or None if there is no
      line range restriction.

  Returns:
    A string representing the reformatted code.
  """
  final_lines = []
  prev_uwline = None  # The previous line.
  indent_width = style.Get('INDENT_WIDTH')

  for uwline in _SingleOrMergedLines(uwlines):
    first_token = uwline.first
    _FormatFirstToken(first_token, uwline.depth, prev_uwline, final_lines)

    indent_amt = indent_width * uwline.depth
    state = format_decision_state.FormatDecisionState(uwline, indent_amt)
    state.MoveStateToNextToken()

    if not uwline.disable:
      if uwline.first.is_comment:
        uwline.first.node.value = uwline.first.node.value.rstrip()
      elif uwline.last.is_comment:
        uwline.last.node.value = uwline.last.node.value.rstrip()
      if prev_uwline and prev_uwline.disable:
        # Keep the vertical spacing between a disabled and enabled formatting
        # region.
        _RetainRequiredVerticalSpacingBetweenTokens(uwline.first,
                                                    prev_uwline.last, lines)
      if any(tok.is_comment for tok in uwline.tokens):
        _RetainVerticalSpacingBeforeComments(uwline)

    if uwline.disable or _LineHasContinuationMarkers(uwline):
      _RetainHorizontalSpacing(uwline)
      _RetainRequiredVerticalSpacing(uwline, prev_uwline, lines)
      _EmitLineUnformatted(state)

    elif (_LineContainsPylintDisableLineTooLong(uwline) or
          _LineContainsI18n(uwline)):
      # Don't modify vertical spacing, but fix any horizontal spacing issues.
      _RetainRequiredVerticalSpacing(uwline, prev_uwline, lines)
      _EmitLineUnformatted(state)

    elif _CanPlaceOnSingleLine(uwline) and not any(tok.must_split
                                                   for tok in uwline.tokens):
      # The unwrapped line fits on one line.
      while state.next_token:
        state.AddTokenToState(newline=False, dry_run=False)

    else:
      if not _AnalyzeSolutionSpace(state):
        # Failsafe mode. If there isn't a solution to the line, then just emit
        # it as is.
        state = format_decision_state.FormatDecisionState(uwline, indent_amt)
        state.MoveStateToNextToken()
        _RetainHorizontalSpacing(uwline)
        _RetainRequiredVerticalSpacing(uwline, prev_uwline, None)
        _EmitLineUnformatted(state)

    final_lines.append(uwline)
    prev_uwline = uwline

  _AlignTrailingComments(final_lines)
  return _FormatFinalLines(final_lines, verify)


def _RetainHorizontalSpacing(uwline):
  """Retain all horizontal spacing between tokens."""
  for tok in uwline.tokens:
    tok.RetainHorizontalSpacing(uwline.first.column, uwline.depth)


def _RetainRequiredVerticalSpacing(cur_uwline, prev_uwline, lines):
  prev_tok = None
  if prev_uwline is not None:
    prev_tok = prev_uwline.last
  for cur_tok in cur_uwline.tokens:
    _RetainRequiredVerticalSpacingBetweenTokens(cur_tok, prev_tok, lines)
    prev_tok = cur_tok


def _RetainRequiredVerticalSpacingBetweenTokens(cur_tok, prev_tok, lines):
  """Retain vertical spacing between two tokens if not in editable range."""
  if prev_tok is None:
    return

  if prev_tok.is_string:
    prev_lineno = prev_tok.lineno + prev_tok.value.count('\n')
  elif prev_tok.is_pseudo_paren:
    if not prev_tok.previous_token.is_multiline_string:
      prev_lineno = prev_tok.previous_token.lineno
    else:
      prev_lineno = prev_tok.lineno
  else:
    prev_lineno = prev_tok.lineno

  if cur_tok.is_comment:
    cur_lineno = cur_tok.lineno - cur_tok.value.count('\n')
  else:
    cur_lineno = cur_tok.lineno

  if prev_tok.value.endswith('\\'):
    prev_lineno += prev_tok.value.count('\n')

  required_newlines = cur_lineno - prev_lineno
  if cur_tok.is_comment and not prev_tok.is_comment:
    # Don't adjust between a comment and non-comment.
    pass
  elif lines and (cur_lineno in lines or prev_lineno in lines):
    desired_newlines = cur_tok.whitespace_prefix.count('\n')
    if desired_newlines < required_newlines:
      desired_newlines = required_newlines
    whitespace_lines = range(prev_lineno + 1, cur_lineno)
    deletable_lines = len(lines.intersection(whitespace_lines))
    required_newlines = max(required_newlines - deletable_lines,
                            desired_newlines)

  cur_tok.AdjustNewlinesBefore(required_newlines)


def _RetainVerticalSpacingBeforeComments(uwline):
  """Retain vertical spacing before comments."""
  prev_token = None
  for tok in uwline.tokens:
    if tok.is_comment and prev_token:
      if tok.lineno - tok.value.count('\n') - prev_token.lineno > 1:
        tok.AdjustNewlinesBefore(ONE_BLANK_LINE)

    prev_token = tok


def _EmitLineUnformatted(state):
  """Emit the line without formatting.

  The line contains code that if reformatted would break a non-syntactic
  convention. E.g., i18n comments and function calls are tightly bound by
  convention. Instead, we calculate when / if a newline should occur and honor
  that. But otherwise the code emitted will be the same as the original code.

  Arguments:
    state: (format_decision_state.FormatDecisionState) The format decision
      state.
  """
  while state.next_token:
    previous_token = state.next_token.previous_token
    previous_lineno = previous_token.lineno

    if previous_token.is_multiline_string or previous_token.is_string:
      previous_lineno += previous_token.value.count('\n')

    if previous_token.is_continuation:
      newline = False
    else:
      newline = state.next_token.lineno > previous_lineno

    state.AddTokenToState(newline=newline, dry_run=False)


def _LineContainsI18n(uwline):
  """Return true if there are i18n comments or function calls in the line.

  I18n comments and pseudo-function calls are closely related. They cannot
  be moved apart without breaking i18n.

  Arguments:
    uwline: (unwrapped_line.UnwrappedLine) The line currently being formatted.

  Returns:
    True if the line contains i18n comments or function calls. False otherwise.
  """
  if style.Get('I18N_COMMENT'):
    for tok in uwline.tokens:
      if tok.is_comment and re.match(style.Get('I18N_COMMENT'), tok.value):
        # Contains an i18n comment.
        return True

  if style.Get('I18N_FUNCTION_CALL'):
    length = len(uwline.tokens)
    index = 0
    while index < length - 1:
      if (uwline.tokens[index + 1].value == '(' and
          uwline.tokens[index].value in style.Get('I18N_FUNCTION_CALL')):
        return True
      index += 1

  return False


def _LineContainsPylintDisableLineTooLong(uwline):
  """Return true if there is a "pylint: disable=line-too-long" comment."""
  return any(
      re.search(r'\bpylint:\s+disable=line-too-long\b', tok.value)
      for tok in uwline.tokens
      if tok.is_comment)


def _LineHasContinuationMarkers(uwline):
  """Return true if the line has continuation markers in it."""
  return any(tok.is_continuation for tok in uwline.tokens)


def _CanPlaceOnSingleLine(uwline):
  """Determine if the unwrapped line can go on a single line.

  Arguments:
    uwline: (unwrapped_line.UnwrappedLine) The line currently being formatted.

  Returns:
    True if the line can or should be added to a single line. False otherwise.
  """
  indent_amt = style.Get('INDENT_WIDTH') * uwline.depth
  last = uwline.last
  last_index = -1
  if last.is_pylint_comment or last.is_pytype_comment:
    last = last.previous_token
    last_index = -2
  if last is None:
    return True
  return (last.total_length + indent_amt <= style.Get('COLUMN_LIMIT') and
          not any(tok.is_comment for tok in uwline.tokens[:last_index]))


def _AlignTrailingComments(final_lines):
  final_lines_index = 0
  while final_lines_index < len(final_lines):
    line = final_lines[final_lines_index]
    assert line.tokens

    processed_content = False

    for tok in line.tokens:
      if (tok.is_comment and isinstance(tok.spaces_required_before, list) and
          tok.value.startswith('#')):
        # All trailing comments and comments that appear on a line by themselves
        # in this block should be indented at the same level. The block is
        # terminated by an empty line or EOF. Enumerate through each line in
        # the block and calculate the max line length. Once complete, use the
        # first col value greater than that value and create the necessary for
        # each line accordingly.
        all_pc_line_lengths = []  # All pre-comment line lengths
        max_line_length = 0

        while True:
          # EOF
          if final_lines_index + len(all_pc_line_lengths) == len(final_lines):
            break

          this_line = final_lines[final_lines_index + len(all_pc_line_lengths)]

          # Blank line - note that content is preformatted so we don't need to
          # worry about spaces/tabs; a blank line will always be '\n\n'.
          assert this_line.tokens
          if (all_pc_line_lengths and
              this_line.tokens[0].formatted_whitespace_prefix.startswith('\n\n')
             ):
            break

          if this_line.disable:
            all_pc_line_lengths.append([])
            continue

          # Calculate the length of each line in this unwrapped line.
          line_content = ''
          pc_line_lengths = []

          for line_tok in this_line.tokens:
            whitespace_prefix = line_tok.formatted_whitespace_prefix

            newline_index = whitespace_prefix.rfind('\n')
            if newline_index != -1:
              max_line_length = max(max_line_length, len(line_content))
              line_content = ''

              whitespace_prefix = whitespace_prefix[newline_index + 1:]

            if line_tok.is_comment:
              pc_line_lengths.append(len(line_content))
            else:
              line_content += '{}{}'.format(whitespace_prefix, line_tok.value)

          if pc_line_lengths:
            max_line_length = max(max_line_length, max(pc_line_lengths))

          all_pc_line_lengths.append(pc_line_lengths)

        # Calculate the aligned column value
        max_line_length += 2

        aligned_col = None
        for potential_col in tok.spaces_required_before:
          if potential_col > max_line_length:
            aligned_col = potential_col
            break

        if aligned_col is None:
          aligned_col = max_line_length

        # Update the comment token values based on the aligned values
        for all_pc_line_lengths_index, pc_line_lengths in enumerate(
            all_pc_line_lengths):
          if not pc_line_lengths:
            continue

          this_line = final_lines[final_lines_index + all_pc_line_lengths_index]

          pc_line_length_index = 0
          for line_tok in this_line.tokens:
            if line_tok.is_comment:
              assert pc_line_length_index < len(pc_line_lengths)
              assert pc_line_lengths[pc_line_length_index] < aligned_col

              # Note that there may be newlines embedded in the comments, so
              # we need to apply a whitespace prefix to each line.
              whitespace = ' ' * (
                  aligned_col - pc_line_lengths[pc_line_length_index] - 1)
              pc_line_length_index += 1

              line_content = []

              for comment_line_index, comment_line in enumerate(
                  line_tok.value.split('\n')):
                line_content.append('{}{}'.format(whitespace,
                                                  comment_line.strip()))

                if comment_line_index == 0:
                  whitespace = ' ' * (aligned_col - 1)

              line_content = '\n'.join(line_content)

              # Account for initial whitespace already slated for the
              # beginning of the line.
              existing_whitespace_prefix = \
                line_tok.formatted_whitespace_prefix.lstrip('\n')

              if line_content.startswith(existing_whitespace_prefix):
                line_content = line_content[len(existing_whitespace_prefix):]

              line_tok.value = line_content

          assert pc_line_length_index == len(pc_line_lengths)

        final_lines_index += len(all_pc_line_lengths)

        processed_content = True
        break

    if not processed_content:
      final_lines_index += 1


def _FormatFinalLines(final_lines, verify):
  """Compose the final output from the finalized lines."""
  formatted_code = []
  for line in final_lines:
    formatted_line = []
    for tok in line.tokens:
      if not tok.is_pseudo_paren:
        formatted_line.append(tok.formatted_whitespace_prefix)
        formatted_line.append(tok.value)
      else:
        if (not tok.next_token.whitespace_prefix.startswith('\n') and
            not tok.next_token.whitespace_prefix.startswith(' ')):
          if (tok.previous_token.value == ':' or
              tok.next_token.value not in ',}])'):
            formatted_line.append(' ')

    formatted_code.append(''.join(formatted_line))
    if verify:
      verifier.VerifyCode(formatted_code[-1])

  return ''.join(formatted_code) + '\n'


class _StateNode(object):
  """An edge in the solution space from 'previous.state' to 'state'.

  Attributes:
    state: (format_decision_state.FormatDecisionState) The format decision state
      for this node.
    newline: If True, then on the edge from 'previous.state' to 'state' a
      newline is inserted.
    previous: (_StateNode) The previous state node in the graph.
  """

  # TODO(morbo): Add a '__cmp__' method.

  def __init__(self, state, newline, previous):
    self.state = state.Clone()
    self.newline = newline
    self.previous = previous

  def __repr__(self):  # pragma: no cover
    return 'StateNode(state=[\n{0}\n], newline={1})'.format(
        self.state, self.newline)


# A tuple of (penalty, count) that is used to prioritize the BFS. In case of
# equal penalties, we prefer states that were inserted first. During state
# generation, we make sure that we insert states first that break the line as
# late as possible.
_OrderedPenalty = collections.namedtuple('OrderedPenalty', ['penalty', 'count'])

# An item in the prioritized BFS search queue. The 'StateNode's 'state' has
# the given '_OrderedPenalty'.
_QueueItem = collections.namedtuple('QueueItem',
                                    ['ordered_penalty', 'state_node'])


def _AnalyzeSolutionSpace(initial_state):
  """Analyze the entire solution space starting from initial_state.

  This implements a variant of Dijkstra's algorithm on the graph that spans
  the solution space (LineStates are the nodes). The algorithm tries to find
  the shortest path (the one with the lowest penalty) from 'initial_state' to
  the state where all tokens are placed.

  Arguments:
    initial_state: (format_decision_state.FormatDecisionState) The initial state
      to start the search from.

  Returns:
    True if a formatting solution was found. False otherwise.
  """
  count = 0
  seen = set()
  p_queue = []

  # Insert start element.
  node = _StateNode(initial_state, False, None)
  heapq.heappush(p_queue, _QueueItem(_OrderedPenalty(0, count), node))

  count += 1
  while p_queue:
    item = p_queue[0]
    penalty = item.ordered_penalty.penalty
    node = item.state_node
    if not node.state.next_token:
      break
    heapq.heappop(p_queue)

    if count > 10000:
      node.state.ignore_stack_for_comparison = True

    if node.state in seen:
      continue

    seen.add(node.state)

    # FIXME(morbo): Add a 'decision' element?

    count = _AddNextStateToQueue(penalty, node, False, count, p_queue)
    count = _AddNextStateToQueue(penalty, node, True, count, p_queue)

  if not p_queue:
    # We weren't able to find a solution. Do nothing.
    return False

  _ReconstructPath(initial_state, heapq.heappop(p_queue).state_node)
  return True


def _AddNextStateToQueue(penalty, previous_node, newline, count, p_queue):
  """Add the following state to the analysis queue.

  Assume the current state is 'previous_node' and has been reached with a
  penalty of 'penalty'. Insert a line break if 'newline' is True.

  Arguments:
    penalty: (int) The penalty associated with the path up to this point.
    previous_node: (_StateNode) The last _StateNode inserted into the priority
      queue.
    newline: (bool) Add a newline if True.
    count: (int) The number of elements in the queue.
    p_queue: (heapq) The priority queue representing the solution space.

  Returns:
    The updated number of elements in the queue.
  """
  must_split = previous_node.state.MustSplit()
  if newline and not previous_node.state.CanSplit(must_split):
    # Don't add a newline if the token cannot be split.
    return count
  if not newline and must_split:
    # Don't add a token we must split but where we aren't splitting.
    return count

  node = _StateNode(previous_node.state, newline, previous_node)
  penalty += node.state.AddTokenToState(
      newline=newline, dry_run=True, must_split=must_split)
  heapq.heappush(p_queue, _QueueItem(_OrderedPenalty(penalty, count), node))
  return count + 1


def _ReconstructPath(initial_state, current):
  """Reconstruct the path through the queue with lowest penalty.

  Arguments:
    initial_state: (format_decision_state.FormatDecisionState) The initial state
      to start the search from.
    current: (_StateNode) The node in the decision graph that is the end point
      of the path with the least penalty.
  """
  path = collections.deque()

  while current.previous:
    path.appendleft(current)
    current = current.previous

  for node in path:
    initial_state.AddTokenToState(newline=node.newline, dry_run=False)


def _FormatFirstToken(first_token, indent_depth, prev_uwline, final_lines):
  """Format the first token in the unwrapped line.

  Add a newline and the required indent before the first token of the unwrapped
  line.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the unwrapped
      line.
    indent_depth: (int) The line's indentation depth.
    prev_uwline: (list of unwrapped_line.UnwrappedLine) The unwrapped line
      previous to this line.
    final_lines: (list of unwrapped_line.UnwrappedLine) The unwrapped lines
      that have already been processed.
  """
  first_token.AddWhitespacePrefix(
      _CalculateNumberOfNewlines(first_token, indent_depth, prev_uwline,
                                 final_lines),
      indent_level=indent_depth)


NO_BLANK_LINES = 1
ONE_BLANK_LINE = 2
TWO_BLANK_LINES = 3


def _IsClassOrDef(uwline):
  if uwline.first.value in {'class', 'def'}:
    return True

  return [t.value for t in uwline.tokens[:2]] == ['async', 'def']


def _CalculateNumberOfNewlines(first_token, indent_depth, prev_uwline,
                               final_lines):
  """Calculate the number of newlines we need to add.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the unwrapped
      line.
    indent_depth: (int) The line's indentation depth.
    prev_uwline: (list of unwrapped_line.UnwrappedLine) The unwrapped line
      previous to this line.
    final_lines: (list of unwrapped_line.UnwrappedLine) The unwrapped lines
      that have already been processed.

  Returns:
    The number of newlines needed before the first token.
  """
  # TODO(morbo): Special handling for imports.
  # TODO(morbo): Create a knob that can tune these.
  if prev_uwline is None:
    # The first line in the file. Don't add blank lines.
    # FIXME(morbo): Is this correct?
    if first_token.newlines is not None:
      pytree_utils.SetNodeAnnotation(first_token.node,
                                     pytree_utils.Annotation.NEWLINES, None)
    return 0

  if first_token.is_docstring:
    if (prev_uwline.first.value == 'class' and
        style.Get('BLANK_LINE_BEFORE_CLASS_DOCSTRING')):
      # Enforce a blank line before a class's docstring.
      return ONE_BLANK_LINE
    elif (prev_uwline.first.value.startswith('#') and
          style.Get('BLANK_LINE_BEFORE_MODULE_DOCSTRING')):
      # Enforce a blank line before a module's docstring.
      return ONE_BLANK_LINE
    # The docstring shouldn't have a newline before it.
    return NO_BLANK_LINES

  prev_last_token = prev_uwline.last
  if prev_last_token.is_docstring:
    if (not indent_depth and first_token.value in {'class', 'def', 'async'}):
      # Separate a class or function from the module-level docstring with
      # appropriate number of blank lines.
      return 1 + style.Get('BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION')
    if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                       prev_last_token):
      return NO_BLANK_LINES
    else:
      return ONE_BLANK_LINE

  if first_token.value in {'class', 'def', 'async', '@'}:
    # TODO(morbo): This can go once the blank line calculator is more
    # sophisticated.
    if not indent_depth:
      # This is a top-level class or function.
      is_inline_comment = prev_last_token.whitespace_prefix.count('\n') == 0
      if (not prev_uwline.disable and prev_last_token.is_comment and
          not is_inline_comment):
        # This token follows a non-inline comment.
        if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                           prev_last_token):
          # Assume that the comment is "attached" to the current line.
          # Therefore, we want two blank lines before the comment.
          index = len(final_lines) - 1
          while index > 0:
            if not final_lines[index - 1].is_comment:
              break
            index -= 1
          if final_lines[index - 1].first.value == '@':
            final_lines[index].first.AdjustNewlinesBefore(NO_BLANK_LINES)
          else:
            prev_last_token.AdjustNewlinesBefore(
                1 + style.Get('BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION'))
          if first_token.newlines is not None:
            pytree_utils.SetNodeAnnotation(first_token.node,
                                           pytree_utils.Annotation.NEWLINES,
                                           None)
          return NO_BLANK_LINES
    elif _IsClassOrDef(prev_uwline):
      if not style.Get('BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'):
        pytree_utils.SetNodeAnnotation(first_token.node,
                                       pytree_utils.Annotation.NEWLINES, None)
        return NO_BLANK_LINES

  # Calculate how many newlines were between the original lines. We want to
  # retain that formatting if it doesn't violate one of the style guide rules.
  if first_token.is_comment:
    first_token_lineno = first_token.lineno - first_token.value.count('\n')
  else:
    first_token_lineno = first_token.lineno

  prev_last_token_lineno = prev_last_token.lineno
  if prev_last_token.is_multiline_string:
    prev_last_token_lineno += prev_last_token.value.count('\n')

  if first_token_lineno - prev_last_token_lineno > 1:
    return ONE_BLANK_LINE

  return NO_BLANK_LINES


def _SingleOrMergedLines(uwlines):
  """Generate the lines we want to format.

  Arguments:
    uwlines: (list of unwrapped_line.UnwrappedLine) Lines we want to format.

  Yields:
    Either a single line, if the current line cannot be merged with the
    succeeding line, or the next two lines merged into one line.
  """
  index = 0
  last_was_merged = False
  while index < len(uwlines):
    if uwlines[index].disable:
      uwline = uwlines[index]
      index += 1
      while index < len(uwlines):
        column = uwline.last.column + 2
        if uwlines[index].lineno != uwline.lineno:
          break
        if uwline.last.value != ':':
          leaf = pytree.Leaf(
              type=token.SEMI, value=';', context=('', (uwline.lineno, column)))
          uwline.AppendToken(format_token.FormatToken(leaf))
        for tok in uwlines[index].tokens:
          uwline.AppendToken(tok)
        index += 1
      yield uwline
    elif line_joiner.CanMergeMultipleLines(uwlines[index:], last_was_merged):
      # TODO(morbo): This splice is potentially very slow. Come up with a more
      # performance-friendly way of determining if two lines can be merged.
      next_uwline = uwlines[index + 1]
      for tok in next_uwline.tokens:
        uwlines[index].AppendToken(tok)
      if (len(next_uwline.tokens) == 1 and
          next_uwline.first.is_multiline_string):
        # This may be a multiline shebang. In that case, we want to retain the
        # formatting. Otherwise, it could mess up the shell script's syntax.
        uwlines[index].disable = True
      yield uwlines[index]
      index += 2
      last_was_merged = True
    else:
      yield uwlines[index]
      index += 1
      last_was_merged = False


def _NoBlankLinesBeforeCurrentToken(text, cur_token, prev_token):
  """Determine if there are no blank lines before the current token.

  The previous token is a docstring or comment. The prev_token_lineno is the
  start of the text of that token. Counting the number of newlines in its text
  gives us the extent and thus where the line number of the end of the
  docstring or comment. After that, we just compare it to the current token's
  line number to see if there are blank lines between them.

  Arguments:
    text: (unicode) The text of the docstring or comment before the current
      token.
    cur_token: (format_token.FormatToken) The current token in the unwrapped
      line.
    prev_token: (format_token.FormatToken) The previous token in the unwrapped
      line.

  Returns:
    True if there is no blank line before the current token.
  """
  cur_token_lineno = cur_token.lineno
  if cur_token.is_comment:
    cur_token_lineno -= cur_token.value.count('\n')
  num_newlines = text.count('\n') if not prev_token.is_comment else 0
  return prev_token.lineno + num_newlines == cur_token_lineno - 1

#!/usr/bin/env python3

"""
 Program: Generate a Markdown commit history from the repository's local branches.
    Name: Andrew Dixon            File: Gen-Repo-Stats.py
    Date: 25 Oct 2026
   Notes: With parameter flags, include all commits reachable from local branches except
          the initial repository commit. Either history flag overrides that omission.
          The report lists every local branch and its full reachable commit count, the
          active branch, the distinct total across local branches, and the selected
          commits in oldest-first topological order. Development time spans the earliest
          and latest author dates in the selected report. Git reads the repository
          from the caller's working directory.

   Flags:
    --branch NAME   Include commits reachable from the named local branch,
                    including commits brought in by merges.
    --commit HASH   Include this commit and its descendants reachable from the
                    selected branch, or from any local branch without --branch.
    --output PATH   Write to PATH instead of Commit-History.md in the current
                    working directory.

  Copyright (c) 2026 Andrew Dixon

  This file is part of Useful_Scripts.
  Licensed under the GNU Lesser General Public License v2.1.
  See the LICENSE file at the project root for details.
........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1
"""

from typing import Literal

import argparse
import calendar
from collections import defaultdict, deque
from datetime import date, datetime
from pathlib import Path
import re
import subprocess


def main():
  """Parse report options, select commits, and write the requested file."""

  # Preserve the module header in --help because it documents the default
  # scope and the meaning of each selection flag in more detail than the
  # short per-option help strings can.
  parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
  )

  parser.add_argument('--branch', help='Report history reachable from this local branch')
  parser.add_argument('--commit', help='Include this commit and its descendants')
  parser.add_argument(
    '--output',
    type=Path,
    default=Path.cwd() / 'Commit-History.md',
    help='Markdown output path (default: ./Commit-History.md)',
  )
  args = parser.parse_args()

  try:
    # Work only with local branch refs. Counts and the distinct total describe
    # the whole local repository even when the report is narrowed to one branch.
    branches = local_branches()

    if not branches:
      raise ValueError('No local branches found')

    if args.branch and args.branch not in branches:
      raise ValueError(f'Not a local branch: {args.branch}')

    selected_branches = [args.branch] if args.branch else branches
    branch_counts = {branch: len(commit_list(branch)) for branch in branches}
    # Set membership prevents commits shared by several branches from inflating
    # the repository total or appearing more than once in the selected report.
    all_commits = set(commit_list(*branches))
    active_branch = git('symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()

    # Selection begins with everything reachable from the requested branch(es).
    # The optional anchor and default initial-commit rule refine that set below.
    selected = set(commit_list(*selected_branches))
    scope = f'branch `{args.branch}`' if args.branch else 'all local branches'

    if args.commit:
      # Validate the spelling before passing user input to Git, then resolve
      # abbreviated hashes to the full commit ID used by rev-list and log.
      if not re.fullmatch(r'[0-9a-fA-F]{4,40}', args.commit):
        raise ValueError('--commit must be a Git commit hash')

      anchor = git('rev-parse', '--verify', f'{args.commit}^{{commit}}').decode().strip()

      if anchor not in selected:
        raise ValueError('The requested commit is not reachable from the selected branch(es)')

      # A commit's descendants cannot be found by following its parent links
      # directly. Build the parent graph, reverse it in descendants_of(), and
      # intersect the result with the already selected branch history.
      graph = commit_list('--parents', *selected_branches)
      parents_by_commit = {parts[0]: parts[1:] for parts in (line.split() for line in graph)}
      selected &= descendants_of(anchor, parents_by_commit)
      scope += f' from `{anchor[:7]}` (inclusive)'

    elif not args.branch:
      # With no explicit history flag, omit one initial repository commit. A
      # graph can have multiple roots; choose the earliest by author timestamp
      # to identify the initial commit used by this report's default scope.
      roots = set(commit_list('--max-parents=0', *selected_branches))
      initial = min(roots, key=lambda commit: int(git('show', '-s', '--format=%at', commit)))
      selected.discard(initial)
      scope += ' (initial commit omitted)'

    # Read Git's topological order once, then filter it by the chosen hashes.
    # Filtering here retains Git's ordering across merges in the final table.
    records = [record for record in commit_records(selected_branches) if record[0] in selected]

    if not records:
      raise ValueError('No commits match the requested report')

    report = make_report(branches, branch_counts, active_branch, len(all_commits), records, scope)

    # The path is intentionally relative to the caller when --output is given;
    # the default was made absolute from the caller's working directory above.
    args.output.write_text(report, encoding='utf-8')

  except (OSError, ValueError) as error:
    parser.exit(1, f'error: {error}\n')

  noun: Literal['commit', 'commits'] = 'commit' if len(records) == 1 else 'commits'
  print(f'Wrote {len(records)} {noun} to {args.output}')


def git(*args):
  """Run Git from the caller's working directory and return its output."""

  # Capture stderr so failed Git lookups become concise report errors instead
  # of leaving a partial traceback or mixing diagnostics with Git data.
  result = subprocess.run(
    ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
  )

  if result.returncode:
    raise ValueError(result.stderr.decode('utf-8', errors='replace').strip())

  return result.stdout


def commit_list(*revisions):
  """Return hashes or parent records from git rev-list for the revisions."""

  # The caller chooses rev-list options: plain output supplies hashes, while
  # --parents supplies one commit followed by its parent hashes on each line.
  return git('rev-list', *revisions).decode('ascii').splitlines()


def local_branches():
  """Return the names of local branches, excluding remote-tracking refs."""

  # refs/heads excludes remotes and tags; the short form is suitable both for
  # Git revision arguments and the branch labels in the report.
  names = git('for-each-ref', '--format=%(refname:short)', 'refs/heads')

  return names.decode('utf-8').splitlines()


def commit_records(revisions):
  """Return commit metadata and messages in oldest-first topological order."""

  # Topological order keeps parent commits ahead of descendants when reversed,
  # including histories with merges. NUL delimiters keep multiline bodies from
  # being mistaken for new records or fields.
  # -z terminates each record; the format's NULs separate its five fields.
  raw = git(
    'log', '-z', '--topo-order', '--reverse', '--format=%H%x00%aI%x00%an%x00%s%x00%b', *revisions
  )

  fields = raw.decode('utf-8', errors='replace').split('\x00')

  if fields[-1] == '':
    fields.pop()

  # Every record must have hash, author date, author, subject, and body. An
  # incomplete group signals that the Git output was not parsed as expected.
  if len(fields) % 5:
    raise ValueError('Could not parse the Git commit history')

  return [fields[index : index + 5] for index in range(0, len(fields), 5)]


def descendants_of(anchor, parents_by_commit):
  """Find the anchor and its descendants within the selected commit graph."""

  # rev-list gives edges from child to parent. Reverse those edges to walk
  # forward through history from the requested anchor, including both sides
  # of merges where they are reachable from the selected branch(es).
  children = defaultdict(list)

  for commit, parents in parents_by_commit.items():
    for parent in parents:
      children[parent].append(commit)

  descendants = {anchor}
  pending = deque([anchor])

  # Track visited commits so shared descendants are returned once and the
  # queue does not revisit nodes reached by more than one ancestry path.
  while pending:
    for child in children[pending.popleft()]:
      if child not in descendants:
        descendants.add(child)
        pending.append(child)

  return descendants


def add_months(start, months):
  """Advance a calendar date by whole months, clipping to the last day."""

  # Use a zero-based month index so year rollover is handled by divmod. If
  # the target month is shorter, keep the date on its final valid day.
  month_index = start.year * 12 + start.month - 1 + months
  year, month_zero = divmod(month_index, 12)
  month = month_zero + 1
  day = min(start.day, calendar.monthrange(year, month)[1])

  return date(year, month, day)


def calendar_duration(start, end):
  """Express the date span as whole years, months, and remaining days."""

  # Start with the difference in calendar months. Subtract one when advancing
  # that many months would pass the end date, then count leftover whole days.
  months = (end.year - start.year) * 12 + end.month - start.month

  if add_months(start, months) > end:
    months -= 1

  days = (end - add_months(start, months)).days
  years, remaining_months = divmod(months, 12)

  return f'{years} years, {remaining_months} months, {days} days'


def markdown_cell(value):
  """Keep a text value inside one Markdown table cell, preserving newlines."""

  # Normalize line endings before turning line breaks into HTML breaks. Escape
  # pipes because an unescaped pipe would create another Markdown column.
  return (
    value.strip()
    .replace('\r\n', '\n')
    .replace('\r', '\n')
    .replace('|', '\\|')
    .replace('\n', '<br>')
  )


def make_report(branches, branch_counts, active_branch, total_count, records, scope):
  """Render branch statistics and selected commit records as Markdown."""

  # The displayed span uses author dates from commits actually in the report;
  # branch counts and repository total above still cover all local branches.
  dates = [datetime.fromisoformat(record[1]).date() for record in records]
  duration = calendar_duration(min(dates), max(dates))

  # Build complete Markdown rows in order, leaving explicit blank lines around
  # headings so the result renders consistently in common Markdown viewers.
  lines = [
    '# Commit History',
    '',
    '## Repo Stats',
    '',
    '| | |',
    '| --- | --- |',
    f'| Active branch: | `{active_branch}` |',
    f'| Total commits across all local branches: | {total_count} |',
    f'| Report scope: | {scope} |',
    f'| Commits in report: | {len(records)} |',
    f'| Total development time: | {duration} ({min(dates)} to {max(dates)}, author dates) |',
    '',
    '## Local branches',
    '',
    '| Local branch | Commits |',
    '| --- | ---: |',
  ]

  lines.extend(f'| `{markdown_cell(branch)}` | {branch_counts[branch]} |' for branch in branches)

  lines.extend(
    [
      '',
      '## Commit history',
      '',
      '| Short hash | Date | Author | Title | Commit description |',
      '| --- | --- | --- | --- | --- |',
    ]
  )

  for commit_hash, author_date, author, title, description in records:
    # Show a compact hash for reading while preserving every author and message
    # field inside its table cell, including multiline commit descriptions.
    lines.append(
      f'| `{commit_hash[:7]}` | {datetime.fromisoformat(author_date).date()} | '
      f'{markdown_cell(author)} | {markdown_cell(title)} | {markdown_cell(description)} |'
    )

  return '\n'.join(lines) + '\n'


if __name__ == '__main__':
  main()

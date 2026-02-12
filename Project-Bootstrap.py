#!/usr/bin/env python3

"""
 Program: ProjectBootstrap
    Name: Andrew Dixon            File: projectBootstrap.py
    Date: 11 Feb 2026
   Notes: Scripting to import/replace uv default files so I do not have to do it by hand.
   TODO: Add comments and clean up code. Large swaths of this are basically AI generated and only briefly tested.

  Copyright (c) 2026 Andrew Dixon

   This file is part of Useful_Scripts.
   Licensed under the GNU Lesser General Public License v2.1.
   See the LICENSE file at the project root for details.

........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1.........2.........3..
"""


from __future__ import annotations

import os
import re
import shutil
import argparse
import datetime
import platform
import subprocess
from pathlib import Path
from typing import Any, Callable


TemplateType = dict[str, Any]
SpecialParserType = Callable[[list[str], TemplateType], list[str]]

pythonVersionRaw: str = ''
pythonVersionMajor: int = 0
pythonVersionMinor: int = 0
pythonVersionPatch: int | None = None


def main() -> int:
  parser = argparse.ArgumentParser(
    description='Apply embedded templates to a uv project, optionally copying global defaults, with per-file parsing.'
  )
  parser.add_argument(
    '--dry-run',
    '--dryrun',
    action='store_true',
    help='Show actions without writing files.'
  )
  parser.add_argument(
    '--force',
    action='store_true',
    help='Overwrite files even if they already exist.'
  )

  args = parser.parse_args()

  projectDirPath: Path = Path.cwd()
  assertUvLikeProject(projectDirPath)
  loadPythonVersion(projectDirPath)

  processTemplates(
    projectDirPath=projectDirPath,
    templatesList=EMBEDDED_TEMPLATES,
    dryRun=bool(args.dry_run),
    cliForce=bool(args.force),
  )

  return 0


def assertUvLikeProject(projectDirPath: Path) -> None:
  requiredPaths = [projectDirPath / 'pyproject.toml', projectDirPath / '.python-version']

  missingNames = [pathObj.name for pathObj in requiredPaths if not pathObj.exists()]
  if missingNames:
    raise SystemExit(
      'Refusing to run: this does not look like a uv project root.\n'
      f'Missing: {", ".join(missingNames)}\n'
      f'Current directory: {projectDirPath}'
    )


def loadPythonVersion(projectDirPath: Path) -> None:
  global pythonVersionRaw
  global pythonVersionMajor
  global pythonVersionMinor
  global pythonVersionPatch

  pythonVersionPath: Path = projectDirPath / '.python-version'
  pythonVersionRaw = pythonVersionPath.read_text(encoding='utf-8').strip()

  matchObj: re.Match[str] | None = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', pythonVersionRaw)
  if not matchObj:
    raise RuntimeError(f'Could not parse .python-version content: {pythonVersionRaw!r}')

  pythonVersionMajor = int(matchObj.group(1))
  pythonVersionMinor = int(matchObj.group(2))
  pythonVersionPatch = int(matchObj.group(3)) if matchObj.group(3) is not None else None


def pythonVersionUpdate(style: str) -> str:
  majorVersion: int = pythonVersionMajor
  minorVersion: int = pythonVersionMinor
  patchVersion: int | None = pythonVersionPatch

  if style == 'majorMinor':
    return f'{majorVersion}.{minorVersion}'

  if style == 'majorMinorPatch':
    if patchVersion is None:
      return f'{majorVersion}.{minorVersion}'

    return f'{majorVersion}.{minorVersion}.{patchVersion}'

  if style == 'ruffTarget':
    return f'py{majorVersion}{minorVersion:02d}'

  if style == 'noDot':
    return f'{majorVersion}{minorVersion:02d}'

  if style == 'cpythonTag':
    return f'cp{majorVersion}{minorVersion:02d}'

  raise ValueError(f'Unknown version style: {style!r}')


def expandUserPath(pathText: str) -> Path:
  expandedText: str = os.path.expandvars(os.path.expanduser(pathText))

  return Path(expandedText)


def readLines(pathObj: Path) -> list[str]:
  return pathObj.read_text(encoding='utf-8').splitlines(keepends=True)


def normalizeLines(linesList: list[str]) -> list[str]:
  if not linesList:
    return ['\n']

  normalizedList: list[str] = []
  for line in linesList:
    normalizedList.append(line if line.endswith('\n') else line + '\n')

  if not normalizedList[-1].endswith('\n'):
    normalizedList[-1] = normalizedList[-1] + '\n'

  return normalizedList


def embeddedToLines(embeddedConfig: Any) -> list[str]:
  if isinstance(embeddedConfig, str):
    return normalizeLines(embeddedConfig.splitlines(keepends=True))

  if isinstance(embeddedConfig, (list, tuple)):
    return normalizeLines([str(lineObj) for lineObj in embeddedConfig])

  raise TypeError('embeddedConfig must be a string, list, or tuple')


def findGlobalDefault(templateObj: TemplateType) -> Path | None:
  globalDefaults = templateObj.get('globalDefaults', {})
  systemName: str = platform.system()

  defaultPathText = globalDefaults.get(systemName)
  if not defaultPathText:
    return None

  defaultPath = expandUserPath(str(defaultPathText))
  if defaultPath.exists() and defaultPath.is_file():
    return defaultPath

  return None


def sanitizeOutputPath(outputPathText: str) -> Path:
  # - If "~" appears anywhere OR any ".." traversal appears, drop to project root.
  if '~' in outputPathText:
    return Path('.')

  rawPath = Path(outputPathText)

  for part in rawPath.parts:
    if part == '..':
      return Path('.')

  # Treat absolute paths as relative under project root by stripping anchor/root.
  if rawPath.is_absolute():
    relativeParts: list[str] = list(rawPath.parts)

    if relativeParts:
      relativeParts: list[str] = relativeParts[1:]

    return Path(*relativeParts) if relativeParts else Path('.')

  # Also strip leading "./" noise naturally
  return rawPath


def upsertRuffTargetVersion(linesList: list[str]) -> list[str]:
  # Insert/replace an active target-version setting.
  desiredLine = f'target-version = "{pythonVersionUpdate("ruffTarget")}"'
  activeRegex: re.Pattern[str] = re.compile(r'^\s*target-version\s*=\s*"[^"]*"\s*$')

  linesList = normalizeLines(linesList)

  for index, line in enumerate(linesList):
    if activeRegex.match(line.strip()):
      linesList[index] = desiredLine + '\n'
      return linesList

  anchorRegex: re.Pattern[str] = re.compile(r'^\s*(line-length|indent-width)\s*=\s*')

  lastAnchorIndex = None
  for index, line in enumerate(linesList):
    if anchorRegex.search(line):
      lastAnchorIndex: int = index

  insertIndex = 0
  if lastAnchorIndex is not None:
    insertIndex: int = lastAnchorIndex + 1

    if insertIndex < len(linesList) and linesList[insertIndex].strip() != '':
      linesList.insert(insertIndex, '\n')
      insertIndex += 1

  else:
    for index, line in enumerate(linesList):
      strippedLine: str = line.strip()

      if strippedLine.startswith('#') or strippedLine == '':
        continue

      insertIndex: int = index
      break

  linesList.insert(insertIndex, desiredLine + '\n')

  return linesList


def upsertTyEnvironmentPythonVersion(linesList: list[str]) -> list[str]:
  desiredLine = f'python-version = "{pythonVersionUpdate("majorMinor")}"'
  sectionHeaderRegex: re.Pattern[str] = re.compile(r'^\s*\[environment\]\s*$')
  anySectionHeaderRegex: re.Pattern[str] = re.compile(r'^\s*\[[^\]]+\]\s*$')
  keyRegex: re.Pattern[str] = re.compile(r'^\s*python-version\s*=\s*"[^"]*"\s*$')

  linesList: list[str] = normalizeLines(linesList)

  sectionStartIndex = None
  for index, line in enumerate(linesList):
    if sectionHeaderRegex.match(line):
      sectionStartIndex: int = index
      break

  if sectionStartIndex is None:
    prefix = ['[environment]\n', desiredLine + '\n', '\n']
    return prefix + linesList

  sectionEndIndex: int = len(linesList)
  for index in range(sectionStartIndex + 1, len(linesList)):
    if anySectionHeaderRegex.match(linesList[index]):
      sectionEndIndex: int = index
      break

  sectionSlice: list[str] = linesList[sectionStartIndex:sectionEndIndex]

  replaced = False
  for localIndex, line in enumerate(sectionSlice):
    if keyRegex.match(line.strip()):
      sectionSlice[localIndex] = desiredLine + '\n'
      replaced = True
      break

  if not replaced:
    sectionSlice.insert(1, desiredLine + '\n')

  # Ensure a blank line before the next section header
  while sectionSlice and sectionSlice[-1] == '\n':
    sectionSlice.pop()
  sectionSlice.append('\n')
  sectionSlice.append('\n')

  return linesList[:sectionStartIndex] + sectionSlice + linesList[sectionEndIndex:]


def parseRuffTemplate(linesList: list[str], templateObj: TemplateType) -> list[str]:
  return upsertRuffTargetVersion(linesList)


def parseTyTemplate(linesList: list[str], templateObj: TemplateType) -> list[str]:
  return upsertTyEnvironmentPythonVersion(linesList)


def parseMainPyTemplate(linesList: list[str], templateObj: TemplateType) -> list[str]:
  projectDirPath = Path.cwd()

  replacements = {
    'project' : getProjectName(projectDirPath),
    'description': getProjectName(projectDirPath),
    'author': getUserName(),
    'date': formatDateForHeader(datetime.date.today()),
    'filename': Path(templateObj.get('fileName', '')).name,
  }

  updatedLines = replaceTemplateKeys(linesList, replacements)

  # Normalize first-line shebang if present
  if updatedLines:
    updatedLines[0] = normalizeMainShebang(updatedLines[0])

  return updatedLines


def writeFileIfNeeded(outputFilePath: Path, linesList: list[str],
                        effectiveForce: bool, dryRun: bool) -> bool:

  if outputFilePath.exists() and not effectiveForce:
    return False

  contentText: str = ''.join(normalizeLines(linesList))

  if dryRun:
    return True

  outputFilePath.write_text(contentText, encoding='utf-8')
  return True


def getProjectName(projectDirPath: Path) -> str:
  folderName = projectDirPath.name

  if not folderName:
    return ''

  return folderName[0].upper() + folderName[1:]


def formatDateForHeader(dateObj: datetime.date) -> str:
  # "D Mon YYYY" (no leading zero on day)
  return f'{dateObj.day} {dateObj.strftime("%b")} {dateObj.year}'


def runCommandCapture(commandParts: list[str]) -> str:
  try:
    resultObj = subprocess.run(
      commandParts, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False
    )

  except Exception:
    return ''

  if resultObj.returncode != 0:
    return ''

  return (resultObj.stdout or '').strip()


def getUserNameFromGit() -> str:
  gitPath = shutil.which('git')
  if not gitPath:
    return ''

  nameText = runCommandCapture([gitPath, 'config', '--global', 'user.name'])
  return nameText.strip()


def getUserNameFromGh() -> str:
  ghPath = shutil.which('gh')
  if not ghPath:
    return ''

  # Prefer the human name; fallback to login if name isn't set.
  nameText = runCommandCapture([ghPath, 'api', 'user', '-q', '.name'])
  if nameText:
    return nameText.strip()

  loginText = runCommandCapture([ghPath, 'api', 'user', '-q', '.login'])

  return loginText.strip()


def getUserName() -> str:
  nameText = getUserNameFromGit()
  if nameText:
    return nameText

  nameText = getUserNameFromGh()
  if nameText:
    return nameText

  return ''


def normalizeMainShebang(lineText: str) -> str:
  strippedText = lineText.strip()

  if strippedText.startswith(r'#!') and '/usr/bin/env' in strippedText and 'python3' in strippedText:
    return '#!/usr/bin/env python3\n'

  return lineText if lineText.endswith('\n') else lineText + '\n'


def x_replaceTemplateKeys(linesList: list[str], replacements: dict[str, str]) -> list[str]:
  # Replace ${key} occurrences everywhere; unknown keys are left as-is.
  updatedLines: list[str] = []
  keyRegex = re.compile(r'\#\{([A-Za-z0-9_]+)\}')

  for rawLine in normalizeLines(linesList):
    lineText = rawLine

    def replaceMatch(matchObj: re.Match[str]) -> str:
      keyName = matchObj.group(1)
      return replacements.get(keyName, matchObj.group(0))

    lineText = keyRegex.sub(replaceMatch, lineText)
    updatedLines.append(lineText)

  return updatedLines


def replaceTemplateKeys(linesList: list[str], replacements: dict[str, str]) -> list[str]:
  updatedLines: list[str] = []
  keyRegex: re.Pattern[str] = re.compile(r'#\{([A-Za-z0-9_]+)\}')

  for rawLine in normalizeLines(linesList):
    lineText: str = rawLine

    def replaceMatch(matchObj: re.Match[str]) -> str:
      keyName = matchObj.group(1)
      replacementText: str = replacements.get(keyName, matchObj.group(0))

      # Special case: avoid filename.ext.ext when template does "#{filename}.py"
      if keyName == 'filename' and replacementText:
        # startIndex: int = matchObj.start()
        endIndex: int = matchObj.end()
        suffixText: str = lineText[endIndex:]
        extMatch: re.Match[str] | None = re.match(r'(\.[A-Za-z0-9]+)', suffixText)

        if extMatch:
          extText = extMatch.group(1)

          if replacementText.endswith(extText):
            return Path(replacementText).stem

      return replacementText

    lineText: str = keyRegex.sub(replaceMatch, lineText)
    updatedLines.append(lineText)

  return updatedLines


def processTemplates(
  projectDirPath: Path, templatesList: tuple[TemplateType, ...], dryRun: bool, cliForce: bool) -> None:
  for templateObj in templatesList:
    fileName = str(templateObj['fileName'])
    outputPathText = str(templateObj.get('outputPath', './'))
    templateForce = bool(templateObj.get('force', False))
    effectiveForce = bool(cliForce or templateForce)

    safeOutputDirRel = sanitizeOutputPath(outputPathText)
    outputDirPath = (projectDirPath / safeOutputDirRel).resolve()
    globalDefaultPath = findGlobalDefault(templateObj)

    if globalDefaultPath:
      sourceLines = readLines(globalDefaultPath)
      sourceLabel = f'global default {globalDefaultPath}'

    else:
      sourceLines = embeddedToLines(templateObj.get('embeddedConfig', ()))
      sourceLabel = 'embedded config'

    specialParser = templateObj.get('specialParser')
    if callable(specialParser):
      sourceLines = specialParser(sourceLines, templateObj)

    outputDirPath.mkdir(parents=True, exist_ok=True)
    outputFilePath = outputDirPath / fileName

    wrote = writeFileIfNeeded(
      outputFilePath=outputFilePath,
      linesList=sourceLines,
      effectiveForce=effectiveForce,
      dryRun=dryRun,
    )

    prefixText = '[DRY RUN] ' if dryRun else ''
    if wrote:
      actionText = 'Would write' if dryRun else 'Wrote'
      forceText = ' (forced)' if effectiveForce and outputFilePath.exists() else ''
      print(f'{prefixText}{actionText}: {outputFilePath} from {sourceLabel}{forceText}')

    else:
      print(f'{prefixText}Skipped (exists): {outputFilePath}')

# Embeded template configuration and embeded templates to output.
EMBEDDED_TEMPLATES: tuple[TemplateType, ...] = (
  {
    'fileName': 'ruff.toml',
    'outputPath': './',
    'force': False,
    'globalDefaults': {
      'Darwin': '~/.config/ruff/ruff.toml',
      'Linux': '~/.config/ruff/ruff.toml',
      'Windows': r'%APPDATA%\ruff\ruff.toml',
    },
    'embeddedConfig': (
      '# Exclude a variety of commonly ignored directories.',
      'exclude = [',
      '    ".bzr",',
      '    ".direnv",',
      '    ".eggs",',
      '    ".git",',
      '    ".git-rewrite",',
      '    ".hg",',
      '    ".ipynb_checkpoints",',
      '    ".mypy_cache",',
      '    ".nox",',
      '    ".pants.d",',
      '    ".pyenv",',
      '    ".pytest_cache",',
      '    ".pytype",',
      '    ".ruff_cache",',
      '    ".svn",',
      '    ".tox",',
      '    ".venv",',
      '    ".vscode",',
      '    "__pypackages__",',
      '    "_build",',
      '    "buck-out",',
      '    "build",',
      '    "dist",',
      '    "node_modules",',
      '    "site-packages",',
      '    "venv",',
      ']',
      '',
      '# Same as Black.',
      'line-length = 100',
      'indent-width = 2',
      '',
      '# target-version = ',
      '',
      '[lint]',
      'select = ["E1", "E4", "E7", "E9", "F", "W", "B"]',
      'ignore = []',
      '',
      'fixable = ["ALL"]',
      'unfixable = ["B"]',
      '',
      'dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"',
      '',
      '[format]',
      'quote-style = "single"',
      'indent-style = "space"',
      'skip-magic-trailing-comma = true',
      'line-ending = "auto"',
      'docstring-code-format = true',
      'docstring-code-line-length = "dynamic"',
    ),
    'specialParser': parseRuffTemplate,
  },
  {
    'fileName': 'ty.toml',
    'outputPath': './',
    'force': False,
    'globalDefaults': {
      'Darwin': '~/.config/ty/ty.toml',
      'Linux': '~/.config/ty/ty.toml',
      'Windows': r'%APPDATA%\ty\ty.toml',
    },
    'embeddedConfig': (
      '# ty.toml',
      '# Portable "sane defaults" for solo dev projects:',
      '# - Respect .gitignore by default',
      '# - Exclude common junk/venvs/build output explicitly',
      '# - Keep diagnostics as warnings unless you choose otherwise',
      '',
      '[src]',
      '# include = ["src", "tests"]',
      '',
      'exclude = [',
      '  ".bzr",',
      '  ".direnv",',
      '  ".eggs",',
      '  ".git",',
      '  ".git-rewrite",',
      '  ".hg",',
      '  ".ipynb_checkpoints",',
      '  ".mypy_cache",',
      '  ".nox",',
      '  ".pants.d",',
      '  ".pyenv",',
      '  ".pytest_cache",',
      '  ".pytype",',
      '  ".ruff_cache",',
      '  ".svn",',
      '  ".tox",',
      '  ".venv",',
      '  ".vscode",',
      '  "__pypackages__",',
      '  "_build",',
      '  "buck-out",',
      '  "build",',
      '  "dist",',
      '  "node_modules",',
      '  "site-packages",',
      '  "venv",',
      ']',
      '',
      '[environment]',
      '# Keep this aligned with whatever you target in Ruff / your runtime.',
      '# python-version = "3.14"',
      '',
      '[terminal]',
      'error-on-warning = false',
      '',
      '[rules]',
      'all = "warn"',
    ),
    'specialParser': parseTyTemplate,
  },
  {
    'fileName': 'main.py',
    'outputPath': './',
    'force': True,
    'globalDefaults': {
      'Darwin': '~/Library/Application Support/Code/User/FileTemplates/python-basic.py',
      'Linux': '~/.config/Code/User/FileTemplates/python-basic.py',
      'Windows': r'%APPDATA%\Roaming\Code\User\FileTemplates/python-basic.py',
    },
    'embeddedConfig': (
      r'#! /usr/bin/env python3',
      '',
      r"'''",
      ' Program: #{description}',
      '    Name: #{author}            File: #{filename}',
      '    Date: #{date}',
      '   Notes:',
      '........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1.........2.........3..',
      r"'''",
      '',
      'import atexit',
      '',
      "SYMBOLS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'",
      "SYMBOLS = SYMBOLS + SYMBOLS.lower() + '1234567890 !?.'",
      '',
      'def main() -> None:',
      '  # Code Beginning ----',
      '  msg = "Hello World!"',
      '  oprs = [msg.lower, msg.upper, msg.capitalize, msg.swapcase, msg.title]',
      '',
      '  for m in oprs:',
      '    print(m())',
      '',
      '# Make sure we clean up anything we need to do if someone aborts the script',
      'def onExit() -> None:',
      '  try:',
      '    # Try and do any clean up, error check as necessary',
      '    pass',
      '  except Exception:',
      '    # Deal with errors, or just ignore them by leaving this as "pass"',
      '    pass',
      '  return',
      '',
      '# If the hello.py is run (instead of imported as a module),',
      '# call the main() function:',
      "if __name__ == '__main__':",
      '# Register the function to execute on ending the script',
      '  atexit.register(onExit)',
      '  main()',
    ),
    'specialParser': parseMainPyTemplate,
  },
  {
    'fileName': '.gitignore',
    'outputPath': './',
    'force': True,
    'globalDefaults': {
      'Darwin': None,
      'Linux': None,
      'Windows': None
    },
    'embeddedConfig': (
      '#',
      '#  Program: gitignore file for #{project}',
      '#     Name: #{author}            File: .gitignore',
      '#     Date: #{date}',
      '#    Notes:',
      '#',
      '# ........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1.........2.........3..',
      '',
      '# Byte-compiled / optimized / DLL files',
      '__pycache__/',
      '*.py[cod]',
      '*$py.class',
      '',
      '# C extensions',
      '*.so',
      '',
      '# Distribution / packaging',
      '.Python',
      'build/',
      'develop-eggs/',
      'dist/',
      'downloads/',
      'eggs/',
      '.eggs/',
      'lib/',
      'lib64/',
      'parts/',
      'sdist/',
      'var/',
      'wheels/',
      'share/python-wheels/',
      '*.egg-info/',
      '.installed.cfg',
      '*.egg',
      'MANIFEST',
      '',
      '# PyInstaller',
      '#  Usually these files are written by a python script from a template',
      '#  before PyInstaller builds the exe, so as to inject date/other infos into it.',
      '*.manifest',
      '*.spec',
      '',
      '# Installer logs',
      'pip-log.txt',
      'pip-delete-this-directory.txt',
      '',
      '# Unit test / coverage reports',
      'htmlcov/',
      '.tox/',
      '.nox/',
      '.coverage',
      '.coverage.*',
      '.cache',
      'nosetests.xml',
      'coverage.xml',
      '*.cover',
      '*.py,cover',
      '.hypothesis/',
      '.pytest_cache/',
      'cover/',
      '',
      '# Translations',
      '*.mo',
      '*.pot',
      '',
      '# Django stuff:',
      '*.log',
      'local_settings.py',
      'db.sqlite3',
      'db.sqlite3-journal',
      '',
      '# Flask stuff:',
      'instance/',
      '.webassets-cache',
      '',
      '# Scrapy stuff:',
      '.scrapy',
      '',
      '# Sphinx documentation',
      'docs/_build/',
      '',
      '# PyBuilder',
      '.pybuilder/',
      'target/',
      '',
      '# Jupyter Notebook',
      '.ipynb_checkpoints',
      '',
      '# IPython',
      'profile_default/',
      'ipython_config.py',
      '',
      '# pyenv',
      '#   For a library or package, you might want to ignore these files since the code is',
      '#   intended to run in multiple environments; otherwise, check them in:',
      '# .python-version',
      '',
      '# pipenv',
      '#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.',
      '#   However, in case of collaboration, if having platform-specific dependencies or dependencies',
      "#   having no cross-platform support, pipenv may install dependencies that don't work, or not",
      '#   install all needed dependencies.',
      '#Pipfile.lock',
      '',
      '# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm',
      '__pypackages__/',
      '',
      '# Celery stuff',
      'celerybeat-schedule',
      'celerybeat.pid',
      '',
      '# SageMath parsed files',
      '*.sage.py',
      '',
      '# Environments',
      '.env',
      '.venv',
      '.direnv',
      '.vscode',
      'env/',
      'venv/',
      'ENV/',
      'env.bak/',
      'venv.bak/',
      '',
      '# Spyder project settings',
      '.spyderproject',
      '.spyproject',
      '',
      '# Rope project settings',
      '.ropeproject',
      '',
      '# mkdocs documentation',
      '/site',
      '',
      '# mypy',
      '.mypy_cache/',
      '.dmypy.json',
      'dmypy.json',
      '',
      '# Ruff',
      '.ruff_cache',
      '',
      '# Pyre type checker',
      '.pyre/',
      '',
      '# pytype static type analyzer',
      '.pytype/',
      '',
      '# Cython debug symbols',
      'cython_debug/',
      '',
      '# OS Files to exclude',
      '.DS_Store',
      'Desktop.ini',
      '',
    ),
    'specialParser': parseMainPyTemplate,
  },
)

# If the projectBootstrap.py is run (instead of imported as a module),
#   call the main() function:
if __name__ == '__main__':
  # Return the exit code to the OS.
  raise SystemExit(main())

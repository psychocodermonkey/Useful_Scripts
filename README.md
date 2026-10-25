# Generally useful scripts

This repository contains generally useful Python scripts that can do a myriad of things. These are scripts that are more stand alone in nature and don't constitute having their own repository, but I wanted them easy to get access to, track changes.

## Project Bootstrap

### File

- [`Project-Bootstrap.py`](Project-Bootstrap.py)

### Description

This script is for automating the creation of a new Python project that has been initilized by `uv`. This script is to fill a need that I had to not copy my preferred settings files and starting point by hand. Since `uv` does not allow a way to override or specify versions of files, or additional files to include, this provides a way to do just that.

The bottom of this script contains a data structure that allows for additional files to be added, existing files to be overwritten with content, and/or files to be defaulted in from other locations should they exist.

I leverage [File Templates by Bruno Paz](https://marketplace.visualstudio.com/items?itemName=brpaz.file-templates) for my file templates, so the `main.py` is defaulted from a file I have at that location `python-basic.py`. (Filename can be changed in the data structure.)

### Usage

``` python
EMBEDDED_TEMPLATES: tuple[TemplateType, ...] = (
  {
    'fileName': 'some-file-to-create.file',
    'outputPath': './',
    'force': False,
    'globalDefaults': {
      'Darwin': '~/MacOS/path/for/default/file/base.file',
      'Linux': '~/Linux/path/for/default/file/base.file',
      'Windows': r'%APPDATA%\path/for\default\file/base.file',
    },
    'embeddedConfig': (
      'File Contents Here',
      'Specify lines here that should be the contents of the "created file",
    ),
    'specialParser': specialFunctionsCallable,
  },
}
```

- `fileName`
  - Contains the filename to be written out. `main.py` exists currently in the script as that is the base file that `uv` creates by default.
  - Additional files could be added if you wish to include more than just `main.py`.
- outputPath`
  - Contains the path where the file will be created. Project directory tree is enforced. No traversial allowed, traversial `~` or `..` are stripped out and the remaining path is put in place at `./`.
  - Directories missing will be automatically created, so if you want to create `src/file.py`, you can. THis will create `src` and place `file.py` inside it.
- `force`
  - This will tell the script to overwrite the file if it exists, if not it will ignore the file. This is how we overwrite `main.py` and `.gitignore` that are included in the script currently.
  - There is a `--force` flag the script takes that overwrites **ALL** files, use with cauthion.
- `globalDefaults`
  - This is the path to check for a file to be utilized for the output if found.
  - If this file does not exist, `embededConfig` is utilized instead.
  - Pathing is allowed for MacOS, Linux, and Windows.
  - If no checks need to be made replace the path with `None`, it will skip trying to copy from an outside location.
- `embeddedConfig`
  - This is the internal text to be utilized for output if no external file is found or specified.
  - Each entry in the `list` should be one line in the file.
  - This makes parsing the data easier for replacements and manipulation that may need to happen with whatever callable is specified in the `specialParser`.
- `specialParser`
  - This is a callable object whos name is specified by you.
  - This can be an external script or can be a function added by custom code within this script.
  - Coding is necessary for this to be leveraged, otherwise set this field to `None`.
  - Existing examples in the script are `parseMainPyTemplate` or `parseRuffTemplate`.
    - These example parse and replace data fields within in the templates to do date formatting, etc.

## Print Environment Path

### File

- [`Print-Environment-Path.py](Print-Environment-Path.py)

### Description

Small basic script that pulls the `$PATH` variable and prints it with line breaks from the environment.

This is a good example of leveraging `os` to get info from the environemnt.

## Wake on LAN

### File

- [`Wake-on-LAN.py`](Wake-on-LAN.py)

### Description

Script that sends a Wake-on-LAN magic packet to a machine with Wake-on-LAN enabled. After sending the packet, it can wait for the machine's SSH server to respond. A progress bar shows the configured wait period, and the script reports whether it received an SSH banner before timing out. The SSH check does not log in to the machine.

### Usage

**This script requires Python 3.14 or later.**

Modify `BROADCAST` and `SYSTEM` at the top of the script with your network's broadcast address (for example, `192.168.1.255`) and the MAC address of the machine you want to start. Use the MAC address of the network interface with Wake-on-LAN enabled, and make sure Wake-on-LAN is enabled on the machine.

Set `FQDN` to the machine's hostname or IP address to wait for SSH after sending the packet. Set it to `None` to skip the SSH check and progress bar. If SSH uses a different port, change `SSH_PORT`. Adjust `SSH_WAIT_TIMEOUT` for the expected boot time, `SSH_RETRY_INTERVAL` for how often to check SSH, and `PROGRESS_REFRESH_INTERVAL` for how often the progress bar updates. The bar uses terminal color when output is sent to a terminal.

``` bash
python3 Wake-on-LAN.py
```

## Generate Repo Statistics Report

### File

- [`Gen-Repo-Stats.py`](Gen-Repo-Stats.py)

### Description

This script generates a Markdown report of the repository's local branches and commit history. It lists the active branch, the number of commits reachable from each local branch, the total number of distinct commits across those branches, and the selected commits in oldest-first topological order. The development time shown in the report spans the earliest and latest author dates of the selected commits.

By default, the report includes commits reachable from all local branches except the initial repository commit. You can narrow the history to one branch or start at a specific commit with the flags below.

### Usage

Run the script from the command line. It reads the Git repository containing the script and writes `Commit-History.md` to your current working directory unless you specify another output path.

``` bash
python3 Gen-Repo-Stats.py
python3 Gen-Repo-Stats.py --branch BRANCH_NAME
python3 Gen-Repo-Stats.py --commit COMMIT_HASH
python3 Gen-Repo-Stats.py --branch BRANCH_NAME --commit COMMIT_HASH --output report.md
```

- `--branch BRANCH_NAME` includes commits reachable from that local branch, including commits brought in by merges.
- `--commit COMMIT_HASH` includes the named commit and its descendants reachable from the selected branch, or from any local branch when `--branch` is omitted. The commit must be reachable from the selected history.
- `--output PATH` writes the report to the specified path instead of `Commit-History.md`.

---
  Copyright (c) 2026 Andrew Dixon

  This file is part of Useful_Scripts.
  Licensed under the GNU Lesser General Public License v2.1.
  See the LICENSE file at the project root for details.

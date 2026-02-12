# Generally useful scripts

This repository contains generally useful Python scripts that can a myriad of things. These are scripts that are more stand alone in nature and don't constitute having their own repository, but I wanted them easy to get access to, track changes.

## Project Bootstrap

### File

- [`Project-Bootstrap.py`](Project-Bootstrap.py)

### Description

This script is for automating the creation of a new Python project that has been initilized by `uv`. This script is to fill a need that I had to not copy my preferred settings files and starting point by hand. Since `uv` does not allow a way to override or specify versions of files, or additional files to include, this provides a way to do just tyat.

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

Script that generates a magic pack to be broadscast to wake a machine that is wake-on-lan enabled.

### Usage

Modify `BROADCAST` and `SYSTEM` at the top of the script with the broadcast address of your network. (EX: `192.168.1.255`) and the MAC address of the machine you want to start. Be sure that the MAC address used is the MAC address that is enabled for wake-on-lan and not a secondary network interface. Be sure that wake-on-lan is enabled on the device and it is functioning.
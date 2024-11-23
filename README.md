# caiman

A build system for MicroPython applications.


## Features
- Define named targets for MicroPython sources, third party dependencies, and config resources
- Selectively tag targets for mpy compilation or freezing
- Dependency management using mip with dual install locations for development and deployment
- Maintains a build copy on your development machine for code completion
- Build code deployment to target devices using `mpremote`

## Requirements
- Python 3.9+ for local development
- MicroPython installed and added to `PATH` on your local machine 
- MicroPython installed on your target device

## Installation
1. In your development environment, install caiman in a Python virtual environment:
    
    ```bash
    pip install caiman
    ```

2. Install a MicroPython port on your development machine. 
   * If developing on a Mac, you can use brew:
   
    ```bash
    brew install micropython
    ```
   
3. Flash the MicroPython firmware on your target device.

## Initialize a new project

* Installing caiman in your local Python environment will make the `caiman` command available.
* All `caiman` commands are run from the root of your project directory.
* `caiman` is configured using a `caiman.yaml` file in the root of your project. 

Run the following command from the root of a new project directory:

```bash
caiman init
```
An interactive prompt will guide you through the setup process.
At the end, a `caiman.yaml` file will be created in the root of your project, 
together with a basic directory structure.

Your project directory should look like this:

* `caiman.yaml` the project configuration file with your build targets and project metadata.
* `build` folder. Contains the build copy of your project, together with dependency artifacts and manifest files for your targets. Add this to `.gitignore`!
* `venv/mip-packages`folder which stores local copies of your `mip` installed dependencies for code completion. Add this to `.gitignore` and to your `PYTHONPATH`. This folder will be copied over to the build folder when the build command runs.
* `venv/tools` `mip` installed dependencies for development only. Not deployed to the device. 
* `micropython` an example folder for your MicroPython source target. You can rename this folder from `caiman.yaml` or define additional source targets. Add this to `PYTHONPATH` for code completion.

## Building your entire project
To build all targets in your project, run the following command from the root of your project:

```bash
caiman build
```

This will copy and selectively compile or freeze all targets defined in your `caiman.yaml` file to the `build` folder.
Nothing is deployed on your device at this point.

The following sections will explain how to define your build targets.

## Defining MicroPython sources

To define a MicroPython source target, add a new entry to your `caiman.yaml` file.
A sample source was created in the `micropython` folder during project initialization.

```yaml
sources:
- name: micropython # the name of the target
  parent: micropython # the parent directory of MicroPython sources
  frozen: false # whether to tag the target for freezing to firmware (separate firmware build required)
  compile: true # whether to compile the target to mpy
  files: # paths to component files relative to the parent directory
  - '**/*.py'
  version: '' # optional - version of the target
```

To build all source targets, run the following command from the root of your project:

```bash
caiman build --target=sources
```

This will copy matching source files from all source targets into the `build/micropython` folder.
Sources tagged for compilation will be compiled to mpy format at this point.

## Defining resources

Any files that are not MicroPython sources can be defined as resources.
These can be config files, images, or other data files that your application needs.

To define a resource target, add a new entry to your `caiman.yaml` file in the `resources` section.

```yaml
resources:
- name: resources # the name of the target
  parent: resources # the parent directory of resources
```
The above example will copy all files from the `resources` folder to the `build/micropython` folder.

To build all resource targets, run the following command from the root of your project:

```bash
caiman build --target=resources
```

## Defining dependencies

> A local install of MicroPython is required for dependency management. Make sure it's discoverable on the `PATH`

Dependencies are managed using `mip`, a MicroPython package manager.
They are specified in the `caiman.yaml` file in the `dependencies` section.

Example:
```yaml
dependencies:
- name: logging
  version: latest
  frozen: false # whether to tag the target for freezing to firmware (separate firmware build required)
  compile: true # whether to compile the target to mpy. Local install is always not compiled.
```

This example will install the `logging` package from the MicroPython package index.

To install all dependencies, run the following command from the root of your project:

```bash
caiman build --target=dependencies
```

You can also define specific files that you want to fetch from a dependency.

Example:

```yaml
dependencies:
  - name: github:T0ha/uprotobuf
    version: main
    files:
      - protobuf/uprotobuf.py
```

This will only install the specified files from the `uprotobuf` github repository.

## Defining tools

Tools are dependencies that are only required for development and are not deployed to the device.
They are specified in the `caiman.yaml` file in the `tools` section.
You can use parts of a dependency for development only by specifying the files you need.

Example:
```yaml
tools:
  - name: github:T0ha/uprotobuf
    version: main
    compile: false
    files:
      - scripts/uprotobuf_plugin.py
```

Building all tools:

```bash
caiman build --target=tools
```

This command will copy the specified files from the dependency to the `venv/tools` folder.

## Deploying to the device

> Ensure your device is connected via USB and is discoverable: `ls -latr /dev | grep tty.usbmodem` on OSX.

> Ensure no other processes are using the serial port when deploying to the device. This includes any IDE plugins.


The deployment operation copies the contents of `build/micropython` to the target device.

To deploy all targets, run the following command from the root of your project:

```bash
caiman deploy
```

## Device Operations

### List files on the device

```bash
caiman walk --target=/
```

### Remove all files from the device

> *WARNING*: This will remove all files from the device!

```bash
caiman rmtree --target=/
```

### Dump file contents to the console

```bash
caiman cat --target=/boot.py
```

To do this without logging (useful for parsing):

```bash
caiman --silent cat --target=/boot.py
```

### Run a file on the device

```bash
caiman run --target=/boot.py
```
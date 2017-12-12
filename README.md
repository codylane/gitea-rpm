# Gitea-RPM

A tool/process for generating RPMS for Gitea (Git with a cup of tea) for
Redhat based distros.

[![Build
Status](https://travis-ci.org/codylane/gitea-rpm.svg?branch=master)](https://travis-ci.org/codylane/gitea-rpm)


## Pre-Conditions

* Requires that Docker is installed on your workstation
* Requires python >= 2.7 and < 3 to be installed on your workstation


## Step 1: Initialize this project
**NOTE**: This step should only be required the first time you are
initializing the project.
```
./init.sh
```

* Now we activate the virtualenv in our shell.
* **NOTE:** All further commands assume that the virtualenv has been activated
```
. venv/bin/activate
```

## Step 2: Build the RPMS for 6.x and 7.x
This example shows how to install Gitea version 1.2
(gitea-1.2-linux-amd64) into an RPM.

This step does the the following:
* Downloads the gitea binary
* Builds both the CentOS 6 RPM and a CentOS 7 RPM
* Executes the system integration tests to make sure the RPM works on
  CentOS 6 and CentOS 7.

```
fab build_rpms:gitea_version=1.2,build_git=True
```

* **NOTE:** the `build_git` parameter is optional and is only required the
  first time you build a CentOS 6 RPM.  CentOS 6 doesn't ship with a git
  version that works with Gitea. In order for the system integration
  tests to pass, we need git > 1.7.  Adding the `build_git=True` flag will
  compile git 1.8 for CentOS 6 only.

If all goes well and the tests pass, please consult the `builds/rpms` directory where you checked out the project to get the RPMs for your intended operating system.


## Building a patch release
A patch release is generally the same version i.e `1.2` but it's not ready for the next incremented release which would be `1.3`. To handle this case we just create a JSON file in the `builds` directory with the new release information.  This only handles parameters used to build the RPM.  If the RPM spec file contains bugs then you would also need to adjust the `builds/gitea.spec.j2`.  The specfile is a python Jinja2 template that is fed variables from a JSON blob.

Let's say we encounted a problem with the RPM for gitea version `1.2` and we have already adjusted our RPM spec file.  We just want to increment a new release number.  So we do the following:


```
cat > builds/gitea-1.2-2 << EOF
{
    "package_release": "2"
}
EOF
```

Next, we just run the build process, passing in an argument of what spec we want to use.

```
fab build_rpms:gitea_version=1.2,spec_template=/builds/gitea-1.2-2
```

* **IMPORTANT:** For the folks that are wondering about the `spec_template` param and notice it is `/builds/gitea-1.2-2'` not `builds/gitea-1.2-2`.  It's important that you do not forget to use `/builds/gitea-1.2-2` because the context is inside our build machine and we must pass the fully qualified path, otherwise you will get an error like `IOError: [Errno 2] No such file or directory: 'builds/gitea-1.2-2'`



## Building the next release
Sweet!  We want to build a new RPM for the gitea RPM.  Let's say we are upgrading from `1.2` to `1.3`.  All we need to do is the following.

The best method would be to create a new branch, do the the following changes and then tag the release instead of polluting your repo with `builds/gitea-<version>` stuff.

* We create a new file in `builds/gitea-1.3-1`
* **[OPTIONAL]** adjust the RPM specfile template as needed.
* Build the RPMs


NOTE: this is optional and sould only be used when building a patch release. A major release should be done in a new branch and then tagged.
```
cat > builds/gitea-1.3-1 << EOF
{
    "package_version": "1.3",
    "package_release": "1"
}
EOF

fab build_rpms:gitea_version=1.3,spec_template=/builds/gitea-1.3-1
```

* Ensure the tests for each operating system are updated
* Ensure the the [.travis.yml](.travis.yml) is updated with the new version
* Ensure the fabfile.py files are updated with the right version


## Available JSON parameters for the RPM spec file
Here is the default config found in `builds/fabfile.py`.  If you need to override a default setting then it is recommended that you create a new file in the `builds` directory as follows `builds/gitea-$major.$minor-$release` and ensure the file passes a JSON lint test.
* Where `$major` is the major release #
* Where `$minor` is the minor release #
* Where `$release` is the release #.

Example: `builds/gitea-1.3-1`

```
{
    "package_name": "gitea",
    "package_version": "1.2",
    "package_release": "1",

    "distro": "linux",
    "arch": "amd64",

    "spec_summary": "Git with a cup of Tea",
    "spec_url": "https://gitea.io/en-us",
    "spec_source": "https://dl.gitea.io/gitea/%{pkg_version}/%{pkg_name_ver}-%{distro}-%{distro_arch}",
    "spec_description": "The goal of this project is to make the easiest, fastest, and most painless way of setting up a self-hosted Git service",

    "username": "gitea",
    "groupname": "gitea"
}
```

* **NOTE:** You can customize a individual setting or all of them if you prefer.  If you don't override a setting then you get the default.  All custom values for a key should override the default value.

## Additional tasks available
Consult the `fabfile.py` in the root directory.  There is also a `fabfile.py` in the `builds` directory but those tasks should only be executed on the docker containers that are used to build the RPM.

* Available task arguments are listed in brackets.  I.E. [...]

```
$ fab -l
Available commands:

    build                  Build the docker container entrypoint.  [distro='centos6']
    build_git18            Execute the rpmbuild process to build Git 1.8.  This is really only useful for CentOS 6 boxes
    build_rpm              Execute the rpmbuild process  [distro='centos6']
    build_rpms             Execute the rpmbuild process for all supported distros  [spec_template='']
    clean                  Cleanup builds/bits/*, *.pyc.   []
    download_gitea_binary  Download Gitea binary.   [version, distro='linux', arch='amd64']
    sha256                 Caclulate a sha256 checksum.   [filename]
    test                   Run testinfra integration tests
```

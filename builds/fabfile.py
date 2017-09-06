import json
import os
import testinfra


from fabric.api import *
from jinja2 import Template

GITEA_REMOTE_DIR = '/opt/gitea'
GITEA_USER = 'gitea'
GITEA_GROUP = 'gitea'
GITEA_PID_FILE = '/var/run/gitea/gitea.pid'
GITEA_SYSCONFIG = '/etc/default/gitea'
GITEA_CONF = '/etc/gitea/gitea.conf'
GITEA_PORT = '3000'
GITEA_LOG_FILE = '/var/log/gitea/gitea.log'


DEFAULT_SPEC_DATA = {
    'package_name': 'gitea',
    'package_version': '1.2',
    'package_release': '1',

    'distro': 'linux',
    'arch': 'amd64',

    'spec_summary': 'Git with a cup of Tea',
    'spec_url': 'https://gitea.io/en-us',
    'spec_source': 'https://dl.gitea.io/gitea/%{pkg_version}/%{pkg_name_ver}-%{distro}-%{distro_arch}',
    'spec_description': 'The goal of this project is to make the easiest, fastest, and most painless way of setting up a self-hosted Git service',

    'username': 'gitea',
    'groupname': 'gitea',
}


def render_template(template_file, **data):
    with open(template_file, 'r') as fd:
        t = Template(fd.read())

    return t.render(**data)


def save_template(save_to, content):
    save_to = os.path.expanduser(save_to)
    with open(save_to, 'w') as fd:
        fd.write(content)


@task
def init():
    local('rpmdev-setuptree')


@task
def init_sources():
    local('cp -r /builds/bits/* ~/rpmbuild/SOURCES/')
    local('cp -r /builds/gitea.conf ~/rpmbuild/SOURCES/')


@task
def init_spec(template=None):

    if template:
        with open(template, 'r') as fd:
            jdata = json.load(fd)
        DEFAULT_SPEC_DATA.update(jdata)

    content = render_template('gitea.spec.j2', **DEFAULT_SPEC_DATA)
    save_template('~/rpmbuild/SPECS/gitea.spec', content)


@task
def init_admin_script():
    content = render_template('gitea_adm.j2', remote_dir=GITEA_REMOTE_DIR)
    save_template('~/rpmbuild/SOURCES/gitea-adm', content)


@task
def init_sysconfig():
    data = {
        'remote_dir': GITEA_REMOTE_DIR,
        'pid_file': GITEA_PID_FILE,
        'log_file': GITEA_LOG_FILE,
        'username': GITEA_USER,
        'conf': GITEA_CONF,
        'port': GITEA_PORT,
    }
    content = render_template('gitea.sysconfig.j2', **data)
    save_template('~/rpmbuild/SOURCES/gitea.sysconfig', content)


@task
def init_systemd():
    data = {
        'username': GITEA_USER,
        'groupname': GITEA_GROUP,
        'remote_dir': GITEA_REMOTE_DIR,
        'pid_file': GITEA_PID_FILE,
        'sysconfig_file': GITEA_SYSCONFIG,
    }
    content = render_template('gitea.systemd.j2', **data)
    save_template('~/rpmbuild/SOURCES/gitea.systemd', content)



@task
def build(spec_template=None):
    init()
    init_sources()
    init_spec(template=spec_template)
    init_admin_script()
    init_sysconfig()
    init_systemd()

    host = testinfra.get_host('local://')
    distro = host.system_info.distribution.lower()
    release = int(host.system_info.release.split('.')[0])

    with lcd('~/rpmbuild/SPECS'):
        local('rpmbuild -ba gitea.spec')

    rpm_dir = '/builds/rpms/{distro}/{release}'.format(distro=distro,
                                                       release=release)

    local('mkdir -p {rpm_dir}'.format(rpm_dir=rpm_dir))
    local('rsync -av ~/rpmbuild/RPMS/ {rpm_dir}'.format(rpm_dir=rpm_dir))


@task
def build_git18(distro='centos6'):
    with lcd('~/rpmbuild/SPECS'):
        local('rpmbuild -ba git.spec')

    host = testinfra.get_host('local://')
    distro = host.system_info.distribution.lower()
    release = int(host.system_info.release.split('.')[0])
    rpm_dir = '/builds/rpms/{distro}/{release}'.format(distro=distro,
                                                       release=release)

    local('mkdir -p {rpm_dir}'.format(rpm_dir=rpm_dir))
    local('rsync -av ~/rpmbuild/RPMS/ {rpm_dir}'.format(rpm_dir=rpm_dir))

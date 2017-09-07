# coding: utf-8

import hashlib
import itertools
import os
import pytest
import sys
import testinfra
import threading
import time


from six.moves import urllib


_CACHE = {}

local = testinfra.get_host('local://').check_output


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(TEST_DIR)


INSTALL_GITEA_VERSION='gitea-1.2-1.*'

GITEA_VERSION='1.2.0'


BASE_DIR= os.path.realpath(os.path.join(TEST_DIR, os.path.pardir))
BUILDS_DIR = os.path.realpath(os.path.join(BASE_DIR, 'builds'))


SUT_CENTOS6 = 'gitea-centos6-integration-test'
SUT_CENTOS7 = 'gitea-centos7-integration-test'

DOCKER_IMAGES = [
        SUT_CENTOS6,
        SUT_CENTOS7,
]

TEST_DOCKERFILE = '''
FROM {image}

RUN yum -y install epel-release

RUN yum clean all && \
    yum -y install \
    createrepo \
    initscripts \
    python-pip \
    rsyslog

RUN pip install testinfra

COPY /rpms /rpms

RUN createrepo /rpms/centos/6 && \
    createrepo /rpms/centos/7

RUN echo '' > /rpms/gitea-6.repo && \
    echo '[gitea-6]' >> /rpms/gitea-6.repo && \
    echo 'name = Gitea with a cup of tea' >> /rpms/gitea-6.repo && \
    echo 'baseurl = file:///rpms/centos/6' >> /rpms/gitea-6.repo && \
    echo 'enabled = 1' >> /rpms/gitea-6.repo && \
    echo 'gpgcheck = 0' >> /rpms/gitea-6.repo && \
    echo 'priority = 1' >> /rpms/gitea-6.repo

RUN echo '' > /rpms/gitea-7.repo && \
    echo '[gitea-7]' >> /rpms/gitea-7.repo && \
    echo 'name = Gitea with a cup of tea' >> /rpms/gitea-7.repo && \
    echo 'baseurl = file:///rpms/centos/7' >> /rpms/gitea-7.repo && \
    echo 'enabled = 1' >> /rpms/gitea-7.repo && \
    echo 'gpgcheck = 0' >> /rpms/gitea-7.repo && \
    echo 'priority = 1' >> /rpms/gitea-7.repo

RUN cp /rpms/gitea-{major}.repo /etc/yum.repos.d/

{extra}

CMD ["/sbin/init"]
'''


def get_os_release(host):
    distro = host.system_info.distribution.lower()
    major = host.system_info.release.split('.')[0]

    return (distro, int(major))


def sha256_checksum(text, filename=None):
    sha256 = hashlib.sha256()
    blocksize = 64 * 1024

    if filename is None:
        sha256.update(text)
        return sha256.hexdigest()

    try:
        with open(os.path.realpath(filename), 'rb') as infile:
            block = infile.read(blocksize)
        while block:
            sha256.update(block)
            block = infile.read(blocksize)
        return sha256.hexdigest()
    except IOError:
        return


def build_sut_dockerfile(image):
    distro = image.split('-')[1]
    from_image = distro.replace('centos', 'centos:')
    major = distro.replace('centos', '')

    extra_cmds = ''

    if distro == 'centos7':
        extra_cmds = '''
RUN (cd /lib/systemd/system/sysinit.target.wants/ && \\
     for i in *; \\
        do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done \\
    ); \\
    rm -f /lib/systemd/system/multi-user.target.wants/*; \\
    rm -f /etc/systemd/system/*.wants/*; \\
    rm -f /lib/systemd/system/local-fs.target.wants/*; \\
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \\
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \\
    rm -f /lib/systemd/system/basic.target.wants/*; \\
    rm -f /lib/systemd/system/anaconda.target.wants/*;'''

    content = TEST_DOCKERFILE.format(image=from_image,
                                     builds_dir=BUILDS_DIR,
                                     extra=extra_cmds,
                                     major=major,
                                     )
    filename = 'Dockerfile_{name}-integration-test'.format(name=image.replace(':', ''))
    dockerfile = os.path.join(TEST_DIR, filename)

    with open(dockerfile, 'w') as fd:
        fd.write(content)

    current_checksum = sha256_checksum(content)

    # If the cache is empty for our image, create it and signal to buid image
    if _CACHE.get(image) is None:
        _CACHE[image] = dict(sha256=current_checksum, rebuild=True)
        return dockerfile

    # Our cache must already contain the build image so we validate
    # whether or not we need to rebuild it.
    if current_checksum == _CACHE[image]['sha256']:
        _CACHE[image]['rebuild'] = False
        return dockerfile

    # Our cache must contain the build image but the checksums do not
    # match, so we set the signal to rebuild the image
    _CACHE[image]['rebuild'] = True
    _CACHE[image]['sha256'] = current_checksum

    return dockerfile


def build_docker_container(image):
    sut_container_name = image
    dockerfile = build_sut_dockerfile(image)
    tmpdir = os.path.dirname(dockerfile)

    if _CACHE[image]['rebuild']:

        local('rsync -a {src}/rpms {tmpdir}'.format(src=BUILDS_DIR, tmpdir=TEST_DIR))
        local('docker build -t {image} -f {df} {build_dir}'.format(image=sut_container_name,
                                                                   df=dockerfile,
                                                                   build_dir=tmpdir,
                                                                   ))
        # This is redundant but it should help reduce confusion and bugs
        _CACHE[image]['rebuild'] = False

    return sut_container_name


def docker_container_fixture_name(image, scope):
    fname = '_docker_container_%s_%s' % (image, scope)
    return fname


def build_docker_container_fixture(image, scope):
    @pytest.fixture(scope=scope)
    def func(request):
        docker_host = os.environ.get('DOCKER_HOST')
        if docker_host is not None:
            docker_host = urllib.parse.urlparse(
                docker_host).hostname or 'localhost'
        else:
            docker_host = 'localhost'

        build_docker_container(image)

        docker_id = local('docker run --privileged -dP %s ', image)

        def teardown():
            local('docker rm -f %s', docker_id)

        request.addfinalizer(teardown)

        return docker_id, docker_host
    fname = docker_container_fixture_name(image=image, scope=scope)
    mod = sys.modules[__name__]
    setattr(mod, fname, func)


def initialize_container_fixtures():
    scopes = ['function', 'session']
    for image, scope in itertools.product(DOCKER_IMAGES, scopes):
        build_docker_container_fixture(image, scope)


initialize_container_fixtures()


def build_ssh_config(port, docker_id=None, user='root'):
    filename = os.path.join(TEST_DIR, 'ssh_config')
    if docker_id:
        filename = os.path.join(TEST_DIR, 'ssh_config.%s' %(docker_id))

    items = [
        'Host *',
        'StrictHostKeyChecking no',
        'UserKnownHostsFile /dev/null',
        'IdentityFile %s' %(os.path.join(TEST_DIR, 'id_rsa')),
        'User %s' %(user),
        'Port %s' %(port),
    ]
    with open(filename, 'w') as fd:
        fd.write('\n'.join(items))
    os.chmod(filename, 384) # 0600

    return filename


def get_container_ssh_config(docker_id):
    ssh_config = os.path.join(TEST_DIR, 'ssh_config.' + docker_id)
    if os.path.exists(ssh_config):
        return ssh_config


@pytest.fixture
def host(request):
    image = request.param
    spec_user = 'root'

    scope = 'session'
    if getattr(request.function, 'destructive', None) is not None:
        scope = 'function'

    fname = docker_container_fixture_name(image=image, scope=scope)
    docker_id, docker_host = request.getfixturevalue(fname)

    hostspec = 'docker://' + spec_user + '@' + docker_id

    bkend = testinfra.host.get_host(hostspec)
    bkend.backend.get_hostname = lambda: image

    return bkend


@pytest.fixture
def install_rpm(host, request):
    def oncall(host, name):

        if isinstance(name, list) or isinstance(name, tuple):
            pkgs = ' '.join(name)
            cmd = 'yum install -y {packages}'.format(packages=pkgs)
            result = host.run(cmd)
            assert result.rc == 0, "Unable to Install rpms {}".format(name)
            return result

        if '-' not in name:
            cmd = 'yum install -y {name}'.format(name=name)
            result = host.run(cmd)

            assert result.rc == 0, 'Unable to install rpm {}'.format(name)
            assert host.package(name).is_installed
            return result

        rpm_name, rpm_version, rpm_release = name.split('-')
        rpm_release = rpm_release.replace('.*', '')

        cmd = 'yum install -y {name}'.format(name=name)
        result = host.run(cmd)
        assert result.rc == 0, "Unable to Install rpm {}".format(name)

        assert host.package(rpm_name).is_installed
        assert host.package(rpm_name).version == rpm_version

        return result

    return oncall


@pytest.fixture
def wait_for_svc(host):
    def oncall(host, status, timeout=5):
        status_cmd = '/opt/gitea/gitea-adm status'
        count = 0

        if status == 'start':
            result = host.run(status_cmd).stdout.strip() == ''
        else:
            result = host.run(status_cmd).stdout.strip() != ''

        # minimum of 5 seconds
        if timeout < 50:
            timeout *= 10

        while result:
            if count >= timeout:
                return False
            time.sleep(.1)
            count += 1

        return True

    return oncall


def pytest_generate_tests(metafunc):
    if 'host' in metafunc.fixturenames:
        marker = getattr(metafunc.function, 'docker_images', None)
        if marker is not None:
            hosts = marker.args
        else:
            # Default
            hosts = ['centos:6']

        metafunc.parametrize('host', hosts, indirect=True,
                             scope='function')

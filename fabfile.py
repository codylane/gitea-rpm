import hashlib
import os
import requests
import sys

from fabric.api import *
from fabric.utils import error
from os import environ as ENV


CONTAINER_TAG = ENV.setdefault('CONTAINER_TAG', 'gitea-rpmbuild')
CONTAINER_NAME = ENV.setdefault('CONTAINER_NAME', 'gitea-rpmbuild')

GITEA_DOWNLOAD_URL = 'https://dl.gitea.io/gitea/'

SUPPORTED_DISTROS = [
    'centos6',
    'centos7',
]

BASEDIR = os.path.dirname(os.path.realpath(__file__))

BUILD_DIR = os.path.abspath(os.path.join(BASEDIR, 'builds'))


def GET_HTTP(url, save_to):
    resp = requests.get(url)

    if resp.status_code == 200:
        with open(save_to, 'wb') as fd:
            fd.write(resp.content)
        return resp

    raise ValueError('Received status code: {} from uri: {}'.format(resp.status_code, url))


def sha256_checksum(filename):
    sha256 = hashlib.sha256()
    blocksize = 64 * 1024
    try:
        with open(os.path.realpath(filename), 'rb') as infile:
            block = infile.read(blocksize)
            while block:
                sha256.update(block)
                block = infile.read(blocksize)
        return sha256.hexdigest()
    except IOError:
        pass


def validate_checksum(expected_chksum, filename):

    actual_chksum = sha256_checksum(filename)

    if actual_chksum:
        if actual_chksum == expected_chksum:
            return True

    return False


def valid_distro(distro, raise_error=True):
    if distro not in SUPPORTED_DISTROS:
        if raise_error:
            error('"{}" is an invalid distro.  Choose {}'.format(distro, SUPPORTED_DISTROS))
        return False

    return True


def build_rpm_exec(args, distro='centos6'):
    valid_distro(distro)
    cmd = 'docker run --rm -it --name {name}-{distro} -v {pwd}/builds:/builds {image} {args}'.format(name=CONTAINER_NAME,
                                                                                                     distro=distro,
                                                                                                     pwd=os.getcwd(),
                                                                                                     image=CONTAINER_TAG + '/' + distro,
                                                                                                     args=args,
                                                                                                     )
    local(cmd)


@task
def build(distro='centos6'):
    '''Build the docker container entrypoint.  [distro='centos6'] '''
    valid_distro(distro)
    cmd = 'docker build -t {tag}/{distro} -f Dockerfile.{distro} .'.format(tag=CONTAINER_TAG, distro=distro)
    local(cmd)


@task
def build_rpm(distro='centos6', spec_template=''):
    '''Execute the rpmbuild process  [distro='centos6'] '''
    valid_distro(distro)

    args = []
    if spec_template:
        args.append('spec_template=%s' %(spec_template))

    if args:
        args = ','.join(args)
        build_rpm_exec('build:' + args, distro=distro)
    else:
        build_rpm_exec('build', distro=distro)


@task
def build_git18(distro='centos6'):
    '''Execute the rpmbuild process to build Git 1.8.  This is really only useful for CentOS 6 boxes'''
    build_rpm_exec('build_git18', distro=distro)


@task
def build_rpms(gitea_version, gitea_distro='linux', gitea_arch='amd64', spec_template='', run_tests=True, build_git=False):
    '''Execute the rpmbuild process for all supported distros  [spec_template='']'''

    download_gitea_binary(version=gitea_version, distro=gitea_distro, arch=gitea_arch)

    if build_git:
        build_git18(distro='centos6')

    for distro in SUPPORTED_DISTROS:
        build_rpm(distro=distro, spec_template=spec_template)

    if run_tests:
        test()

@task
def clean():
    '''Cleanup builds/bits/*, *.pyc.   []'''
    local('rm -rf {basedir}/builds/bits/*'.format(basedir=BASEDIR))
    local('rm -rf {basedir}/builds/rpms/*'.format(basedir=BASEDIR))
    local('rm -f *.pyc')


@task
def download_gitea_binary(version, distro='linux', arch='amd64'):
    '''Download Gitea binary.   [version, distro='linux', arch='amd64'] '''
    url = GITEA_DOWNLOAD_URL + '{version}/gitea-{version}-{distro}-{arch}'.format(version=version,
                                                                                  arch=arch,
                                                                                  distro=distro,
                                                                                  )

    url_sha256 = url + '.sha256'

    local('mkdir -p {basedir}/builds/bits'.format(basedir=BASEDIR))

    bin_fname = "{basedir}/builds/bits/{filename}".format(basedir=BASEDIR,
                                                     filename='gitea-{}-{}-{}'.format(version, distro, arch)
                                                     )
    sha256_fname = bin_fname + '.sha256'

    binary_sha256 = GET_HTTP(url_sha256, sha256_fname)
    expected_cksum = binary_sha256.content.split(' ')[0]

    if validate_checksum(expected_cksum, bin_fname):
        return

    binary = GET_HTTP(url, bin_fname)
    if validate_checksum(expected_cksum, bin_fname):
        return

    raise Exception('Downloaded binary: {} but the checksums do not match'.format(bin_fname))


@task
def test(debug=False):
    '''Run testinfra integration tests   [debug=False]'''
    args = ''
    if debug:
        args += '--pdb'

    local('testinfra -vs {}'.format(args))


@task
def sha256(filename):
    '''Caclulate a sha256 checksum.   [filename]'''
    sha256 = sha256_checksum(filename)
    if sha256:
        print(sha256)
        return

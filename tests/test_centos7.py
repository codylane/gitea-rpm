import testinfra
import os
import pytest
import time

from glob import glob

from tests.conftest import get_os_release
from tests.conftest import TEST_DIR
from tests.conftest import INSTALL_GITEA_VERSION
from tests.conftest import GITEA_VERSION
from tests.conftest import SUT_CENTOS7


os.chdir(TEST_DIR)


@pytest.mark.docker_images(SUT_CENTOS7, packages=['git', 'gitea'])
def test_the_gitea_rpm_installs_cleanly(host, install_rpm):
    install_rpm(host=host, name=['git', INSTALL_GITEA_VERSION])


@pytest.mark.docker_images(SUT_CENTOS7)
def test_etc_sysconfig_gitea_file_does_not_exist(host):
    assert host.file('/etc/sysconfig/gitea').exists is False


@pytest.mark.docker_images(SUT_CENTOS7)
def test_etc_initd_gitea_does_not_exist(host):
    assert host.file('/etc/init.d/gitea').exists is False


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_user_exists(host):
    gitea = host.user('gitea')

    assert gitea.exists
    assert gitea.shell == '/sbin/nologin'
    assert gitea.gecos == 'gitea'
    assert gitea.home == '/opt/gitea'
    assert gitea.group == 'gitea'


@pytest.mark.docker_images(SUT_CENTOS7)
def test_opt_gitea_exists(host):
    root_dir = host.file('/opt/gitea')

    assert root_dir.is_directory
    assert root_dir.user == 'gitea'
    assert root_dir.group == 'gitea'
    assert root_dir.mode == 493 # 0755

    assert host.file('/opt/gitea/gitea').exists
    assert host.file('/opt/gitea/gitea').user == 'root'
    assert host.file('/opt/gitea/gitea').group == 'gitea'
    assert host.file('/opt/gitea/gitea').mode == 365 # 0555

    assert host.file('/opt/gitea/gitea-adm').exists
    assert host.file('/opt/gitea/gitea-adm').user == 'root'
    assert host.file('/opt/gitea/gitea-adm').group == 'root'
    assert host.file('/opt/gitea/gitea-adm').mode == 493 # 0755


@pytest.mark.docker_images(SUT_CENTOS7)
def test_etc_gitea_gitea_conf_exists(host):
    etc_gitea = host.file('/etc/gitea')

    assert etc_gitea.is_directory
    assert etc_gitea.user == 'root'
    assert etc_gitea.group == 'gitea'
    assert etc_gitea.mode == 509 # 0775

    gitea_conf = host.file('/etc/gitea/gitea.conf')

    assert gitea_conf.exists
    assert gitea_conf.user == 'root'
    assert gitea_conf.group == 'gitea'
    assert gitea_conf.mode == 436 # 0664


@pytest.mark.docker_images(SUT_CENTOS7)
def test_var_run_gitea_exists(host):
    var_run = host.file('/var/run/gitea')
    assert var_run.exists
    assert var_run.user == 'root'
    assert var_run.group == 'gitea'
    assert var_run.mode == 509 # 0775


@pytest.mark.docker_images(SUT_CENTOS7)
def test_var_log_gitea_exists(host):
    var_run = host.file('/var/log/gitea')
    assert var_run.exists
    assert var_run.user == 'root'
    assert var_run.group == 'gitea'
    assert var_run.mode == 509 # 0775


@pytest.mark.docker_images(SUT_CENTOS7)
def test_etc_default_gitea_exists(host):
    etc_default_gitea = host.file('/etc/default/gitea')

    assert etc_default_gitea.exists
    assert etc_default_gitea.user == 'root'
    assert etc_default_gitea.group == 'gitea'
    assert etc_default_gitea.mode == 436 # 0664

@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_adm_status_is_invoked_and_the_service_is_not_running_it_should_return_3(host):
    host.run('/opt/gitea/gitea-adm stop')
    gitea = host.run('/opt/gitea/gitea-adm status')

    assert gitea.rc == 3


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_service_starts_up_via_gitea_adm_start(host):
    gitea = host.run('/opt/gitea/gitea-adm start')
    time.sleep(.3)

    assert gitea.rc == 0

    gitea = host.run('/opt/gitea/gitea-adm status')
    assert gitea.rc == 0
    assert gitea.stdout.strip().isdigit() and int(gitea.stdout.strip()) > 0

    gitea = host.run('/opt/gitea/gitea-adm stop')
    assert gitea.rc == 0


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_service_script_will_report_the_correction_gitea_version(host):
    gitea = host.run('/opt/gitea/gitea-adm version')

    assert gitea.rc == 0
    assert gitea.stdout.strip() == GITEA_VERSION


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_service_script_can_create_cacerts_into_current_working_directory_of_the_user(host):
    gitea = host.run('/opt/gitea/gitea-adm create-cacert')

    assert gitea.rc == 0

    assert host.file('key.pem').exists
    assert host.file('key.pem').user == 'root'
    assert host.file('key.pem').group == 'root'
    assert host.file('key.pem').mode == 384 # 0600

    assert host.file('cert.pem').exists
    assert host.file('cert.pem').user == 'root'
    assert host.file('cert.pem').group == 'root'
    assert host.file('cert.pem').mode == 420 # 0644


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_service_will_startup_through_systemd(host):
    host.run('systemctl stop gitea')
    time.sleep(.3)

    assert host.service('gitea').is_running is False
    assert host.service('gitea').is_enabled is False

    result =  host.run('systemctl start gitea')
    time.sleep(.5)
    assert result.rc == 0

    assert host.service('gitea').is_running
    assert host.service('gitea').is_enabled is False


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_service_will_shutdown_through_systemd(host):
    host.run('systemctl start gitea')
    time.sleep(.3)

    result = host.run('systemctl stop gitea')
    time.sleep(.3)
    assert result.rc == 0

    assert host.service('gitea').is_running is False
    assert host.service('gitea').is_enabled is False


@pytest.mark.docker_images(SUT_CENTOS7)
def test_gitea_adm_script_can_be_invoked_by_the_gitea_user(host):
    host.run('/opt/gitea/gitea-adm stop')
    time.sleep(.3)

    result = host.run('su - gitea -s /bin/bash -c "/opt/gitea/gitea-adm status"')
    assert result.rc == 3

    result = host.run('su - gitea -s /bin/bash -c "/opt/gitea/gitea-adm start"')
    time.sleep(.5)
    assert result.rc == 0

    result = host.process.filter(user='gitea', comm='gitea')
    assert result

    result = host.run('su - gitea -s /bin/bash -c "/opt/gitea/gitea-adm stop"')
    time.sleep(.5)
    assert result.rc == 0

    result = host.process.filter(user='gitea', comm='gitea')
    assert result == []


@pytest.mark.docker_images(SUT_CENTOS7)
def test_uninstall_of_gitea(host):
    assert host.package('gitea').is_installed

    result = host.run('yum remove -y gitea')
    assert result.rc == 0
    assert host.package('gitea').is_installed is False

    assert host.user('gitea').exists

    etc_gitea = host.file('/etc/gitea')
    assert etc_gitea.exists

    assert host.file('/etc/gitea/gitea.conf.rpmsave').exists
    assert host.file('/etc/default/gitea.rpmsave').exists is False

    assert host.file('/opt/gitea').exists

    assert host.file('/var/log/gitea').exists

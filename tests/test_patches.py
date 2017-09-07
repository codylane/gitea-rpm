import pytest

from tests.conftest import SUT_CENTOS6
from tests.conftest import SUT_CENTOS7


@pytest.mark.docker_images(SUT_CENTOS6)
def test_we_patched_the_service_module_to_SysvService_on_centos6(host):
    assert host.service('foo').__class__.__name__ == 'SysvService'

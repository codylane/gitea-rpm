import testinfra.modules
from testinfra.modules.service import *  # noqa: H303


class PatchedService(Service):

    @classmethod
    def get_module_class(cls, host):
        if host.system_info.type == "linux":
            if (
                host.exists("systemctl")
                and "systemd" in host.file("/sbin/init").linked_to
            ):
                return SystemdService

            if host.exists("initctl") and host.system_info.distribution.lower() != 'centos':
                return UpstartService

            return SysvService

        if host.system_info.type == "freebsd":
            return FreeBSDService

        if host.system_info.type == "openbsd":
            return OpenBSDService

        if host.system_info.type == "netbsd":
            return NetBSDService

        raise NotImplementedError

testinfra.modules.get_module_class('service').get_module_class = PatchedService.get_module_class

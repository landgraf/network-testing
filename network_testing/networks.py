from pyroute2 import NetNS
from pyroute2 import IPDB
## FIXME isn't needed once https://github.com/svinota/pyroute2/issues/450 
## is fixed
import subprocess

class Network():

    name = ""
    ipdb = None
    ## dict to reflect connection with other namespaces (if any)
    links = {}
    initialized = False

    def _delns(self, name):
        netns = NetNS(name)
        netns.close()
        netns.remove()

    def __init__(self, name):
        self._delns(name)
        self.ipdb = IPDB(nl = NetNS(name))
        with self.ipdb.interfaces.lo as lo:
            lo.up()
        self.ipdb.release()
        self.name = name

    def delete(self):
        netns = NetNS(self.name)
        netns.close()
        netns.remove()

    def add_address(self, dstns, address):
        """
        Assign IP address to the link between two namespaces (self and dstns)
        """
        #self.links.append({"network" : connectto, "iface" : srclink})

        ifname = None
        if self.links.has_key(dstns.name):
            ifname = self.links[dstns.name]
            ipdb = IPDB(nl = NetNS(self.name))
            iface = ipdb.interfaces.get(ifname)
            subprocess.check_call(['ip', '-n', self.name, 'address', 'add', address, 'dev', iface.ifname])
            return
            ## Use subprocess for now because of
            ## https://github.com/svinota/pyroute2/issues/450
            print("NS: %s Attaching %s to %s") %(self.name, address, iface.ifname)
            with iface:
                iface.add_ip(address)
                iface.up()
            ipdb.release()
        else:
            ## FIXME exception
            print("Exception XXX")
            pass

    def connect(self, connectto):
        """
        Connect this network to the one specified by connectto
        basically it means two virtual inrerfaces should be created in the namespace
        and connectto, linked to each other and brought up
        """
        common_ipdb = IPDB()
        srclink = "{}_{}".format(self.name, connectto.name)
        dstlink = "{}_{}".format(connectto.name, self.name)
        iface = common_ipdb.interfaces.get(srclink)
        if iface is not None:
            with iface:
                print("Removing orphaned interface %s") %{iface.ifname}
                iface.remove()
        common_ipdb.create(ifname=srclink, kind='veth', peer=dstlink).commit()
        for link, ns in (srclink, self.name), (dstlink, connectto.name):
            iface = common_ipdb.interfaces.get(link)
            with iface:
                iface.net_ns_fd = ns
        for (ipdb, link) in (IPDB(nl = NetNS(self.name)), srclink), (IPDB(nl = NetNS(connectto.name)), dstlink):
           iface = ipdb.interfaces.get(link)
           with iface:
               iface.up()
           ipdb.release()
        self.links[connectto.name] = srclink
        connectto.links[self.name] = dstlink


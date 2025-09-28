#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.node import OVSController
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.term import makeTerm


class Single3Topo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        
        self.addHost(f'h1')
        self.addLink(f'h1', s1, bw=100, loss=10)
        
        for i in range(2, 4):
            self.addHost(f'h{i}')
            self.addLink(f'h{i}', s1, bw=100, loss=0)

def run():
    topo = Single3Topo()
    net = Mininet(topo=topo, controller=OVSController, link=TCLink)
    net.start()

    h1 = net.get('h1')

    makeTerm(h1, cmd='python3 start-server.py -v -s ../assets -H 10.0.0.1')

    from mininet.term import makeTerms
    makeTerms([h for h in net.hosts if h.name != 'h1'])

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
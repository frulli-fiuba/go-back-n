from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

def run_test_topology():
    setLogLevel('info')

    # Create a Mininet object with Traffic Control links
    net = Mininet(link=TCLink)

    info('*** Adding hosts and a switch\n')
    # Add a server host with a static IP
    server = net.addHost('server', ip='10.0.0.1')
    # Add a client host with a static IP
    client = net.addHost('client', ip='10.0.0.2')
    # Add a simple switch
    s1 = net.addSwitch('s1')

    info('*** Creating links with 10% packet loss\n')
    # Add links between the hosts and the switch
    # The 'loss' parameter is key here to simulate a lossy network
    net.addLink(server, s1, loss=10)
    net.addLink(client, s1, loss=10)

    info('*** Starting the network\n')
    net.start()

    # Place your client and server scripts in the same directory as this file.
    info('*** Running the server and client scripts\n')
    
    # Start the server script in the background
    # The '&' sends the process to the background, so the script can continue
    info('Starting server on host server...\n')
    server.cmd('python3 server.py &')

    # Run the client script and wait for it to finish
    info('Starting client on host client...\n')
    client.cmd('python3 client.py')
    
    info('Client finished execution.\n')

    # This line opens a command-line interface for manual inspection if needed
    # Comment this out for automated testing
    # CLI(net)

    info('*** Stopping the network\n')
    net.stop()

if __name__ == '__main__':
    run_test_topology()

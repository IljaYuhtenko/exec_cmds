# exec_cmds
A simple script designed to run multiple commands on multiple network devices

An idea is simple: you have a network full of various devices and for most of them there is your own RADIUS-controlled login/password that is taken by the script as default
You want to run multiple commands on multiple devices. 

So, instead of putting your login/password on each switch or router you write a simple .yml, like the following:

    my-switch:
      cmds:
        - show version
        - show ip int bri
    my-switch-2:
      cmds:
        - show int status
        - conf t
        - int Gi0/1
        - swi trunk all vlan 100

Then you execute the file (python main.py example.yml) and find yourself losing access to my-switch-2, because Gi0/1 is an uplink port and you deleted every vlan except 100, so be careful with the script!

You can specify you company default domain in config.yml like:

    def_domain = .example.co.uk
    
And script will resolve my-switch-2.example.co.uk instead of my-switch-2

You can also specify login different from your RADIUS login (script will ask you to provide different password), specific port or explicitly specify a platform (which is useful, if you provide an ip address instead of a hostname of the device). Here's an example:

    192.168.88.1:
      login: admin
      port: 12322
      platform: mikrotik_routeros
      cmds:
        - ip service set disabled=no [find where name=winbox]
        
In case your SSH fails (or the devices is not set up for SSH), script will attempt to reach the device via Telnet

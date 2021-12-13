# xosmon
This script uses SSH to connect to the target linux machine and executes below 3 commands based on the specified interval, logs the result and sends email if configured, to notify the usage values.

 - System requiremenet:
```
OS: Any
Environment: Python 3.6 or higher
#pip3 install paramiko
```

 - The SSH session will remain open until the script is terminated using CTRL+C.

 - Below commands will be executed on the target machine every {interval} seconds:

CPU:
```
cat <(grep 'cpu ' /proc/stat) <(sleep 1 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}'
```

RAM:
```
free -m
```

Disk:
```
df -h
```


Basic Usage:
```
$python3 xosmon.py -u username -p Password -a 172.172.172.172
```

Options:
```
$ python3 xosmon.py -h
Usage: xosmon.py [options]

Options:
  -h, --help            show this help message and exit
  -u UNAME, --username=UNAME
                        Linux Server username. e.g. root - Mandatory
  -p PASSW, --password=PASSW
                        Linux Server password. e.g. password - Mandatory
  -a IP, --ipaddress=IP
                        Server ip address, like 172.29.4.3 - Mandatory
  -C CPUTHRESHOLD, --cputhreshold=CPUTHRESHOLD
                        Specify the threshold above which the cpu usage will
                        be logged and mailed. like 40 ,or -1 to log all values
                        - Optional-Default=-1
  -D DISKTHRESHOLD, --diskthreshold=DISKTHRESHOLD
                        Specify the threshold above which the disk usage will
                        be logged and mailed. like 40,or -1 to log all values
                        - Optional-Default=-1
  -R RAMTHRESHOLD, --ramthreshold=RAMTHRESHOLD
                        Specify the threshold above which the ram usage will
                        be logged and mailed - The value considers buff/cache
                        usage as used. like 40,or -1 to log all values -
                        Optional-Default=-1
  -i INTERVAL, --interval=INTERVAL
                        Metric query interval in seconds - Optional-
                        Default=5
  -s LOGSIZE, --logfilesize=LOGSIZE
                        Log file size/rotation limitation in MB - Optional-Default=10
  -e EMAILADDRESS, --emailaddress=EMAILADDRESS
                        The destnation email address to receive the mail
                        notifications - Optional-Default=monitor@nfmt.com
  -m RELAYSERVER, --relayserver=RELAYSERVER
                        SMTP Relay server IP address,like -m 172.29.4.3 -
                        Optional-Default=127.0.0.1
  -M ENABLEMAIL, --enablemail=ENABLEMAIL
                        Whether to enable mail notification feature (1), or
                        not (0), e.g: -M 1 - Optional-Default=0
  -y MAILINTERVAL, --mailinterval=MAILINTERVAL
                        Time in seconds to put the mail engine into sleep
                        after each mail to avoid mailbox overload, e.g: -y
                        1800 - Optional-Default=1800
  -P SSHPORT, --sshport=SSHPORT
                        non-default ssh port number. Default is 22, use 5122
                        for 1830PSS
```

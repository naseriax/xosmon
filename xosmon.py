__author__ = "naseredin.aramnejad@gmail.com"


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from optparse import OptionParser
from threading import Thread
import smtplib
import getpass
import socket
import time
import sys
import os

try:
    import paramiko
except:
    print("Error in importing paramiko, Make sure paramiko is installed properly (pip3 install paramiko)")
    input("Press Enter to exit...")
    sys.exit()


'''
How the script works:
 - It tries to login to the linux server (NFMT or 1830 PSS) using the provided params.
 - After a successful login (if No exception is raised on ssh.connect() ), it starts the monitoring loop and queries the  RAM/CPU/DISK usage by
   sending below command every "interval" seconds:
    CPU: cat <(grep 'cpu ' /proc/stat) <(sleep 1 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}'
    RAM: free -m
    DISK: df -h
    
 - It will continue running unless stopped using CTRL-C on the terminal, then it sends a logout command to the target and closes the SSH session.
    
 - Execution: (Python 3.6 or higher)
    python xosmon.py -a 1.1.1.1 -u root -p 'password' -P 5122 -i 5
'''






#Handles Email notification to the Mail Relay server
class typhoon: 
    def __init__(self,params):
        self.smptpRelayServerIp = params['ip']
        self.smptpPort = params['port'] if "port" in params else 25
        self.fromAddr = params['from']
        self.toAddr = params['to']
        self.subject = params['subject']
        self.content = params['content']
        if self.sender():
            print(f"{self.getTime()} - Mail notification event")
        else:
            print(f"{self.getTime()} - Mail error")
    
    #Returns current time and date      
    def getTime(self): 
        return time.strftime("%Y-%m-%d-%H-%M-%S")

    def sender(self):
        try:
            s = smtplib.SMTP(host=self.smptpRelayServerIp, port=self.smptpPort)
            msg = MIMEMultipart()
            msg['To'] = self.toAddr
            msg['From'] = self.fromAddr
            msg['subject'] = self.subject
            msg.attach(MIMEText(self.content, 'plain'))
            s.send_message(msg)
            return True
        except ConnectionRefusedError:
            print("SMTP relay server unreachable (IP or Port)")
        except Exception as e:
            return False      


#Handles linux os resource monitoring (RAM/CPU/DISK)      
class eagleEye: 
    def __init__(self,kwargs):
        self.readyToSend = True
        self.logfilename = f"{self.getTime()}_xosmon.csv"
        self.serverIp = kwargs["ip"]
        self.enablemail = kwargs["enablemail"]
        self.mailinterval = kwargs["mailinterval"]
        self.logsize = kwargs["logsize"]
        self.relayserver = kwargs["relayserver"]
        self.emailaddress = kwargs["emailaddress"]
        self.port = kwargs["port"]
        self.uname = kwargs["uname"]
        self.passw = kwargs["passw"]
        self.thr = kwargs["threshold"]
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    #After a successful login, it starts collecting the data
    def mainFunc(self):
        self.cpuMonitor()
        time.sleep(0.1)
        self.ramMonitor()
        time.sleep(0.1)
        self.diskSpaceMonitor()
        self.output()

    #login to the server
    def connect(self):
        try:
            self.ssh.connect(self.serverIp,self.port,self.uname,self.passw)
            time.sleep(0.25)
            return 0
            
        except paramiko.AuthenticationException:
            return 1
        except  (socket.error,ConnectionResetError):
            return 2

    #Retrieves Current CPU Utilization, Works on 1830PSS and RHEL
    # Command: cat <(grep 'cpu ' /proc/stat) <(sleep 1 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}'
    def cpuMonitor(self):
        cpu = self.cliExec("cat <(grep 'cpu ' /proc/stat) <(sleep 1 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}'")
        self.cpuUsage = round(float(cpu),2)

    #Retrieves Current RAN Utilization, Works on 1830PSS and RHEL
    #Command: free -m
    def ramMonitor(self):
        ram = self.cliExec("free -m")
        parsedRam = [val for val in ram.splitlines()[1].split(" ") if val !=""]
        
        #It uses Available column on free -m as the reference which considers buff/cache column as used!
        self.ramUsage = round( 100 - (int(parsedRam[6])*100)/int(parsedRam[1]),2)

    #Retrieves Current Disk Utilization, Works on 1830PSS and RHEL
    #Command: df -h
    def diskSpaceMonitor(self):
        self.mountPoints = {}
        diskSpace = self.cliExec("df -h")
        for m in diskSpace.splitlines()[1::]:
            ramUsageValues = [val for val in m.split(" ") if val != ""]
            self.mountPoints[ramUsageValues[5]] = float(ramUsageValues[4].replace("%",""))

    #This method executes the provided command on the logged in server (ssh session) and returns the output
    def cliExec(self,cmd):
        output = ""
        stdout = self.ssh.exec_command(cmd)[1]
        while True:
            line = stdout.readline()
            if not line:
                break
            output += line
        return output

    #Returns current date and time
    def getTime(self): 
        return time.strftime("%Y-%m-%d-%H-%M-%S")

    #Terminates the ssh session after logout
    def terminator(self):
        print("\nClosing the session...")
        self.cliExec("exit")
        self.ssh.close()
        print("SSH session is successfully terminated!")

    #Handles log file creation/rotation and content insertion
    def log(self,filename,data="",meth=False): 
        try:
            if meth == True:
                print(data)
            if os.path.exists(filename):
                if os.path.getsize(filename) >= self.logsize * 1000000:
                    self.logfilename = f"{self.getTime()}_xosmon.csv"
                    with open(filename,"a") as logs:
                        logs.write(f"{self.getTime()},,,,Log Rotation Event! - New log File: {self.logfilename}\n")
                    filename = self.logfilename  
                    print(f"{self.getTime()},,,,Log rotation event! - New log file: {filename}")

            if not os.path.exists(filename):
                with open(filename,"a") as logs:
                    logs.write("Date&Time,Category,Location,Utilization,Remarks\n")
                    logs.write(f"{data}\n")
            else:
                with open(filename,"a") as logs:
                    logs.write(f"{data}\n")

        except PermissionError:
            print("Cannot access the log file, If it's open by Excel, the script won't be able to access the file. Use Notpad++ or VSCode for trace purposes!")
        except:
            print(f"Logging exception! for:",data)
    
    #Prepares the needed data for sending an email notification
    def mailNotify(self,mailContent=[]):
        params = {}
        params['ip'] = self.relayserver
        params['port'] = 25
        params['from'] = "eagleeyeNotif@servermon.local"
        params['to'] = self.emailaddress
        params['subject'] = f"High server resource usage detected!"
        params['content'] = f"\n{'*'*10}\n".join(mailContent)
        try:
            typhoon(params)
        except:
            print("Exception : ****  Mail Exception ****")
    
    #Gathers resource utilization data for logging in the log file or sending email notification
    def output(self):
        mailContent = []
        t = self.getTime()
        if self.ramUsage >= self.thr["RAM"]:
            self.log(data=f"{t},Computational Resource,RAM,"+f"{self.ramUsage}%",meth=False,filename=self.logfilename)
            mailContent.append(f"RAM Usage at {t},{self.ramUsage}%")
        if self.cpuUsage >= self.thr["CPU"]:
            self.log(data=f"{t},Computational Resource,CPU,"+f"{self.cpuUsage}%",meth=False,filename=self.logfilename)
            mailContent.append(f"CPU Usage at {t}: {self.cpuUsage}%")
        for i,j in self.mountPoints.items():
            if j > self.thr["DISK"]:
                self.log(data=f"{t},Storage Resource,{i},"+f"{j}%",meth=False,filename=self.logfilename)
                mailContent.append(f"DISK mountpoint:{i} Usage at {t}: {j}%")
        
        #Email sending interval thread
        #It sends email notification only if:
            #self.enablemail is set to 1 during script execution
            #mailContent is not empty
            #Email sending time interval is passed (self.readyToSend == True)
        if int(self.enablemail) == 1:
            if mailContent:
                if self.readyToSend == True:
                    self.mailNotify(mailContent)
                    thread = Thread(target=self.mailSleep)
                    thread.daemon = True
                    thread.start()

    #After sending of each mail, the mail function will sleep for self.mailinterval time period  
    def mailSleep(self):
        self.readyToSend = False
        time.sleep(self.mailinterval)
        self.readyToSend = True
        
#Initiates login secquence, retries until login is successful
def connect(serverObject):
    counter = 1
    while True:
        print(f"Connection attempt: {counter}")
        connectionProbe = serverObject.connect()
        if connectionProbe == 0:
            print("Successfully connected!, Running the monitoring engine...")
            print("use CTRL+C to stop!")
            break
        elif connectionProbe == 1:
            print("Wrong username/password, closing...")
            time.sleep(5)
            sys.exit()
        elif connectionProbe == 2:
            print("Server unreachable. retrying after 5 seconds...")
            time.sleep(5)
            counter += 1
         
if __name__ == "__main__":

    #Server initialal params
    serv = {
        "ip" : "172.16.1.1",
        "uname" : "root",
        "passw" : "password",
        "interval":10,
        "logsize":10.0, #MB
        "emailaddress":"monitor@nfmt.com",
        "enablemail": 0,
        "relayserver":"127.0.0.1",
        "port" : 22,
        "threshold":{"RAM":-1, #The script logs the data and send mail notif only if the monitored resource utilization is above these values
                     "CPU":-1,
                     "DISK":-1}}
    
    parser = OptionParser()
    
    #Mandatory params
    parser.add_option("-u", "--username", dest="uname", default="", help="Linux Server username. e.g. root - Mandatory" )
    parser.add_option("-p", "--password", dest="passw", default="", help="Linux Server password. e.g. password - Mandatory" )
    parser.add_option("-a", "--ipaddress", dest="ip", default="", help="Server ip address, like 172.29.4.3 - Mandatory")
    
    #Optional params
    parser.add_option("-C", "--cputhreshold", dest="cputhreshold", default="", help="Specify the threshold above which the cpu usage will be logged and mailed. like 40 ,or -1 to log all values - Optional-Default=-1")
    parser.add_option("-D", "--diskthreshold", dest="diskthreshold", default="", help="Specify the threshold above which the disk usage will be logged and mailed. like 40,or -1 to log all values - Optional-Default=-1")
    parser.add_option("-R", "--ramthreshold", dest="ramthreshold", default="", help="Specify the threshold above which the ram usage will be logged and mailed - The value considers buff/cache usage as used. like 40,or -1 to log all values - Optional-Default=-1")
    parser.add_option("-i", "--interval", dest="interval", default="", help="Metric query int-i 5erval in seconds - Optional-Default=5")
    parser.add_option("-s", "--logfilesize", dest="logsize", default="", help="Log file size limitation in MB - Optional-Default=10")
    parser.add_option("-e", "--emailaddress", dest="emailaddress", default="", help="The destnation email address to receive the mail notifications - Optional-Default=monitor@nfmt.com")
    parser.add_option("-m", "--relayserver", dest="relayserver", default="", help="SMTP Relay server IP address,like -m 172.29.4.3 - Optional-Default=127.0.0.1")
    parser.add_option("-M", "--enablemail", dest="enablemail", default="", help="Whether to enable mail notification feature (1), or not (0), e.g: -M 1 - Optional-Default=0")
    parser.add_option("-y", "--mailinterval", dest="mailinterval", default="", help="Time in seconds to put the mail engine into sleep after each mail to avoid mailbox overload, e.g: -y 1800 - Optional-Default=1800")
    parser.add_option("-P", "--sshport", dest="sshport", default="", help="non-default ssh port number. Default is 22, use 5122 for 1830PSS")
    (options, args) = parser.parse_args()
    
    serv['relayserver'] = options.relayserver if options.relayserver else "172.29.4.37"
    serv['enablemail'] = options.enablemail if options.enablemail else 0
    serv['emailaddress'] = options.emailaddress if options.emailaddress else "monitor@nfmt.com"
    serv['uname'] = options.uname if options.uname else input("NFM-T Server Username: ")
    serv['passw'] = options.passw if options.passw else getpass.getpass()
    serv['ip'] = options.ip if options.ip else input("Server IP Address: ")
    serv['port'] = options.sshport if options.sshport else 22
    serv['mailinterval'] = int(options.mailinterval) if options.mailinterval else 1800
    serv['interval'] = int(options.interval) if options.interval else 10
    serv['logsize'] = float(options.logsize) if options.logsize else 10.0
    serv['threshold']["RAM"] = int(options.ramthreshold) if options.ramthreshold else -1
    serv['threshold']["CPU"] = int(options.cputhreshold) if options.cputhreshold else -1
    serv['threshold']["DISK"] = int(options.diskthreshold) if options.diskthreshold else -1
    

    serverPmQuery = eagleEye(serv)
    print(f"Current query interval: {serv['interval']}s")
    
    #Login sequence
    connect(serverPmQuery)
    
    #Main execution loop
    while True:
        try:
            serverPmQuery.mainFunc()
            time.sleep(serv["interval"])

        #If for any reason, the ssh session is closed, it starts the login sequence and continues only if the login is successful
        except (socket.error , ConnectionResetError):
            print("Lost connection to the server.")
            connect(serverPmQuery)

        #Stops the script if CTRL-C is issued
        except KeyboardInterrupt:
            serverPmQuery.terminator()
            break
        


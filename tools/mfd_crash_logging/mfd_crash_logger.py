from tools.ssh import SSHHandler
import os
from time import sleep


class MFDCrashLogs:
    def __init__(self, crash_log_script_name, crash_log_script_path, local_crash_log_path, host, ssh_handler):

        self.ssh_handler = ssh_handler
        self.crash_script = crash_log_script_name
        self.script_path = crash_log_script_path
        self.local_path = local_crash_log_path
        self.host = host

        if not os.path.exists(self.local_path):
            print(f"Creating crash log directory {self.local_path}")
            os.mkdir(self.local_path)
            print("Crash log directory created")

        if host["Model"] == "Axiom":
            self.remote_path = "/data/raymarine"
        elif host["Model"] == "Axiom 2":
            self.remote_path = "/data/vendor/raymarine"
        else:
            print("Unknown model, Cant set script path")
    #         todo custom exception here

    def transfer_crash_log_script(self):
        print("Transferring shell script")
        self.ssh_handler.scp_connect()


        connection, return_code = self.ssh_handler.push_file(self.script_path, self.remote_path)
        if return_code == 1011:
            print(f"Pushed {self.script_path} to {self.remote_path}")
        else:
            print("An error occurred whilst pushing shell script to remote")
            return "Couldn't Push Shell Script"

        print("Transferred shell script")

        sleep(2)

    def execute_crash_log_script(self):
        _full_remote_path = f"{self.remote_path}/{self.crash_script}"

        # Set permissions for shell script
        print("Setting Permissions for extract_crashes.sh")
        _set_permissions = f"chmod +x {_full_remote_path}"

        # todo I think this previously needed to have the output caught, Test this
        print(f"Setting Permissions for {self.remote_path}/{self.crash_script}")
        self.ssh_handler.execute_command(_set_permissions)

        # Execute shell script
        print(f"Executing shell script at {self.remote_path}/{self.crash_script}")
        _execute_script = f".{_full_remote_path}"

        # todo I think this previously needed to have the output caught, Test this
        self.ssh_handler.execute_command(_execute_script)

        sleep(5)

    def pull_crash_logs(self):
        _check_crash_logs = "ls /mnt/tmp/crash_logs/"

        print("Checking for crashlog file")
        # todo if command fails to execute we need to catch it here
        _output = self.ssh_handler.execute_command_with_output(_check_crash_logs)

        _output = _output[0]

        print(f"{_output} Checking for crashlog file")

        # If crash log file is not present, print message and go through loop again
        # If crash log file is present, get the name of the file and use scp tunnel to transfer it to local machine
        if _output == "ls: /mnt/tmp/crash_logs/: No such file or directory":
            print(f"No crashes detected for {self.host['hostname']}")
            # todo am i still tracking this?? This line only works for one host pretty sure
            hosts_without_crash_logs = [self.host]

            print(f"Closing SSH connections to {self.host['hostname']}")
            self.ssh_handler.disconnect_all()

        elif _output != "ls: /mnt/tmp/crash_logs/: No such file or directory":
            _log_name = _output
            _remote_directory = f"./mnt/tmp/crash_logs/{_log_name}"
            _find_crash_logs_file = f"ls {_remote_directory}"

            print(f"Crash logs for {self.host['hostname']} located at {_remote_directory}")
            print(f"Checking for crash logs in {_remote_directory}")
            _output, _exit_status = self.ssh_handler.execute_command_with_exit_status(_find_crash_logs_file)

            if _exit_status == 0:
                # todo did i break this "output"?
                print(f"Crash logs found in {_remote_directory}: {_output[0]}")
                # todo this falls over if the directory already exists
                # Create directory for the system if it doesn't exist
                # this is no longer needed as we are removing the concepts of systems
                if not os.path.exists(f"{app.config['CRASH_LOG_DIR']}/{host['System']}"):
                    os.mkdir(f"{app.config['CRASH_LOG_DIR']}/{host['System']}")
                    print(f"Created {app.config['CRASH_LOG_DIR']}/{host['System']} directory for " + host["System"])

                # Create directory for crash logs using MFD Name and MFD Serial Number
                log_file_name = (f"{app.config['CRASH_LOG_DIR']}/{host['System']}/{host['Name']}"
                                 f"_{host['SerialNumber']}")
                log_file_name = log_file_name.replace(" ", "_")
                os.mkdir(log_file_name)
                print(
                    f"Created {log_file_name} directory")

                save_useful_host_info(host, log_file_name, ssh_handler)

                # todo did i break this by moving into the if statement from past the else?
                if output:
                    for file in output:
                        file = file.replace("\n", "").replace("\r", "")
                        remote_file = f"{remote_directory}/{file}"
                        print(remote_file)
                        local_file = log_file_name + "/" + file
                        local_file = local_file.replace(":", "-")
                        print(local_file)

                        print("Getting Logs")
                        connection, return_code = ssh_handler.pull_file(local_file, remote_file)
                        if return_code == 1013:
                            print(f"Pulled {remote_path} to {local_path}")
                        else:
                            print("An error occurred whilst pulling file from remote")
                            return "Couldn't Pull Logs"
                else:
                    print("No files in directory")

            else:
                print(f"ls command failed with exit status {exit_status}")
    def remove_mfd_crash_logs(self):

    def reset_mfd_dropbox(self):



    def get_mfd_crash_logs(self, host):
        # set up ssh
        # Runs all steps, then returns logs
        # tear down ssh/scp
        pass


class ProcessMFDCrashLogs(MFDCrashLogs):
    def __init__(self, host):


    def get_mfd_crash_logs(self, host):
        for host in hosts:
            ssh_handler = SSHHandler(host)
            mfd_crash_logs = MFDCrashLogs(app.config['CRASH_LOG_DIR'], host, ssh_handler)
            mfd_crash_logs.transfer_crash_log_script(app.config['CRASH_LOG_SCRIPT_PATH'])
            mfd_crash_logs.execute_crash_log_script()
            mfd_crash_logs.check_for_crash_logs()
            mfd_crash_logs.pull_crash_logs()
            mfd_crash_logs.remove_mfd_crash_logs()
            mfd_crash_logs.reset_mfd_dropbox()
            mfd_crash_logs.get_mfd_crash_logs(host)

        pass






# get logs > sort logs > jira tickets > stats
# get logs > sort logs > jira tickets
# get logs
"""
Title: SSHHandler.py
Author: Arthur White
Date Created: 09/02/2024
Date Refactored: 08/11/2024

The SSH Handler Module is used to connect to a remote device to execute commands or to transfer files

Usage - Create an instance of the SSHHandler Class:
SSHHandler = SSHHandler(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")
SSHHandler.execute_command("reboot")

Connection Status for SSH and SCP:
2 - Connected
1 - Disconnected
0 - Connection Failed
"""

import paramiko
from scp import SCPClient, SCPException
from time import sleep
from contextlib import suppress
import errno


class SSHError(Exception):
    # This exception is raised when an error occurs during an SSH operation
    pass


class SCPError(Exception):
    # This exception is raised when an error occurs during an SCP operation
    pass


class NetworkError(Exception):
    # This exception is raised when a network error occurs
    pass


class UnknownError(Exception):
    # This exception is raised when an unknown error occurs
    pass


class SSHConnectionError(SSHError):
    # This exception is raised when an error occurs during SSH connection
    pass


class SSHAuthenticationError(SSHError):
    # This exception is raised when an error occurs during an SSH authentication
    pass


class SSHAlreadyConnectedError(SSHError):
    # This exception is raised when an SSH connection is already established
    pass


class ExecuteCommandError(SSHError):
    # This exception is raised when an error occurs during command execution
    pass


class SCPConnectionError(SCPError):
    # This exception is raised when an error occurs during SCP connection
    pass


class SCPAlreadyConnectedError(SCPError):
    # This exception is raised when an SCP connection is already established
    pass


class SCPTransferError(SCPError):
    # This exception is raised when an error occurs during SCP file transfer
    pass


class SSHConnect:
    def __init__(self):

        self.ssh_session = None
        self.scp_session = None

        self.ssh_connection_status = 1
        self.scp_connection_status = 1

    def ssh_connect(self, hostname, username, ssh_key_path, force_connect=False):
        """
        ssh_connect Function:

        The ssh_connect function is used to connect to a given SSH host.

        Call this function with a hostname, username and SSH key and it will attempt to connect to that device. In order to
        establish a new connection when one is already open then set the force_connect parameter to True.

        Usage:
        ssh_session = SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")

        Raises:
        SSHConnectionError: If the SSH connection fails
        NetworkError: If a network error occurs
        UnknownError: If an unknown error occurs
        """

        print(f"Attempting to establish an SSH connection to {hostname}")

        if self.ssh_connection_status == 2 and not force_connect:
            print("Already connected to SSH session")
            raise SSHAlreadyConnectedError("SSH Connection already established")

        self.ssh_session = paramiko.SSHClient()
        self.ssh_session.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        max_connection_attempts = 2
        retry_delay = 1

        last_exception = None

        for connection_attempts in range(max_connection_attempts):
            try:
                if ssh_key_path:
                    self.ssh_session.connect(hostname=hostname, username=username, key_filename=ssh_key_path)
                elif not ssh_key_path:
                    print("Attempting SSH connection without SSH Key")
                    with suppress(paramiko.ssh_exception.AuthenticationException):
                        self.ssh_session.connect(hostname=hostname, username=username, password='')
                    self.ssh_session.get_transport().auth_none(username)
                print("SSH Connection Successful")
                self.ssh_connection_status = 2
                return self.ssh_session

            except paramiko.ssh_exception.AuthenticationException:
                print("Authentication failed, please verify your credentials.")
                raise SSHAuthenticationError("Authentication failed, verify SSH Key and credentials")

            except OSError as e:
                last_exception = e
                if e.errno == errno.ENETUNREACH:
                    print(f"Network is unreachable, reconnection attempt {connection_attempts + 1}"
                          f" of {max_connection_attempts}.")
                elif e.errno == 10065:
                    print(f"The host is unreachable, reconnection attempt {connection_attempts + 1}"
                          f" of {max_connection_attempts}.")
                else:
                    print(f"Socket error: {e}, reconnection attempt {connection_attempts + 1}"
                          f" of {max_connection_attempts}.")

            except paramiko.SSHException as e:
                last_exception = e
                print(f"SSH Exception occurred: {e}, reconnection attempt {connection_attempts + 1}"
                      f" of {max_connection_attempts}.")

            except Exception as e:
                last_exception = e
                print(f"An unexpected error occurred: {e}")

            if connection_attempts < max_connection_attempts - 1:
                print(
                    f"Connection attempt {connection_attempts + 1} of {max_connection_attempts} failed."
                    f" Retrying in {retry_delay} seconds.")
                sleep(retry_delay)

        if isinstance(last_exception, OSError):
            self.ssh_connection_status = 0
            raise NetworkError(f"Network error occurred: {last_exception}")
        elif isinstance(last_exception, paramiko.SSHException):
            self.ssh_connection_status = 0
            raise SSHConnectionError(f"SSH Connection failed: {last_exception}")
        else:
            self.ssh_connection_status = 0
            raise UnknownError(
                f"SSH Connection failed due to an unknown reason after {max_connection_attempts} attempts:"
                f" {last_exception}")

    def ssh_disconnect(self):
        """
        ssh_disconnect Function:

        The ssh_disconnect function is used to disconnect from a connected SSH host.

        Call this function, and it will attempt to close the open SSH session.

        Usage:
        connection, return_code = SSHConnect.ssh_disconnect()

        Raises:
        SSHConnectionError: If the SSH disconnection fails
        """

        print("Attempting to disconnect SSH Connection")
        try:
            if self.ssh_connection_status == 2:
                self.ssh_session.close()
                self.ssh_connection_status = 1
                self.ssh_session = None
                print(f"SSH session successfully closed. SSH Connection Status Code: "
                      f"{self.ssh_connection_status}")
            elif self.ssh_connection_status in (0, 1):
                print(f"SSH not connected, cannot disconnect. SSH Connection Status Code:"
                      f" {self.ssh_connection_status}")
                raise SSHConnectionError("SSH Disconnection failed: No SSH session to close")
        except (paramiko.SSHException, OSError) as e:
            print(f"An error occurred while closing the SSH connection: {e}")
            raise SSHConnectionError(f"SSH Disconnection failed: {e}")

    def scp_connect(self):
        """
        scp_connect Function:

        The scp_connect function is used to connect to a given SSH host.

        First call the ssh_connect function and then call scp_connect in order to push/pull files to and from the remote

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")

        scp_session = SSHConnect.scp_connect()

        Raises:
        SCPConnectionError: If the SCP connection fails
        """

        print("Attempting to establish the SCP connection")
        try:
            if self.ssh_connection_status == 2:
                if self.ssh_session:
                    self.scp_session = SCPClient(self.ssh_session.get_transport())
                    self.scp_connection_status = 2
                    print(f"Successfully connected to SCP server. SCP Connection Status Code: "
                          f"{self.scp_connection_status}")
                    return self.scp_session
            else:
                self.scp_connection_status = 0
                print(f"Not connected to SSH session, cannot connect to SCP server. SCP Connection Status Code: "
                      f"{self.scp_connection_status}")
                raise SCPConnectionError("SCP Connection failed: No SSH session available")
        except (paramiko.SSHException, OSError) as e:
            self.scp_connection_status = 0
            print(f"An error occurred while opening the SCP connection. SCP Connection Status Code: "
                  f"{self.scp_connection_status} Exception: {e}")
            raise SCPConnectionError(f"SCP Connection failed: {e}")
        except Exception as e:
            self.scp_connection_status = 0
            print(f"An unexpected error occurred while attempting SCP connection. SCP Connection Status Code: "
                  f"{self.scp_connection_status} Exception: {e}")
            raise SCPConnectionError(f"SCP Connection failed: {e}")

    def scp_disconnect(self):
        """
        scp_disconnect Function:

        The scp_disconnect function is used to disconnect from a connected SSH host.

        Call this function, and it will attempt to close the open scp session.

        Usage:
        SSHConnect.scp_disconnect()

        Raises:
        SCPConnectionError: If the SCP disconnection fails
        """

        print("Attempting to disconnect SCP connection")
        try:
            if self.scp_connection_status == 2:
                self.scp_session.close()
                self.scp_connection_status = 1
                self.scp_session = None
                print(f"SCP session successfully closed. SCP Connection Status Code: {self.scp_connection_status}")
            elif self.scp_connection_status in (0, 1):
                print(f"SCP not connected, cannot disconnect. SCP Connection Status Code: {self.scp_connection_status}")
                raise SCPConnectionError("SCP Disconnection failed: No SCP session to close")
        except (paramiko.SSHException, OSError) as e:
            print(f"An error occurred while closing the SCP connection: SCP Connection Status Code: "
                  f"{self.scp_connection_status} Exception: {e}")
            raise SCPConnectionError(f"SCP Disconnection failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while attempting SCP connection. SCP Connection Status Code: "
                  f"{self.scp_connection_status} Exception: {e}")
            raise SCPConnectionError(f"SCP Disconnection failed for an unknown reason: {e}")

    def disconnect_all(self):
        """
        disconnect_all Function:

        The disconnect_all function is used to disconnect from any connected SSH and SCP hosts.

        Call this function, and it will attempt to close the open SSH and SCP sessions.

        Usage:
        SSHConnect.disconnect_all()

        Raises:
        SSHError: If an error occurs during disconnection
        """

        try:
            if self.scp_connection_status == 2:
                self.scp_disconnect()

            if self.ssh_connection_status == 2:
                self.ssh_disconnect()

            print(f"Successfully disconnected from SSH and SCP connections. "
                  f"SSH Connection Status: {self.ssh_connection_status} "
                  f"SCP Connection Status: {self.scp_connection_status}")

        except (SCPConnectionError, SSHConnectionError) as e:
            raise SSHError(f"An error occurred when disconnecting all sessions: {e}")


class SSHCommands(SSHConnect):
    def __init__(self):
        super().__init__()

    def execute_command(self, command, parse):
        """
        execute_command Function:

        This function is used to execute a command through the connected SSH session

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")

        SSHCommands.execute_command("ls /mnt/internal_slot1")

        Raises:
        ExecuteCommandError: If the command execution fails
        """

        if self.ssh_connection_status == 2:
            print(f"Attempting to Execute Command: {command}")
            self.ssh_session.exec_command(command)
            print(f"Successfully Executed Command: {command}, without reading lines")
        elif self.ssh_connection_status in (0, 1):
            print(f"SSH not connected, cannot execute command. SSH Connection Status Code: "
                  f"{self.ssh_connection_status}")
            raise ExecuteCommandError("SSH Command execution failed: No SSH session available")

    def execute_command_with_output(self, command):
        """
        execute_command_with_output Function:

        This function is used to execute a command through the connected SSH session and return the output

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")

        output = SSHCommands.execute_command_with_output("ls /mnt/internal_slot1")

        Raises:
        ExecuteCommandError: If the command execution fails
        """

        if self.ssh_connection_status == 2:
            print(f"Attempting to Execute Command: {command} and read the output")
            stdin, stdout, stderr = self.ssh_session.exec_command(command, get_pty=True)
            stdout.channel.set_combine_stderr(True)
            output = stdout.readlines()

            print(f"Successfully Executed Command: {command} and read the output")

            if not output:
                raise ExecuteCommandError("The command did not return any output")

            output = [s.replace("\n", "").replace("\r", "") for s in output]
            print(f"Output of {command}: {output}")

            return output

    def execute_command_with_exit_status(self, command):
        """
        execute_command_with_exit_status Function:

        This function is used to execute a command through the connected SSH session and return the output and exit
        status

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")

        output, exit_status = SSHCommands.execute_command_with_output("ls /mnt/internal_slot1")

        Raises:
        ExecuteCommandError: If the command execution fails
        """

        if self.ssh_connection_status == 2:
            print(f"Attempting to Execute Command: {command} and read the output and exit status")
            stdin, stdout, stderr = self.ssh_session.exec_command(command, get_pty=True)
            stdout.channel.set_combine_stderr(True)
            output = stdout.readlines()
            stdin.close()
            stdout.channel.shutdown_write()
            exit_status = stdout.channel.recv_exit_status()

            print(f"Successfully Executed Command: {command}")

            if not output:
                raise ExecuteCommandError("The command did not return any output")

            output = [s.replace("\n", "").replace("\r", "") for s in output]
            print(f"Output of {command}: {output}")

            if not exit_status:
                raise ExecuteCommandError("The command did not return an exit status")

            return output, exit_status


class SCPFileTransfer(SSHConnect):
    def __init__(self):
        super().__init__()

    def push_file(self, local_path, remote_path):
        """
        push_file Function:

        This function is used to push a file to a remote host

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")
        SSHConnect.scp_connect()

        local_path = "./test.txt"
        remote_path = "/mnt/internal_slot1/"

        SCPFileTransfer.push_file(local_path, remote_path)

        Raises:
        SCPTransferError: If the SCP transfer fails
        """

        local_path = local_path
        remote_path = remote_path

        print(f"Attempting to push {local_path} to {remote_path}")

        if self.scp_connection_status != 2:
            print(f"Not connected to SCP. SCP Connection Status Code: {self.scp_connection_status}")
            raise SCPConnectionError("There is no established SCP connection")

        try:
            print(f"Pushing {local_path} to {remote_path}")
            self.scp_session.put(local_path, remote_path)
            print(f"Successfully pushed {local_path} to {remote_path}")
        except FileNotFoundError:
            print(f"Local file ({local_path}) not found.")
            raise SCPTransferError("Local file not found")
        except PermissionError:
            print(f"Permission denied when accessing {local_path} or writing to {remote_path}.")
            raise SCPTransferError("Permission denied")
        except TimeoutError:
            print("SCP operation timed out.")
            raise SCPTransferError("SCP operation timed out")
        except OSError as e:
            print(f"OS error during SCP operation: {e}")
            raise SCPTransferError("Unknown OS error")
        except SCPException as e:
            print(f"Remote Path ({remote_path}) does not exist. SCP Exception: {e}")
            raise SCPTransferError("Remote path does not exist")
        except paramiko.SSHException as e:
            print(f"SSH Connection Failed during SCP Put. SCP Exception: {e}")
            raise SCPTransferError("SSH Connection failed during SCP Put")
        except Exception as e:
            print(f"An unexpected exception occurred during SCP Put. SCP Exception: {e}")
            raise SCPTransferError("Unexpected exception occurred during SCP Put")

    """
        pull_file Function:

        This function is used to pull a file from a remote host

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")
        SSHConnect.scp_connect()

        local_path = "./"
        remote_path = "/mnt/internal_slot1/test.txt"

        connection, return_code = SCPFileTransfer.pull_file(local_path, remote_path)
        if return_code == 1013:
            print(f"Pulled {remote_path} to {local_path}")
        else:
            print("An error occurred whilst pulling file from remote")
    """

    def pull_file(self, local_path, remote_path):
        """
        pull_file Function:

        This function is used to pull a file from a remote host

        Usage:
        SSHConnect.ssh_connect(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")
        SSHConnect.scp_connect()

        local_path = "./"
        remote_path = "/mnt/internal_slot1/test.txt"

        SCPFileTransfer.pull_file(local_path, remote_path)

        Raises:
        SCPTransferError: If the SCP transfer fails
        """

        local_path = local_path
        remote_path = remote_path

        print(f"Attempting to pull {remote_path} to {local_path}")

        if self.scp_connection_status != 2:
            print(f"Not connected to SCP. SCP Connection Status Code: {self.scp_connection_status}")
            raise SCPConnectionError("There is no established SCP connection")

        try:
            self.scp_session.get(remote_path, local_path)
            print(f"Successfully pulled {remote_path} to {local_path}")
        except SCPException as e:
            print(
                f"SCP error occurred: {e}. Possible causes include the remote file not existing or permission issues.")
            raise SCPTransferError("Unknown SCP error occurred")
        except paramiko.SSHException as e:
            print(f"SSH error during SCP operation: {e}")
            raise SCPTransferError("SSH error occurred during SCP operation")
        except PermissionError:
            print(f"Permission denied when writing to {local_path}.")
            raise SCPTransferError("Permission denied")
        except FileNotFoundError:
            print(f"Local path {local_path} does not exist.")
            raise SCPTransferError("Local path does not exist")
        except TimeoutError:
            print("SCP operation timed out.")
            raise SCPTransferError("SCP operation timed out")
        except OSError as e:
            print(f"OS error during SCP operation: {e}")
            raise SCPTransferError("Unknown OS error")
        except Exception as e:
            print(f"Unexpected error during SCP operation: {e}")
            raise SCPTransferError("Unexpected error occurred during SCP operation")


class SSHHandler(SSHCommands, SCPFileTransfer):
    """
    SSHHandler Class:

    This class is used to handle SSH and SCP operations.

    Initialise this class with hostname, username and SSH key. On initialisation the SSHHandler will automatically
    connect to the target device.

    Usage:
    SSHHandler = SSHHandler(hostname="198.18.0.171", username="root", ssh_key_path="./axiom_rsa.key")
    SSHHandler.execute_command("reboot")
    """

    def __init__(self, hostname, ssh_key_path, username):
        super().__init__()

        self.ssh_connect(hostname, username, ssh_key_path)

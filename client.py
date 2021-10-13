# COMP9331 Term 1 2021: Assignment
# Python 3.7.3 CSE Machine

import time
from socket import *
import sys
import threading
import os

from network_tools import UDPServer, UDPClient

is_exit = False
is_shutdown = False
t_lock = threading.Condition()


class Client:
    def __init__(self, server_ip, server_port, client_udp_port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((server_ip, server_port))
        self.is_active = False
        self.username = None
        self.server_ip = server_ip
        self.client_udp_port = client_udp_port
        self.username_entered = False
        self.password_entered = False

    def send_msg(self, msg):
        self.socket.send(msg.encode('utf-8'))

    def receive_msg(self):
        return self.socket.recv(2048).decode('utf-8')

    def validate_username(self, username):
        self.username = username
        self.send_msg(f'VALIDATE_USERNAME {username}')
        return self.receive_msg()

    def validate_credentials(self, username, password):
        self.send_msg(f'VALIDATE_CREDENTIALS {username}-{password}-{self.server_ip}-{self.client_udp_port}')
        return self.receive_msg()

    def open_file_server(self):
        video_receiver = UDPServer(self.client_udp_port)
        video_receiver_thread = threading.Thread(target=video_receiver.listen, daemon=True)
        video_receiver_thread.start()

    def initiating_commands(self):
        arguments = []
        command = None
        commands_list = ['ATU', 'OUT']
        print(f'> Enter one of the following commands (MSG, DLT, EDT, RDM, ATU, OUT, UPD):')
        msg = input('> ')
        msg = msg.strip()
        if msg.startswith(tuple(commands_list)):
            command, *arguments = msg.split(' ')
        elif msg.startswith('MSG'):
            command, *msg_list = msg.split(' ')

            if len(msg_list) == 0:
                print('> A MSG body cannot be empty. Please try again.\n')
                arguments = []
            else:
                message = ' '.join(msg_list)
                arguments.append(message)
        elif msg.startswith('RDM'):
            command, *timestamp_list = msg.split(' ')

            if len(timestamp_list) == 0:
                print('> The RDM command needs a timestamp parameter. Please try again.\n')
                arguments = []
            else:
                timestamp = ' '.join(timestamp_list)
                arguments.append(timestamp)
        elif msg.startswith('EDT'):
            command, *args = msg.split(' ')

            if len(args) < 5:
                print('> Invalid number of arguments for EDT.\n')
            else:
                arguments.append(args[0])
                arguments.append(args[1:5])
                arguments.append(args[5:])

        elif msg.startswith('DLT'):
            command, *args = msg.split(' ')

            if len(args) != 5:
                print('> Invalid number of arguments for DLT.\n')
            else:
                arguments.append(args[0])
                arguments.append(args[1:])
        elif msg.startswith('UPD'):
            command, *args = msg.split(' ')

            if len(args) != 2:
                print('> Invalid number of arguments for UPD.\n')
            else:
                arguments.append(args[0])
                arguments.append(args[1])
        else:
            print('> Error. Invalid command!\n')

        return command, arguments

    # All functions for commands
    def download_active_users(self, command):
        self.send_msg(command)
        resp = self.receive_msg()

        print('>', resp)

    def exit(self, command):
        global is_exit
        self.send_msg(command)
        resp = self.receive_msg()

        if resp == 'ACKNOWLEDGED':
            self.is_active = False
            print(f'> Bye, {self.username}!')
            self.socket.close()
            is_exit = True

    def post_message(self, command, message_args):
        if len(message_args) > 0:
            message = message_args[0]

            self.send_msg(f'{command};{message}')
            resp = self.receive_msg()

            print('>', resp)

    def read_messages(self, command, timestamps_args):
        if len(timestamps_args) > 0:
            timestamp = timestamps_args[0]

            self.send_msg(f'{command};{timestamp}')
            resp = self.receive_msg()

            print('>', resp)

    def edit_message(self, command, args):
        if len(args) == 3:
            message_number = args[0]
            message_timestamp = ' '.join(args[1])
            new_message = ' '.join(args[2])

            self.send_msg(f'{command};{message_number};{message_timestamp};{new_message}')
            resp = self.receive_msg()

            print('>', resp)

    def delete_message(self, command, args):
        if len(args) == 2:
            message_number = args[0]
            message_timestamp = ' '.join(args[1])

            self.send_msg(f'{command};{message_number};{message_timestamp}')
            resp = self.receive_msg()

            print('>', resp)

    def upload_video(self, command, args):
        if len(args) == 2:
            recipient, filename = args

            # Check whether the user is online
            self.send_msg(f'{command};{recipient}')
            resp = self.receive_msg()

            if resp == 'OFFLINE':
                print(f'> {recipient} is currently offline. {filename} not sent.\n')
            else:
                # Indicates that the user is online. 
                # Check the existence of the sending file
                if os.path.exists(filename):
                    # Get the recipient IP address and UDP port number
                    recipient_ip, recipient_udp_port = resp.split(';')

                    udp_client = UDPClient(recipient_ip, recipient_udp_port)

                    # Sending both the filename and username to the send message UDP port
                    udp_client.send(f'{filename};{self.username}')
                    print(f'{filename} has been uploaded.\n')
                else:
                    print(f'> File Not Found! Please ensure that {filename} exists in your directory.\n')

    def run(self):
        global is_exit
        global is_shutdown

        while self.is_active is False:
            if self.username_entered is False:
                print('\n')
                print('*' * 30)
                print('Login Portal')
                print('*' * 30)
                print('\n')
                username = input('> Username: ')

                # Username cannot be blank. If user enters a blank username, they will be asked to provide the
                # username again.
                if username.strip() == '':
                    print('The username cannot be empty. Please type the username again.')
                    continue
                else:
                    username_validation_status = self.validate_username(username)

                    # Case where the username is already logged in and active.
                    if username_validation_status == 'ACTIVE_USERNAME':
                        print(
                            f'[STATUS] The username {username} is currently active. Please enter a different username.')
                        continue
                    # Case where the username is invalid. User will be asked to provide a valid username.
                    elif username_validation_status == 'INVALID_USERNAME':
                        print(f'[STATUS] The username {username} is invalid. Please enter a different name.')
                        continue
                    # Case where the username is valid. Move on to the validation the credentials (both username &
                    # password)
                    elif username_validation_status == 'VALID_USERNAME':
                        self.username_entered = True

            if self.password_entered is False:
                # Check if the username is valid, if valid it means that only the password is incorrect
                password = input('> Password: ')
                valid_credentials = self.validate_credentials(self.username, password)

                # Case where the user has provided an invalid password. Will be asked to provide password again until
                # the max attemp that the server set
                if valid_credentials == 'INVALID_CREDENTIALS':
                    print('> Invalid Password. Please try again.')
                    continue
                # Case the user has entered the maximum login attempt and the account is blocked.
                elif valid_credentials == 'ACCOUNT_LOCKED':
                    print('> Invalid Password. Your account has been blocked. Please try again later.')
                    self.socket.close()
                    os._exit(0)
                    break
                # Case where the user tries to log in again to the same account before the 10 second timeout ends.
                elif valid_credentials == 'ACCOUNT_LOCKED_LOGINS':
                    print('> Your account is blocked due to multiple login failures. Please try again later.')
                    self.socket.close()
                    os._exit(0)
                    break
                # Case where the user has provided valid crendentials. Move on to the next step.
                elif valid_credentials == 'VALID_CREDENTIALS':
                    print('\n')
                    print('*' * 30)
                    print(f'Hello, {self.username}! Welcome to Toom')
                    print('*' * 30)
                    print('\n')
                    self.password_entered = True
                    self.is_active = True
                    self.open_file_server()

        while self.is_active:
            try:
                command, arguments = self.initiating_commands()

                if command == 'ATU':
                    self.download_active_users(command)
                if command == 'OUT':
                    self.exit(command)
                    if is_exit is True:
                        os._exit(0)
                        break
                if command == 'MSG':
                    self.post_message(command, arguments)
                if command == 'RDM':
                    self.read_messages(command, arguments)
                if command == 'EDT':
                    self.edit_message(command, arguments)
                if command == 'DLT':
                    self.delete_message(command, arguments)
                if command == 'UPD':
                    self.upload_video(command, arguments)

            except BaseException as e:
                if is_exit is False:
                    print(f'Errors occurs: {e}')
                    continue
                else:
                    break

    def server_shutdown_detection(self):
        global is_exit
        global is_shutdown
        while True:
            try:
                if is_exit is False:
                    self.send_msg('IS_ALIVE')
                    _resp = self.receive_msg()
                else:
                    break
                time.sleep(1)
            except BaseException:
                is_shutdown = True
                print(f'\n[DISCONNECTED] Server disconnected...')
                break


if __name__ == '__main__':
    server_IP = sys.argv[1]
    server_port = int(sys.argv[2])
    client_udp_port = int(sys.argv[3])

    client_main = Client(server_IP, server_port, client_udp_port)
    server_shutdown_detection = Client(server_IP, server_port, client_udp_port)

    client_main_thread = threading.Thread(target=client_main.run, daemon=True)
    server_shutdown_detection_thread = threading.Thread(target=server_shutdown_detection.server_shutdown_detection,
                                                        daemon=True)
    try:
        client_main_thread.start()
        server_shutdown_detection_thread.start()

        server_shutdown_detection_thread.join()
    except BaseException as e:
        print(f'Error occurs: {e}')

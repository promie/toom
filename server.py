# COMP9331 Term 1 2021: Assignment
# Python 3.7.3 CSE Machine

from socket import *
from threading import Thread
import time
import os
import threading
import sys
import datetime

t_lock = threading.Condition()


class Server:
    def __init__(self, socket, number_of_consecutive_failed_attempts):
        self.client_connections = []
        self.socket = socket
        self.is_running = True
        self.credential_dict = self.get_credentials()
        self.active_users = []
        self.number_of_consecutive_failed_attempts = number_of_consecutive_failed_attempts
        self.login_attempts_users = []
        self.lockedout_users = []
        self.client_ip = None
        self.client_udp_port = None

    def get_credentials(self):
        try:
            global t_lock
            with t_lock:
                if os.path.exists('credentials.txt'):
                    with open('credentials.txt', 'r') as file:
                        credential_dict = {}
                        for ln in file:
                            split_credential = ln.rstrip().split(' ')
                            new_credential = [string for string in split_credential if string != ""]
                            credential_dict[new_credential[0]] = new_credential[1]
                        file.close()
                        t_lock.notify()
                        return credential_dict
                else:
                    print('Error: credentials.txt does not exist')
                    t_lock.notify()
                    return {}
        except BaseException as e:
            print(f'Error occurs: {e}')

    def run(self):
        self.accept_new_connection()
        while self.is_running:
            time.sleep(1)

    def accept_new_connection(self):
        client_connection = ClientConnection(self)
        if client_connection.socket is not None:
            self.client_connections.append(client_connection)


class ClientConnection:
    def __init__(self, server):
        self.server = server
        self.socket = None
        self.username = None
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def receive_msg(self):
        return self.socket.recv(2048).decode('utf-8')

    def send_msg(self, msg):
        self.socket.send(msg.encode('utf-8'))

    def close(self):
        self.socket.close()

    def validate_username(self, msg):
        _, usrname = msg.split(' ')
        username = usrname

        # Check to see if the username exists in the credential_dict dictionary
        if username in self.server.credential_dict:
            # Check to see if the user is already in a session
            if username in self.server.active_users:
                print(f'[STATUS] {username} already has an active session.')
                self.send_msg('ACTIVE_USERNAME')
            # User is valid and exists in the dictionary
            else:
                self.username = username
                print(f'[STATUS] {username} is initiating a connection...')
                self.send_msg('VALID_USERNAME')
        else:
            print(f'[STATUS] {username} is an invalid username')
            self.send_msg('INVALID_USERNAME')

    # A function to remove a user from a lockout list after 10 seconds.
    def remove_user_from_lockout(self, username):
        try:
            time.sleep(10)
            self.server.lockedout_users.remove(username)
        except ValueError:
            return

    def format_user_logs(self, sequence, timestamp, username, client_ip, client_udp_port):
        return f'{sequence}; {timestamp}; {username}; {client_ip}; {client_udp_port}'

    def format_users_message_log(self, sequence, timestamp, username, message, edited):
        return f'{sequence}; {timestamp}; {username}; {message}; {edited}'

    def log_user_session(self):
        userlog_file = 'userlog.txt'
        current_timestamp = time.strftime('%d %b %Y %H:%M:%S')

        # Check to see the existence of the log file. If it doesn't exist create it.
        # Format: 1; 19 Feb 2021 21:30:04; yoda; 129.64.1.11; 6666
        if not os.path.exists(userlog_file):
            with open(userlog_file, 'w') as f:
                f.write(self.format_user_logs('1', current_timestamp, self.username, self.server.client_ip,
                                              self.server.client_udp_port))
            print(f'[LOG] {self.username} logged to userlog.txt')
        else:
            next_sequence = 1

            # Otherwise, open the file and increment the next sequence
            with open(userlog_file, 'r') as f:
                for _ in f:
                    next_sequence += 1

            # Append the username to the user log
            with open(userlog_file, 'a') as f:
                f.write('\n')
                f.write(self.format_user_logs(next_sequence, current_timestamp, self.username, self.server.client_ip,
                                              self.server.client_udp_port))
            print(f'[LOG] {self.username} logged to userlog.txt')

    def validate_credentials(self, msg):
        _, args = msg.split(' ')
        username, password, client_ip, client_udp_port = args.split('-')

        # Assigning the client ip address and UDP port
        self.server.client_ip = client_ip
        self.server.client_udp_port = int(client_udp_port)

        # Validating both that that the username and password matches the credentials dictionary
        is_credential_valid = (username, password) in self.server.credential_dict.items()

        # Check the credentials to see if the username exists in the lockedout_users list
        if username in self.server.lockedout_users:
            self.send_msg('ACCOUNT_LOCKED_LOGINS')
            # Wait ten seconds and remove the username from the lockedout_users list
            self.remove_user_from_lockout(username)

        # Upon successful login
        elif is_credential_valid:
            self.send_msg('VALID_CREDENTIALS')
            self.server.active_users.append(self.username)
            self.server.client_connections.append(self)
            print(f'[NEW CONNECTION] {username} connected')

            # Log user session to the userlog.txt file
            self.log_user_session()

        # If username and password do not match
        else:
            # Push the loggedin user into a list
            self.server.login_attempts_users.append(self.username)

            # If the login attempts meets the number of consecutive failed attempts
            if self.server.login_attempts_users.count(
                    self.username) == self.server.number_of_consecutive_failed_attempts:
                self.send_msg('ACCOUNT_LOCKED')
                # Add the username to the lockedout_users list
                self.server.lockedout_users.append(username)
                # Remove the lockedin user from the login_attempts list

                for name in self.server.login_attempts_users:
                    if name == username:
                        self.server.login_attempts_users.remove(name)

                print(f'[STATUS] {username} account has been blocked for 10 seconds.')

                # Wait ten second and remove this user from the lockout list.
                self.remove_user_from_lockout(username)
            else:
                self.send_msg('INVALID_CREDENTIALS')
                print(f'[STATUS] {username} login attempts failed.')

    def print_active_users_server(self, active_users_msg):
        if len(active_users_msg) > 0:
            print('> Return active user list:')
            for users_list in active_users_msg:
                for user in users_list:
                    print(user.replace('>', ';'))
        else:
            print('> No other active user.')

    def send_active_users_to_client(self, active_users_msg):
        if len(active_users_msg) > 0:
            users = ''
            for users_list in active_users_msg:
                for user in users_list:
                    users += f"{user.replace('>', ',')}\n"

            return users
        else:
            return 'No other active user.\n'

    def is_date_format_correct(self, date_text):
        try:
            datetime.datetime.strptime(date_text, '%d %b %Y %H:%M:%S')
            return True
        except ValueError:
            return False

    def is_message_number_correct(self, message_number):
        return message_number.startswith('#') and message_number[1:].isnumeric()

    def strip_last_line_txt_file(self, txt_file):
        with open(txt_file, 'r') as f:
            data = f.read()
            with open(txt_file, 'w') as w:
                w.write(data[:-1])

    def remove_user_from_log(self):
        new_sequence = 0
        userlog_file = 'userlog.txt'

        # Check that file is not empty. If file is empty then remove it.
        with open(userlog_file, 'r') as f:
            lines = f.readlines()
        with open(userlog_file, 'w') as f:
            for line in lines:
                _, tmp, user, client_ip, client_udp_port = line.strip('\n').split('; ')

                if user != self.username:
                    new_sequence += 1
                    f.write(f'{new_sequence}; {tmp}; {user}; {client_ip}; {client_udp_port}\n')

        self.strip_last_line_txt_file(userlog_file)

        # Check how many active usersare currently in the userlog file
        with open(userlog_file, 'r') as f:
            nl = f.readlines()

        # Remove the file if there's no more active users in the userlog
        if len(nl) == 0:
            os.remove(userlog_file)

    # All functions for commands
    def download_active_users(self):
        userlog_file = 'userlog.txt'
        active_users_msg = []

        with open(userlog_file, 'r') as f:
            for user in f:
                _sequence_no, timestamp, username, client_ip, client_udp_port = user.split('; ')

                # If the username match then continue without pushing the value in to the active users lists
                if username == self.username:
                    continue
                else:
                    # Only include the information 
                    active_users_msg.append([
                                                f'{username.strip()}> {client_ip.strip()}> {client_udp_port.strip()}> active since {timestamp.strip()}.'])

        # Print out on the server side the list of active users (excluding the logged in users)
        self.print_active_users_server(active_users_msg)
        # Send the list of active_users_msg to the client
        self.send_msg(self.send_active_users_to_client(active_users_msg))

    def exit(self):
        # Remove the current user from active_user_list
        self.server.active_users.remove(self.username)
        self.send_msg('ACKNOWLEDGED')

        # Remove the current session from clients_connections
        current_connection = next(conn for conn in self.server.client_connections if conn.username == self.username)
        current_connection.close()

        self.server.client_connections.remove(current_connection)

        # Remove the user from the userlog file
        self.remove_user_from_log()
        print(f'> {self.username} logout')

    def post_message(self, msg):
        _command, message = msg.split(';')
        messagelog_file = 'messagelog.txt'
        current_timestamp = time.strftime('%d %b %Y %H:%M:%S')

        if not os.path.exists(messagelog_file):
            with open(messagelog_file, 'w') as f:
                f.write(self.format_users_message_log('1', current_timestamp, self.username, message, 'no'))
            print(f'> {self.username} posted MSG #1 "{message}" at {current_timestamp}')
            self.send_msg(f'Message #1 posted at {current_timestamp}\n')
        else:
            msg_sequence_main = 1
            numbers_of_users_message = 1

            with open(messagelog_file, 'r') as f:

                for line in f:
                    # Increment the sequence number to append to the message log file
                    msg_sequence_main += 1

                    _sequence, _timestamp, username, _message, _edited = line.split('; ')

                    # Check that the username and the author of the message that was posted are the same person
                    if username == self.username:
                        # Add the messages to the numbers_of_users_list
                        numbers_of_users_message += 1

            # If the author currently has no previous messages then write to the log file with the MSG #1
            if numbers_of_users_message == 1:
                with open(messagelog_file, 'a') as f:
                    f.write('\n')
                    f.write(self.format_users_message_log(msg_sequence_main, current_timestamp, self.username, message,
                                                          'no'))
                print(f'> {self.username} posted MSG #1 "{message}" at {current_timestamp}')
                self.send_msg(f'Message #1 posted at {current_timestamp}\n')
            # If the author current has other previous messages, then the print and send message to client will
            # increment.
            else:
                with open(messagelog_file, 'a') as f:
                    f.write('\n')
                    f.write(self.format_users_message_log(msg_sequence_main, current_timestamp, self.username, message,
                                                          'no'))
                print(f'> {self.username} posted MSG #{numbers_of_users_message} "{message}" at {current_timestamp}')
                self.send_msg(f'Message #{numbers_of_users_message} posted at {current_timestamp}\n')

    def read_messages(self, msg):
        _command, timestamp = msg.split(';')
        messagelog_file = 'messagelog.txt'
        users_messages_logs = []
        users_messages_logs_server = []

        # Validate the date to ensure that the client has sent the correct date format
        if self.is_date_format_correct(timestamp) is False:
            print(f'> {self.username} entered the incorrect date format.')
            return self.send_msg(
                'RDM Timestamp is incorrect. Please enter your time in the following format example: 11 Dec 2020 '
                '17:24:00\n')

        # Check if the file exists, if not then send the mesage to client and print to server that there are no messages
        if not os.path.exists(messagelog_file):
            print(f'> {self.username}: No new message')
            return self.send_msg('No new message\n')

        # Open up the file and loop through all the messages .
        with open(messagelog_file, 'r') as f:
            for line in f:
                sequence_number, tmpstamp, usrname, msg, edited = line.split('; ')

                is_msg_edited = 'posted' if edited.strip() == 'no' else 'edited'

                # Comparing the timestamp in the messages
                if tmpstamp >= timestamp:
                    # Build the string to return to the client
                    users_messages_logs.append(f'#{sequence_number}; {usrname}: "{msg}" {is_msg_edited} at {tmpstamp}.')
                    # Build the string to print on the server
                    users_messages_logs_server.append(
                        f'#{sequence_number} {usrname}: "{msg}" {is_msg_edited} at {tmpstamp}.')

        # If the users message logs remains empty. It means that the date entered by the client is in the messagelog
        # file
        if len(users_messages_logs) == 0:
            print(f'> {self.username}: No new message')
            return self.send_msg('No new message\n')

        # Combine all the users logs based on the timestamp comparisons and send the response to client
        users_messages_response = '\n\n'.join(users_messages_logs)
        self.send_msg(f'{users_messages_response}\n')

        # Print to server the RDM status
        users_messages_response_server = '\n\n'.join(users_messages_logs_server)
        print('> Return messages')
        print(f'{users_messages_response_server}')

    def edit_message(self, msg):
        messagelog_file = 'messagelog.txt'
        _command, message_number, message_timestamp, new_message = msg.split(';')
        message_num_match = False
        message_timestamp_match = False
        message_author_match = False
        current_timestamp = time.strftime('%d %b %Y %H:%M:%S')

        # Validate to ensure that the client has sent through the valid message number
        if self.is_message_number_correct(message_number) is False:
            print(f'> {self.username} has entered an invalid message number.')
            return self.send_msg(
                'Message number format incorrect. The correct message number starts with a # (e.g. #1, #3). Please '
                'try again.\n')

        # Validate to ensure that the client has sent through a valid message timestamp
        if self.is_date_format_correct(message_timestamp) is False:
            print(f'> {self.username} has entered an incorrect timestamp.')
            return self.send_msg('Message timestamp format incorrect. Please try again.\n')

        # validate to ensure that the message body is not empty
        if new_message == '':
            print(f'> {self.username} did not provide a message with the body to edit message.')
            return self.send_msg('There is no body with the new message to edit. Please try again.\n')

        # Check if there is the messagelog file before attempting to edit
        if not os.path.exists(messagelog_file):
            print(f'> {self.username}: No message to edit.')
            return self.send_msg('No message to edit.\n')

        # Loop through the message log file and find the message with the message number
        with open(messagelog_file, 'r') as f:
            for line in f:
                sequence_number, tmpstamp, usrname, msg, _edited = line.split('; ')

                if f'#{sequence_number}' == message_number:
                    message_num_match = True
                    if tmpstamp == message_timestamp:
                        message_timestamp_match = True
                        if self.username == usrname:
                            message_author_match = True

        # If there is no message number match, inform the client
        if message_num_match is False:
            print(f'> {self.username}: Message number {message_number} does not exist on the messagelog.txt file.')
            return self.send_msg(f'Message number {message_number} does not exist on the messagelog.txt file.\n')

        # If there is a message number, but the timestamp does not match
        if message_num_match is True and message_timestamp_match is False:
            print(f'> {self.username}: Timestamp for message number {message_number} does not match.')
            return self.send_msg(f'Timestamp for message number {message_number} does not match.\n')

        # If the message number match, the timestamp match, but the author does not match
        if message_num_match is True and message_timestamp_match is True and message_author_match is False:
            print(
                f'> {self.username} attempts to edit MSG {message_number} at {current_timestamp}. Authorisation fails.')
            return self.send_msg(f'Unauthorised to edit message {message_number}.\n')

        # If all checks pass, go ahead and make the edit: Replace new message, switch edited flag and add new timestamp.
        if message_num_match is True and message_timestamp_match is True and message_author_match is True:
            # Write to file
            with open(messagelog_file, 'r') as f:
                lines = f.readlines()
            with open(messagelog_file, 'w') as f:
                for line in lines:
                    seq, tmp, author, msg, edited = line.strip('\n').split('; ')

                    if f'#{seq}' == message_number:
                        f.write(f'{seq}; {current_timestamp}; {author}; {new_message}; yes\n')
                    else:
                        f.write(f'{seq}; {tmp}; {author}; {msg}; {edited}\n')

            # Strip the last time from the text file
            self.strip_last_line_txt_file(messagelog_file)

            # Notify the server and client that the edit is complete
            print(f'> {self.username} edited MSG {message_number} "{new_message}" at {current_timestamp}.')
            return self.send_msg(f'MSG {message_number} edited at {current_timestamp}.\n')

    def delete_message(self, msg):
        messagelog_file = 'messagelog.txt'
        _command, message_number, message_timestamp = msg.split(';')
        message_num_match = False
        message_timestamp_match = False
        message_author_match = False
        current_timestamp = time.strftime('%d %b %Y %H:%M:%S')

        # Validate to ensure that the client has sent through the valid message number
        if self.is_message_number_correct(message_number) is False:
            print(f'> {self.username} has entered an invalid message number. Message delete unsuccessful.')
            return self.send_msg(
                'Message number format incorrect. The correct message number starts with a # (e.g. #1, #3). Message delete unsuccessful.\n')

        # Validate to ensure that the client has sent through a valid message timestampe
        if self.is_date_format_correct(message_timestamp) is False:
            print(f'> {self.username} has entered an incorrect timestamp. Message delete unsuccessful.')
            return self.send_msg('Message timestamp format incorrect. Message delete unsuccessful.\n')

        # Check if there is the messagelog file before attempting to edit
        if not os.path.exists(messagelog_file):
            print(f'> {self.username}: No message to delete.')
            return self.send_msg('No message to delete.\n')

        # Loop through the message log file and find the message with the message number
        with open(messagelog_file, 'r') as f:
            for line in f:
                sequence_number, tmpstamp, usrname, msg, _edited = line.split('; ')

                if f'#{sequence_number}' == message_number:
                    message_num_match = True
                    if tmpstamp == message_timestamp:
                        message_timestamp_match = True
                        if self.username == usrname:
                            message_author_match = True

        # If there is no message number match, inform the client
        if message_num_match is False:
            print(f'> {self.username}: Message number {message_number} does not exist on the messagelog.txt file.')
            return self.send_msg(f'Message number {message_number} does not exist on the messagelog.txt file.\n')

        # If there is a message number, but the timestamp does not match
        if message_num_match is True and message_timestamp_match is False:
            print(f'> {self.username}: Timestamp for message number {message_number} does not match.')
            return self.send_msg(f'Timestamp for message number {message_number} does not match.\n')

        # If the message number match, the timestamp match, but the author does not match
        if message_num_match is True and message_timestamp_match is True and message_author_match is False:
            print(
                f'> {self.username} attempts to delete MSG {message_number} at {current_timestamp}. Authorisation fails.')
            return self.send_msg(f'Unauthorised to delete message {message_number}.\n')

        # If all checks pass, go ahead and make the delete.
        if message_num_match is True and message_timestamp_match is True and message_author_match is True:
            # New sequence number
            new_sequence = 0
            deleted_message = ''
            # If all checks pass, go ahead and make the edit: Replace new message, switch edited flag and add new timestamp.
            if message_num_match is True and message_timestamp_match is True and message_author_match is True:
                # Write to file
                with open(messagelog_file, 'r') as f:
                    lines = f.readlines()
                with open(messagelog_file, 'w') as f:
                    for line in lines:
                        seq, tmp, author, msg, edited = line.strip('\n').split('; ')

                        if f'#{seq}' == message_number:
                            deleted_message = msg
                        else:
                            new_sequence += 1
                            f.write(f'{new_sequence}; {tmp}; {author}; {msg}; {edited}\n')

                # Strip the last time from the text file
                self.strip_last_line_txt_file(messagelog_file)

                # Check how many messages in the message log
                with open(messagelog_file, 'r') as f:
                    nl = f.readlines()

                # Remove the file if the last message is deleted
                if len(nl) == 0:
                    os.remove(messagelog_file)

                # Notify the server and client that the edit is complete
                print(f'> {self.username} deleted MSG {message_number} "{deleted_message}" at {current_timestamp}.')
                return self.send_msg(f'MSG {message_number} deleted at {current_timestamp}.\n')

    def query_online_users(self, msg):
        _command, recipient = msg.split(';')
        userlog_file = 'userlog.txt'
        recipient_info = []

        with open(userlog_file, 'r') as f:
            for user in f:
                _sequence_no, _timestamp, username, recipient_ip, recipient_udp_port = user.split('; ')

                # Append the recipient_ip and recipient_udp_port to the recipient_info list
                if username == recipient:
                    recipient_info.append(recipient_ip)
                    recipient_info.append(recipient_udp_port)

        # If the recipient_info list is empty. It means the user is offline.
        if len(recipient_info) == 0:
            return self.send_msg('OFFLINE')
        else:
            # Send the info to the client
            return self.send_msg(';'.join(recipient_info))

    def run(self):
        client_socket, _addr = self.server.socket.accept()

        if client_socket is not None:
            self.socket = client_socket
            server.accept_new_connection()
        else:
            print('None')

        while True:
            msg = self.receive_msg()
            if msg.startswith('VALIDATE_USERNAME'):
                self.validate_username(msg)
            if msg.startswith('VALIDATE_CREDENTIALS'):
                self.validate_credentials(msg)
            if msg.startswith('ATU'):
                print(f'> {self.username} issued ATU command.')
                self.download_active_users()
            if msg.startswith('OUT'):
                print(f'> {self.username} issued OUT command.')
                self.exit()
                break
            if msg.startswith('MSG'):
                print(f'> {self.username} issued MSG command.')
                self.post_message(msg)
            if msg.startswith('RDM'):
                print(f'> {self.username} issued RDM command.')
                self.read_messages(msg)
            if msg.startswith('EDT'):
                print(f'> {self.username} issued EDT command.')
                self.edit_message(msg)
            if msg.startswith('DLT'):
                print(f'> {self.username} issued DLT command.')
                self.delete_message(msg)
            if msg.startswith('UPD'):
                self.query_online_users(msg)


if __name__ == '__main__':
    server_port = int(sys.argv[1])
    number_of_consecutive_failed_attempts = int(sys.argv[2])
    print('[STARTING] Server is starting...')

    socket = socket(AF_INET, SOCK_STREAM)
    socket.bind(('localhost', server_port))
    socket.listen(1)
    print(f'[LISTENING] Server is listening on Port: {server_port}')

    server = Server(socket, number_of_consecutive_failed_attempts)
    print(f'[STATUS] Waiting for clients connection...')

    server.run()

# Toom
Toom is a videoconferencing and messaging application. Toom is based on a client server model consisting of one server and multiple clients communicating concurrently. The text messages is communicated using TCP for the reason of reliability, while the video  is communicated using UDP for the reason of low latency. The app supports a range of functions that are typically found on videoconferencing including authentication, posting text messages to all participants and uploading video streams.

This project is part of an individual socket programming assignment for COMP9331 - Computer Networks and Applications.

**Marks: 20/20**

## Requirements
- Python v3.7 and above

## Usage

Run server.py with two parameters

```bash
$ python3 server.py server_port number_of_consecutive_failed_attempts
```

Run client.py with three parameters

```bash
$ python3 client.py server_IP server_port client_udp_server_port
```

After the program run, you will be asked to sign in with the credentials provided in the credentials.txt file.
For more details on how to interact with the program, please refer to the [report.pdf](https://github.com/promie/toom/blob/main/report.pdf) documentation.

from common.core import MessengerCore

def main():
    start_client = MessengerCore(start_client=True)
    start_client.start_client_send()
if __name__ == '__main__':
    main()
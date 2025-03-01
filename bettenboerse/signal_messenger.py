#from pathlib import Path
from pysignalclirestapi import SignalCliRestApi
from base64 import b64encode

from bettenboerse.settings import SIGNAL_CLI_API_URL, SIGNAL_CLI_PHONE_NUMBER


def get_signal_account():
    api = SignalCliRestApi(SIGNAL_CLI_API_URL, SIGNAL_CLI_PHONE_NUMBER)
    accounts = api.get_accounts()
    return next(iter(accounts), None)


def link_signal_account(device_name: str):
    api = SignalCliRestApi(SIGNAL_CLI_API_URL, SIGNAL_CLI_PHONE_NUMBER)
    png_bytes = api.link(device_name)
    return b64encode(png_bytes).decode()
    #with Path("qr-link.png").open("wb") as f:
    #    f.write(png_bytes)
    #print("QR code written to qr-link.png")


def send_signal_message(receiver: str, message: str):
    # receiver can be username or number or group id
    api = SignalCliRestApi(SIGNAL_CLI_API_URL, SIGNAL_CLI_PHONE_NUMBER)
    api.send_message(message, [receiver, ])




if __name__ == '__main__':
    #api = SignalCliRestApi(SIGNAL_CLI_API_URL, SIGNAL_CLI_PHONE_NUMBER)
    #accounts = api.get_accounts()
    #print(accounts)
    pass

from authenticator import Authman
import os

if __name__ == '__main__':
    auth = Authman()
    environment = os.environ
    if 'GLACIER_USER' in environment and 'GLACIER_PASSWORD' in environment:
        if environment['GLACIER_USER'] and environment['GLACIER_PASSWORD']:
            auth.add_user(environment['GLACIER_USER'], environment['GLACIER_PASSWORD'])

from authenticator import AuthManager
from config import UserAddConfig

if __name__ == '__main__':
    auth = AuthManager()
    config = UserAddConfig()
    auth.add_user(config.glacier_user, config.glacier_password)

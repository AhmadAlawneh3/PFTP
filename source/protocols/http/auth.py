"""HTTP Basic Authentication with conditional auth support"""

from flask_basicauth import BasicAuth


class PFTPBasicAuth(BasicAuth):
    """Custom BasicAuth that supports conditional auth"""

    def authenticate(self):
        if not self.app.config.get('AUTH_ENABLED'):
            return True
        return super().authenticate()

    def check_credentials(self, username, password):
        if username != self.app.config['BASIC_AUTH_USERNAME']:
            return False

        stored = self.app.config.get('AUTH_PASSWORD_HASH', '')
        return password == stored if stored else False

import os
import sys

from django.db.backends import BaseDatabaseClient

class DatabaseClient(BaseDatabaseClient):
    # TODO?..
    executable_name = 'mongod'

    def runshell(self):
        # TODO: port/connection/username/password
        args = [self.executable_name,
                self.connection.settings_dict['NAME']]
        if os.name == 'nt':
            sys.exit(os.system(" ".join(args)))
        else:
            os.execvp(self.executable_name, args)
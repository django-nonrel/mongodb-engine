from datetime import datetime
from subprocess import CalledProcessError, check_output


def get_current_year():
    return datetime.utcnow().year


def get_git_head():
    try:
        return check_output(['git', 'rev-parse', 'HEAD'])
    except CalledProcessError:
        pass
    except OSError, exc:
        if exc.errno != 2:
            raise

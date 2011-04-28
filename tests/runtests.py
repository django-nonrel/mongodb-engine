#!/usr/bin/python
import os
from types import ModuleType

def runtests(foo, settings='settings', extra=[]):
    if isinstance(foo, ModuleType):
        settings = foo.__name__
        apps = foo.INSTALLED_APPS
    else:
        apps = foo
    execute(['./manage.py', 'test', '--settings', settings] + extra + apps)


def main(short):
    # Run some basic tests outside Django's test environment
    execute(
        ['python', '-c', 'from query.models import Blog\n'
                         'Blog.objects.create()\n'
                         'Blog.objects.all().delete()\n'
                         'Blog.objects.update()'],
        env=dict(os.environ, DJANGO_SETTINGS_MODULE='settings', PYTHONPATH='..')
    )

    import settings
    import settings_dbindexer
    import settings_slow_tests

    runtests(settings, extra=['--failfast'] if short else [])

    if short:
        exit()

    # Make sure we can syncdb.
    execute(['./manage.py', 'syncdb', '--noinput'])

    runtests(settings_dbindexer)
    runtests(['router'], 'settings_router')
    runtests(settings.INSTALLED_APPS, 'settings_debug')
    runtests(settings_slow_tests)


if __name__ == '__main__':
    import sys
    if 'ignorefailures' in sys.argv:
        from subprocess import call as execute
    else:
        from subprocess import check_call as execute
    if 'coverage' in sys.argv:
        def _new_check_call_closure(old_check_call):
            def _new_check_call(cmd, **kwargs):
                if cmd[0] != 'python':
                    cmd = ['coverage', 'run', '-a', '--source',
                           '../django_mongodb_engine'] + cmd
                return old_check_call(cmd, **kwargs)
            return _new_check_call
        check_call = _new_check_call_closure(check_call)
    main('short' in sys.argv)

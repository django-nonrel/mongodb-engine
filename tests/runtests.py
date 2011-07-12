#!/usr/bin/env python
import os
import sys
from types import ModuleType

def runtests(foo, settings='settings', extra=[], test_builtin=False):
    if isinstance(foo, ModuleType):
        settings = foo.__name__
        apps = foo.INSTALLED_APPS
    else:
        apps = foo
    if not test_builtin:
        apps = filter(lambda name: not name.startswith('django.contrib.'), apps)
    apps = [app.replace('django.contrib.', '') for app in apps]
    execute(['./manage.py', 'test', '--settings', settings] + extra + apps)

def execute_python(lines):
    from textwrap import dedent
    return execute(
        [sys.executable, '-c',  dedent(lines)],
        env=dict(os.environ, DJANGO_SETTINGS_MODULE='settings', PYTHONPATH='..')
    )

def main(short):
    # Run some basic tests outside Django's test environment
    execute_python('''
        from mongodb.models import RawModel
        RawModel.objects.create()
        RawModel.objects.all().delete()
        RawModel.objects.update()
    ''')

    import settings
    import settings.dbindexer
    import settings.slow_tests

    runtests(settings, extra=['--failfast'] if short else [])

    # assert we didn't touch the production database
    execute_python('''
        from pymongo import Connection
        print Connection().test.mongodb_rawmodel.find()
        assert Connection().test.mongodb_rawmodel.find_one()['raw'] == 42
    ''')

    if short:
        exit()

    # Make sure we can syncdb.
    execute(['./manage.py', 'syncdb', '--noinput'])

    runtests(settings.dbindexer)
    runtests(['router'], 'settings.router')
    runtests(settings.INSTALLED_APPS, 'settings.debug')
    runtests(settings.slow_tests, test_builtin=True)


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

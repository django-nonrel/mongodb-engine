from . import *


TEST_DEBUG = True

LOGGING = {
    'version': 1,
    'formatters': {'simple': {'format': '%(levelname)s %(message)s'}},
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}

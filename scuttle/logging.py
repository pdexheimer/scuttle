# scuttle - manage and manipulate sc-rna data files
# Copyright (C) 2019 Phillip Dexheimer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
logging.py - This module is responsible for configuring scuttle logging
"""

import logging
import logging.config
import sys
import warnings

from colorama import Fore


class ColorizingFilter(logging.Filter):
    def filter(self, record):
        record.color = self._logColors[record.levelname]
        return True

    _logColors = {
        'CRITICAL': Fore.RED,
        'ERROR': Fore.RED,
        'WARNING': Fore.YELLOW,
        'INFO': Fore.GREEN,
        'DEBUG': Fore.WHITE
    }


def init():
    logConfig = {
        'version': 1,
        'formatters': {
            'default': {
                'format': f'[%(color)s%(levelname)s{Fore.RESET} %(asctime)s] %(message)s',
                'datefmt': '%H:%M:%S %Y-%m-%d'
            }
        },
        'filters': {
            'colorize': {
                '()': ColorizingFilter
            }
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'filters': ['colorize']
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['default']
        }
    }
    logging.config.dictConfig(logConfig)
    # RPy2 uses the warnings module and tends to spam.  Ignore it
    # https://docs.python.org/3/library/warnings.html#overriding-the-default-filter
    if not sys.warnoptions:
        warnings.simplefilter('ignore')

import logging
import os

import pandas as pd

from .. import utils
from ...garjus import Garjus


logger = logging.getLogger('dashboard.queue.data')


# This is where we save our cache of the data
def get_filename():
    datadir = f'{Garjus().cachedir()}/DATA'
    filename = f'{datadir}/queuedata.pkl'

    try:
        os.makedirs(datadir)
    except FileExistsError:
        pass

    return filename


def get_data(proj_filter, hidedone=True):
    g = Garjus()

    if not g.redcap_enabled():
        return None

    df = g.tasks(hidedone=hidedone)

    df = df[df.STATUS != 'NEED_INPUTS']

    df.reset_index(inplace=True)
    df['ID'] = df.index
    df['USER'] = 'vuiis_daily_singularity'
    df['LABEL'] = df['ASSESSOR']

    df = df.apply(_get_proctype, axis=1)

    return df


def _get_proctype(row):
    try:
        if row['YAMLUPLOAD']:
            tmp = os.path.basename(row['YAMLUPLOAD'])
        else:
            tmp = os.path.basename(row['YAMLFILE'])

        # Get just the filename without the directory path
        # Split on periods and grab the 4th value from right,
        # thus allowing periods in the main processor name
        row['PROCTYPE'] = tmp.rsplit('.')[-4]

    except (KeyError, IndexError):
        row['PROCTYPE'] = ''

    return row


def run_refresh(filename, hidedone=True):
    proj_filter = []

    df = get_data(proj_filter, hidedone=hidedone)

    utils.save_data(df, filename)

    return df


def load_data(refresh=False, hidedone=True):
    filename = get_filename()

    if refresh or not os.path.exists(filename):
        run_refresh(filename, hidedone)

    logger.info('reading data from file:{}'.format(filename))
    return utils.read_data(filename)


def filter_data(df, proj, proc, user):
    # Filter by project
    if proj:
        logger.debug(f'filtering by project:{proj}')
        df = df[df['PROJECT'].isin(proj)]

    # Filter by proc
    if proc:
        logger.debug(f'filtering by proc:{proc}')
        df = df[(df['PROCTYPE'].isin(proc))]

    # Filter by user
    if user:
        logger.debug(f'filtering by user:{user}')
        df = df[(df['USER'].isin(user))]

    return df

"""dash index page."""
import logging

from dash import html
import dash_bootstrap_components as dbc

from .app import app
from .pages import qa
from .pages import activity
from .pages import issues
from .pages import queue
from .pages import stats
from .pages import analyses
from .pages import processors
from .pages import reports
from ..garjus import Garjus


logger = logging.getLogger('garjus.dashboard')


def redcap_found():
    return Garjus.redcap_found()


def xnat_found():
    return Garjus.xnat_found()


footer_content = [
    html.Hr(),
    html.Div(
        [
            html.A(
                "garjus",
                href='https://github.com/ccmvumc/garjus',
                target="_blank",
            )
        ],
        style={'textAlign': 'center'},
    ),
]

has_xnat = xnat_found()
has_redcap = redcap_found()

if has_xnat and has_redcap:
    tabs = dbc.Tabs([
        dbc.Tab(
            label='QA',
            tab_id='tab-qa',
            children=qa.get_content(),
        ),
        dbc.Tab(
            label='Issues',
            tab_id='tab-issues',
            children=issues.get_content(),
        ),
        dbc.Tab(
            label='Queue',
            tab_id='tab-queue',
            children=queue.get_content(),
        ),
        dbc.Tab(
            label='Activity',
            tab_id='tab-activity',
            children=activity.get_content(),
        ),
        dbc.Tab(
            label='Stats',
            tab_id='tab-stats',
            children=stats.get_content(),
        ),
        dbc.Tab(
            label='Processors',
            tab_id='tab-processors',
            children=processors.get_content(),
        ),
        dbc.Tab(
            label='Reports',
            tab_id='tab-reports',
            children=reports.get_content(),
        ),
        dbc.Tab(
            label='Analyses',
            tab_id='tab-analyses',
            children=analyses.get_content(),
        ),
    ])
elif has_xnat and not has_redcap:
    tabs = html.Div(qa.get_content())
elif has_redcap and not has_xnat:
    tabs = dbc.Tabs([
        dbc.Tab(
            label='Issues',
            tab_id='tab-issues',
            children=issues.get_content(),
        ),
        dbc.Tab(
            label='Queue',
            tab_id='tab-queue',
            children=queue.get_content(),
        ),
        dbc.Tab(
            label='Activity',
            tab_id='tab-activity',
            children=activity.get_content(),
        ),
        dbc.Tab(
            label='Processors',
            tab_id='tab-processors',
            children=processors.get_content(),
        ),
        dbc.Tab(
            label='Reports',
            tab_id='tab-reports',
            children=reports.get_content(),
        ),
        dbc.Tab(
            label='Analyses',
            tab_id='tab-analyses',
            children=analyses.get_content(),
        ),
    ])

app.layout = html.Div(
    className='dbc',
    style={'marginLeft': '20px', 'marginRight': '20px'},
    children=[
        html.Div(id='report-content', children=[tabs]),
        html.Div(id='footer-content', children=footer_content)
    ])

# For gunicorn to work correctly
server = app.server

# Allow external css
app.css.config.serve_locally = False

# Set the title to appear on web pages
app.title = 'dashboard'

if __name__ == '__main__':
    app.run_server(host='0.0.0.0')

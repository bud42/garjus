import logging

import pandas as pd
from dash import dcc, html, dash_table as dt, Input, Output, callback
import dash_bootstrap_components as dbc

from .. import utils
from . import data

logger = logging.getLogger('dashboard.analyses')


#COMPLETE2EMO = {'0': '🔴', '1': '🟡', '2': '🟢'}

# command line examples for interacting with analyses
TIPS_MARKDOWN = '''
    &nbsp;

    ### Analyses Tips:

    &nbsp;

    To download all input files for analysis number NUM to folder INPUTS for project NAME, at command-line enter:  
    `garjus getinputs -p NAME NUM INPUTS`

    For example, to download inputs for analysis 1 from ProjectA to a local folder named INPUTS, enter:  
    `garjus getinputs -p ProjectA 1 ./INPUTS`

    &nbsp;

    To download the output zip for analysis number NUM to folder OUTPUTS for project NAME, at command-line enter:  
    `garjus getoutputs -p NAME NUM OUTPUTS`

    For example, to download outputs for analysis 1 from ProjectA to a local folder named OUTPUTS, enter:  
    `garjus getoutputs -p ProjectA 1 ./OUTPUTS`

    &nbsp;

    To run an analysis by downloading the inputs locally and saving the outputs locally:  
    `garjus run -p NAME NUM OUTPUTS.zip`

    For example, to run analysis 3 for project ProjectA and save outputs to zip:  
    `garjus run -p ProjectA 3 ProjectA_3_OUTPUTS.zip`

    &nbsp;

    To update analyses for a project, enter:  
    `garjus update analyses -p ProjectA`

    This will update each analyses by creating the inputs if already done,
    and if outputs does not exist, then it will run the analysis to create the outputs,
    upload a zip to project resources on XNAT, and finally create a link in the analysis record.  

    &nbsp;

'''

COLUMNS = [
    'PROJECT',
    'ID',
    'NAME',
    'EDIT',
    'STATUS',
    'PDF',
    'LOG',
    'DATA',
    'SUBJECTS',
    'INVESTIGATOR',
    'PROCESSOR',
    'NOTES'
]


def get_content():
    columns = utils.make_columns(COLUMNS)

    # Format columns with links as markdown text
    for i, c in enumerate(columns):
        if c['name'] in ['OUTPUT', 'EDIT', 'INPUT', 'DATA', 'PROCESSOR']:
            columns[i]['type'] = 'text'
            columns[i]['presentation'] = 'markdown'

    content = [
        dbc.Row(
            dbc.Col(
                dcc.Dropdown(
                    id='dropdown-analyses-proj',
                    multi=True,
                    placeholder='Select Project(s)',
                ),
                width=3,
            ),
        ),
        dbc.Row(
            dbc.Col(
                dcc.Dropdown(
                    id='dropdown-analyses-lead',
                    multi=True,
                    placeholder='Select Lead Investigator(s)',
                ),
                width=3,
            ),
        ),
        dbc.Row(
            dbc.Col(
                dcc.Dropdown(
                    id='dropdown-analyses-status',
                    multi=True,
                    placeholder='Select Status',
                ),
                width=3,
            ),
        ),
        dbc.Spinner(id="loading-analyses-table", children=[
            dbc.Label('Loading...', id='label-analyses-rowcount1'),
        ]),
        dt.DataTable(
            columns=columns,
            data=[],
            page_action='none',
            sort_action='none',
            id='datatable-analyses',
            style_cell={
                'textAlign': 'center',
                'padding': '15px 5px 15px 5px',
                'height': 'auto',
            },
            style_header={
                'fontWeight': 'bold',
            },
            style_cell_conditional=[
                {'if': {'column_id': 'NAME'}, 'textAlign': 'left'},
            ],
            # Aligns the markdown cells, both vertical and horizontal
            css=[dict(selector="p", rule="margin: 0; text-align: center")],
        ),
        html.Label('0', id='label-analyses-rowcount2'),
        dcc.Markdown(TIPS_MARKDOWN)
    ]

    return content


def load_analyses(projects=[]):

    if projects is None:
        projects = []

    return data.load_data(projects, refresh=True)


@callback(
    [
     Output('dropdown-analyses-proj', 'options'),
     Output('dropdown-analyses-lead', 'options'),
     Output('dropdown-analyses-status', 'options'),
     Output('datatable-analyses', 'data'),
     Output('label-analyses-rowcount1', 'children'),
     Output('label-analyses-rowcount2', 'children'),
    ],
    [
     Input('dropdown-analyses-proj', 'value'),
     Input('dropdown-analyses-lead', 'value'),
     Input('dropdown-analyses-status', 'value'),
    ])
def update_analyses(
    selected_proj,
    selected_lead,
    selected_status,
):
    logger.debug('update_all')

    # Load selected data with refresh if requested
    df = load_analyses(selected_proj)

    # Truncate NOTES
    if 'NOTES' in df:
        df['NOTES'] = df['NOTES'].str.slice(0, 20)

    # Count SUBJECTS list
    df.loc[df['SUBJECTS'].str.len() > 0, 'SUBJECTS'] = 'n=' + df['SUBJECTS'].str.split(r'[,\n\s]+', regex=True, expand=False).agg(len).astype(str)

    # Change blanks to asterisk
    df.loc[df['SUBJECTS'].str.len() == 0, 'SUBJECTS'] = '*'

    # Get just the folder
    df['DATA'] = df['OUTPUT'].str.rsplit('/', n=1).str[0]

    #if r['PDF']:
    #            _link = r['PDF']
    #            r['PDF'] = f'[📊]({_link})'
    df['PDF'] = '📊'
    df['LOG'] = '📄'
    #        if r['LOG']:
    #            _link = r['LOG']
    #            r['LOG'] = f'[📄]({_link})'

    # Get options
    proj_options = data.load_options()
    lead_options = sorted(df['INVESTIGATOR'].unique())
    status_options = sorted(df['STATUS'].unique())
    logger.debug(f'loaded options:{proj_options}:{lead_options}')

    proj = utils.make_options(proj_options)
    lead = utils.make_options(lead_options)
    status = utils.make_options(status_options)

    # Filter data based on dropdown values
    df = data.filter_data(df)

    if selected_lead:
        df = df[df['INVESTIGATOR'].isin(selected_lead)]

    if selected_status:
        df = df[df['STATUS'].isin(selected_status)]

    #df['COMPLETE'] = df['COMPLETE'].map(COMPLETE2EMO).fillna('?')

    # Get the table data as one row per assessor
    records = df.reset_index().to_dict('records')

    # Format records
    for r in records:
        # Make edit a link
        _link = r['EDIT']
        _text = 'edit'
        r['EDIT'] = f'[{_text}]({_link})'

        # Make a link
        if not r['DATA']:
            pass
        elif '/' in r['DATA']:
            _link = r['DATA']
            _text = r['DATA'].rsplit('/', 2)[1]
            r['DATA'] = f'[{_text}]({_link})'
        else:
            _link = r['DATA']
            _text = r['DATA']
            r['DATA'] = f'[{_text}]({_link})'

        # Make a link
        if not r['PROCESSOR']:
            pass
        elif '/' in r['PROCESSOR']:
            _u, _r, _v = r['PROCESSOR'].replace(':', '/').split('/')
            _link = f'https://github.com/{_u}/{_r}/tree/{_v}'
            _text = r['PROCESSOR']
            r['PROCESSOR'] = f'[{_text}]({_link})'

    # Count how many rows are in the table
    rowcount = '{} rows'.format(len(records))

    return [proj, lead, status, records, rowcount, rowcount]

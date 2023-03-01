"""Creates report PDF with zip."""
import logging
import io
import re
import os
import shutil
import itertools
from datetime import datetime, date, timedelta
import tempfile

import pandas as pd
import plotly
import plotly.graph_objs as go
import plotly.subplots
import plotly.express as px
from fpdf import FPDF
from PIL import Image

# These are used to set colors of graphs
RGB_DKBLUE = 'rgb(59,89,152)'
RGB_BLUE = 'rgb(66,133,244)'
RGB_GREEN = 'rgb(15,157,88)'
RGB_YELLOW = 'rgb(244,160,0)'
RGB_RED = 'rgb(219,68,55)'
RGB_PURPLE = 'rgb(160,106,255)'
RGB_GREY = 'rgb(200,200,200)'
RGB_PINK = 'rgb(255,182,193)'
RGB_LIME = 'rgb(17, 180, 101)'

# Give each status a color to display
QASTATUS2COLOR = {
    'PASS': RGB_GREEN,
    'NQA': RGB_LIME,
    'NPUT': RGB_YELLOW,
    'FAIL': RGB_RED,
    'NONE': RGB_GREY,
    'JOBF': RGB_PINK,
    'JOBR': RGB_BLUE}

STATUS2RGB = dict(zip(
    ['WAITING', 'PENDING', 'RUNNING', 'COMPLETE', 'FAILED', 'UNKNOWN', 'JOBF'],
    [RGB_GREY, RGB_YELLOW, RGB_GREEN, RGB_BLUE, RGB_RED, RGB_PURPLE, RGB_PINK]))

# These are used to make progress reports
ASTATUS2COLOR = {
    'PASS': RGB_GREEN,
    'NPUT': RGB_YELLOW,
    'FAIL': RGB_RED,
    'NQA': RGB_LIME,
    'NONE': RGB_GREY,
    'COMPLETE': RGB_BLUE,
    'UNKNOWN': RGB_PURPLE}

SESSCOLS = ['SESSION', 'PROJECT', 'DATE', 'SESSTYPE', 'SITE', 'MODALITY']

HIDECOLS = [
    'assessor_label',
    'PROJECT',
    'SESSION',
    'SUBJECT',
    'AGE',
    'SEX',
    'DEPRESS',
    'TYPE',
    'SITE',
    'SESSTYPE',
    'DATE',
    'ASSR',
    'PROCSTATUS',
    'QCSTATUS',
    'INPUTS',
    'MODALITY',
    'XSITYPE',
    'PROCTYPE',
    'full_path',
    'case',
]

ACOLS = [
    'ASSR',
    'PROJECT',
    'SUBJECT',
    'SESSION',
    'SESSTYPE',
    'SITE',
    'DATE',
    'PROCTYPE',
]


class MYPDF(FPDF):
    """Custom PDF."""

    def set_filename(self, filename):
        """Set the filename."""
        self.filename = filename

    def set_project(self, project):
        """Set the project name."""
        self.project = project
        today = datetime.now().strftime("%Y-%m-%d")
        self.date = today
        self.title = '{} Monthly Report'.format(project)
        self.subtitle = '{}'.format(datetime.now().strftime("%B %Y"))

    def footer(self):
        """Return the custom footer."""
        self.set_y(-0.35)
        self.set_x(0.5)

        # Write date, title, page number
        self.set_font('helvetica', size=10)
        self.set_text_color(100, 100, 100)
        self.set_draw_color(100, 100, 100)
        self.line(x1=0.2, y1=10.55, x2=8.3, y2=10.55)
        self.cell(w=1, txt=self.date)
        self.cell(w=5, align='C', txt=self.title)
        self.cell(w=2.5, align='C', txt=str(self.page_no()))


def blank_letter():
    """Blank letter sized PDF."""
    p = MYPDF(orientation="P", unit='in', format='letter')
    p.set_top_margin(0.5)
    p.set_left_margin(0.5)
    p.set_right_margin(0.5)
    p.set_auto_page_break(auto=False, margin=0.5)

    return p


def _draw_counts(pdf, sessions, rangetype=None):
    # Counts of each session type with sums
    # sessions column names are: SESSION, PROJECT, DATE, SESSTYPE, SITE
    type_list = sessions.SESSTYPE.unique()
    site_list = sessions.SITE.unique()

    # Get the data
    df = sessions.copy()

    if rangetype == 'lastmonth':
        pdf.set_fill_color(114, 172, 77)

        # Get the dates of lst month
        _end = date.today().replace(day=1) - timedelta(days=1)
        _start = date.today().replace(day=1) - timedelta(days=_end.day)

        # Get the name of last month
        lastmonth = _start.strftime("%B")

        # Filter the data to last month
        df = df[df.DATE >= _start.strftime('%Y-%m-%d')]
        df = df[df.DATE <= _end.strftime('%Y-%m-%d')]

        # Create the lastmonth header
        _txt = 'Session Counts ({})'.format(lastmonth)

    else:
        pdf.set_fill_color(94, 156, 211)
        _txt = 'Session Counts (all)'

    # Draw heading
    pdf.set_font('helvetica', size=18)
    pdf.cell(w=7.5, h=0.5, txt=_txt, align='C', border=0, ln=1)

    # Header Formatting
    pdf.cell(w=1.0)
    pdf.set_text_color(245, 245, 245)
    pdf.set_line_width(0.01)
    _kwargs = {'w': 1.2, 'h': 0.7, 'border': 1, 'align': 'C', 'fill': True}
    pdf.cell(w=0.7, border=0, fill=False)

    # Column header for each session type
    for cur_type in type_list:
        pdf.cell(**_kwargs, txt=cur_type)

    # Got to next line
    pdf.ln()

    # Row formatting
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(0, 0, 0)
    _kwargs = {'w': 1.2, 'h': 0.5, 'border': 1, 'align': 'C', 'fill': False}
    _kwargs_site = {'w': 1.7, 'h': 0.5, 'border': 1, 'align': 'C', 'fill': False}

    # Row for each site
    for cur_site in site_list:
        dfs = df[df.SITE == cur_site]
        _txt = cur_site

        pdf.cell(**_kwargs_site, txt=_txt)

        # Count each type for this site
        for cur_type in type_list:
            cur_count = str(len(dfs[dfs.SESSTYPE == cur_type]))
            pdf.cell(**_kwargs, txt=cur_count)

        # Total for site
        cur_count = str(len(dfs))
        pdf.cell(**_kwargs, txt=cur_count)
        pdf.ln()

    # TOTALS row
    pdf.cell(w=1.0)
    pdf.cell(w=0.7, h=0.5)
    for cur_type in type_list:
        pdf.set_font('helvetica', size=18)
        cur_count = str(len(df[df.SESSTYPE == cur_type]))
        pdf.cell(**_kwargs, txt=cur_count)

    pdf.cell(**_kwargs, txt=str(len(df)))

    pdf.ln()

    return pdf


def plot_timeline(df, startdate=None, enddate=None):
    """Plot timeline of data."""
    palette = itertools.cycle(px.colors.qualitative.Plotly)
    type_list = df.SESSTYPE.unique()
    mod_list = df.MODALITY.unique()
    fig = plotly.subplots.make_subplots(rows=1, cols=1)
    fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))

    for mod, sesstype in itertools.product(mod_list, type_list):
        # Get subset for this session type
        dfs = df[(df.SESSTYPE == sesstype) & (df.MODALITY == mod)]
        if dfs.empty:
            continue

        # Advance color here, before filtering by time
        _color = next(palette)

        if startdate:
            dfs = dfs[dfs.DATE >= startdate.strftime('%Y-%m-%d')]

        if enddate:
            dfs = dfs[dfs.DATE <= enddate.strftime('%Y-%m-%d')]

        # Nothing to plot so go to next session type
        if dfs.empty:
            logging.debug('nothing to plot:{}:{}'.format(mod, sesstype))
            continue

        # markers symbols, see https://plotly.com/python/marker-style/
        if mod == 'MR':
            symb = 'circle-dot'
        elif mod == 'PET':
            symb = 'diamond-wide-dot'
        else:
            symb = 'diamond-tall-dot'

        # Convert hex to rgba with alpha of 0.5
        if _color.startswith('#'):
            _rgba = 'rgba({},{},{},{})'.format(
                int(_color[1:3], 16),
                int(_color[3:5], 16),
                int(_color[5:7], 16),
                0.7)
        else:
            _r, _g, _b = _color[4:-1].split(',')
            _a = 0.7
            _rgba = 'rgba({},{},{},{})'.format(_r, _g, _b, _a)

        # Plot this session type
        try:
            _row = 1
            _col = 1
            fig.append_trace(
                go.Box(
                    name='{} {} ({})'.format(sesstype, mod, len(dfs)),
                    x=dfs['DATE'],
                    y=dfs['SITE'],
                    boxpoints='all',
                    jitter=0.7,
                    text=dfs['SESSION'],
                    pointpos=0.5,
                    orientation='h',
                    marker={
                        'symbol': symb,
                        'color': _rgba,
                        'size': 12,
                        'line': dict(width=2, color=_color)
                    },
                    line={'color': 'rgba(0,0,0,0)'},
                    fillcolor='rgba(0,0,0,0)',
                    hoveron='points',
                ),
                _row,
                _col)
        except Exception as err:
            logging.error(err)
            return None

    # show lines so we can better distinguish categories
    fig.update_yaxes(showgrid=True)

    # Set the size
    fig.update_layout(width=900)

    # Export figure to image
    _png = fig.to_image(format="png")
    image = Image.open(io.BytesIO(_png))
    return image


def plot_activity(df, pivot_index):
    """Plot activity data."""
    status2rgb = ASTATUS2COLOR

    fig = plotly.subplots.make_subplots(rows=1, cols=1)
    fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))

    # Draw bar for each status, these will be displayed in order
    dfp = pd.pivot_table(
        df, index=pivot_index, values='ID', columns=['STATUS'],
        aggfunc='count', fill_value=0)

    for status, color in status2rgb.items():
        ydata = sorted(dfp.index)
        if status not in dfp:
            xdata = [0] * len(dfp.index)
        else:
            xdata = dfp[status]

        fig.append_trace(go.Bar(
            x=ydata,
            y=xdata,
            name='{} ({})'.format(status, sum(xdata)),
            marker=dict(color=color),
            opacity=0.9), 1, 1)

    # Customize figure
    fig['layout'].update(barmode='stack', showlegend=True, width=900)

    # Export figure to image
    _png = fig.to_image(format="png")
    image = Image.open(io.BytesIO(_png))
    return image


def _add_page1(pdf, sessions):
    mr_sessions = sessions[sessions.MODALITY == 'MR'].copy()

    # Start the page with titles
    pdf.add_page()
    pdf.set_font('helvetica', size=22)
    pdf.cell(w=7.5, h=0.4, align='C', txt=pdf.title, ln=1)
    pdf.cell(w=7.5, h=0.4, align='C', txt=pdf.subtitle, ln=1, border='B')
    pdf.ln(0.25)

    # Show all MRI session counts
    pdf.set_font('helvetica', size=18)
    pdf.cell(w=7.5, h=0.4, align='C', txt='MRI')
    pdf.ln(0.25)
    _draw_counts(pdf, mr_sessions)
    pdf.ln(1)

    if len(mr_sessions.SITE.unique()) > 3:
        # Start a new page so it fits
        pdf.add_page()

    # Show MRI session counts in date range
    pdf.cell(w=7.5, h=0.4, align='C', txt='MRI')
    pdf.ln(0.25)
    _draw_counts(pdf, mr_sessions, rangetype='lastmonth')
    pdf.ln(1)

    return pdf


def _add_other_page(pdf, sessions):
    # Get non-MRI sessions
    other_sessions = sessions[sessions.MODALITY != 'MR'].copy()

    if len(other_sessions) == 0:
        logging.debug('no other modalities sessions, skipping page')
        return

    # Start a new page
    pdf.add_page()

    # Show all session counts
    pdf.set_font('helvetica', size=18)
    pdf.cell(w=7.5, h=0.4, align='C', txt='Other Modalities')
    pdf.ln(0.25)
    _draw_counts(pdf, other_sessions)
    pdf.ln(1)

    # Show session counts in date range
    pdf.cell(w=7.5, h=0.4, align='C', txt='Other Modalities')
    pdf.ln(0.25)
    _draw_counts(pdf, other_sessions, rangetype='lastmonth')
    pdf.ln(1)

    return pdf


def _add_stats_page(pdf, stats, proctype, short_descrip=None, stats_descrip=None):
    # 4 across, 3 down

    pdf.add_page()
    pdf.set_font('helvetica', size=18)
    pdf.cell(txt=proctype)

    pdf.set_font('helvetica', size=9)
    if short_descrip:
        pdf.cell(txt=short_descrip)
    if stats_descrip:
        pdf.cell(txt=stats_descrip)
    # TODO: show pipeline name and description, look up with proctype

    # this returns a PIL Image object
    image = plot_stats(stats, proctype)

    # Split the image into chunks that fit on a letter page
    # crop((left, top, right, bottom))
    _img1 = image.crop((0, 0, 1000, 500))
    _img2 = image.crop((1000, 0, 2000, 500))
    _img3 = image.crop((2000, 0, 2500, 500))

    pdf.set_fill_color(114, 172, 77)

    # Draw the images on the pdf
    pdf.image(_img1, x=0.5, y=0.75, h=3.3)
    pdf.image(_img2, x=0.5, y=4, h=3.3)
    pdf.image(_img3, x=0.5, y=7.25, h=3.3)

    return pdf


def _add_qa_page(pdf, scandata, assrdata, sesstype):
    scan_image = plot_qa(scandata)
    assr_image = plot_qa(assrdata)

    if not scan_image and not assr_image:
        # skip this page b/c there's nothing to plot
        logging.debug('skipping page, nothing to plot:{}'.format(sesstype))
        return pdf

    pdf.add_page()
    pdf.set_font('helvetica', size=18)
    pdf.ln(0.5)
    pdf.cell(w=5, align='C', txt='Scans by Type ({} Only)'.format(sesstype))

    if scan_image:
        pdf.image(scan_image, x=0.5, y=1.3, w=7.5)
        pdf.ln(4.7)

    if assr_image:
        pdf.cell(w=5, align='C', txt='Assessors by Type ({} Only)'.format(sesstype))
        pdf.image(assr_image, x=0.5, y=6, w=7.5)

    return pdf


def _add_timeline_page(pdf, info):
    # Get the data for all
    df = info['sessions'].copy()

    pdf.add_page()
    pdf.set_font('helvetica', size=18)

    # Draw all timeline
    _txt = 'Sessions Timeline (all)'
    pdf.cell(w=7.5, align='C', txt=_txt)
    image = plot_timeline(df)
    pdf.image(image, x=0.5, y=0.75, w=7.5)
    pdf.ln(5)

    # Get the dates of last month
    enddate = date.today().replace(day=1) - timedelta(days=1)
    startdate = date.today().replace(day=1) - timedelta(days=enddate.day)

    # Get the name of last month
    lastmonth = startdate.strftime("%B")

    _txt = 'Sessions Timeline ({})'.format(lastmonth)
    image = plot_timeline(df, startdate=startdate, enddate=enddate)
    pdf.cell(w=7.5, align='C', txt=_txt)
    pdf.image(image, x=0.5, y=5.75, w=7.5)
    pdf.ln()

    return pdf


def _add_phantom_page(pdf, info):
    # Get the data for all
    df = info['phantoms'].copy()

    pdf.add_page()
    pdf.set_font('helvetica', size=18)

    # Draw all timeline
    _txt = 'Phantoms (all)'
    pdf.cell(w=7.5, align='C', txt=_txt)
    image = plot_timeline(df)
    pdf.image(image, x=0.5, y=0.75, w=7.5)
    pdf.ln(5)

    # Get the dates of last month
    enddate = date.today().replace(day=1) - timedelta(days=1)
    startdate = date.today().replace(day=1) - timedelta(days=enddate.day)

    # Get the name of last month
    lastmonth = startdate.strftime("%B")

    _txt = 'Phantoms ({})'.format(lastmonth)
    image = plot_timeline(df, startdate=startdate, enddate=enddate)
    pdf.cell(w=7.5, align='C', txt=_txt)
    pdf.image(image, x=0.5, y=5.75, w=7.5)
    pdf.ln()

    return pdf


def _add_activity_page(pdf, info):
    # 'index', 'SESSION', 'SUBJECT', 'ASSR', 'JOBDATE', 'QCSTATUS',
    #   'session_ID', 'PROJECT', 'PROCSTATUS', 'xsiType', 'PROCTYPE',
    #   'QCDATE', 'DATE', 'QCBY', 'LABEL', 'CATEGORY', 'STATUS',
    #   'DESCRIPTION', 'DATETIME', 'ID'],
    pdf.add_page()
    pdf.set_font('helvetica', size=16)

    # Top third is QA activity
    #df = info['recentqa'].copy()
    #image = plot_activity(df, 'CATEGORY')
    #pdf.image(image, x=1.6, y=0.2, h=3.3)
    #pdf.ln(0.5)
    #pdf.multi_cell(1.5, 0.3, txt='QA\n')

    # jobs
    df = info['recentjobs'].copy()
    image = plot_activity(df, 'CATEGORY')
    pdf.image(image, x=1.6, y=0.2, h=3.3)
    pdf.ln(0.5)
    pdf.multi_cell(1.5, 0.3, txt='Jobs\n')

    # others
    df = info['activity'].copy()
    image = plot_activity(df, 'CATEGORY')
    pdf.image(image, x=1.6, y=3.5, h=3.3)
    pdf.ln(3)
    pdf.multi_cell(1.5, 0.3, txt='Automations')

    # issues
    df = info['issues'].copy()
    image = plot_activity(df, 'CATEGORY')
    pdf.image(image, x=1.6, y=7.0, h=3.3)
    pdf.ln(3)
    pdf.multi_cell(1.5, 0.3, txt='Issues\n')

    return pdf


def plot_qa(dfp):
    """Plot QA bars."""
    # TODO: fix the code in this function b/c it's weird with the pivots/melts
    for col in dfp.columns:
        if col in ('SESSION', 'PROJECT', 'DATE', 'MODALITY'):
            # don't mess with these columns
            continue

        # Change each value from the multiple values in concatenated
        # characters to a single overall status
        dfp[col] = dfp[col].apply(get_metastatus)

    # Initialize a figure
    fig = plotly.subplots.make_subplots(rows=1, cols=1)
    fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))

    # Check for empty data
    if len(dfp) == 0:
        logging.debug('dfp empty data')
        return None

    # use pandas melt function to unpivot our pivot table
    df = pd.melt(
        dfp,
        id_vars=(
            'SESSION',
            'PROJECT',
            'DATE',
            'SITE',
            'SESSTYPE',
            'MODALITY'),
        value_name='STATUS')

    # Check for empty data
    if len(df) == 0:
        logging.debug('df empty data')
        return None

    # We use fill_value to replace nan with 0
    dfpp = df.pivot_table(
        index='TYPE',
        columns='STATUS',
        values='SESSION',
        aggfunc='count',
        fill_value=0)

    scan_type = []
    assr_type = []
    for cur_type in dfpp.index:
        # Use a regex to test if name ends with _v and a number, then assr
        if re.search('_v\d+$', cur_type):
            assr_type.append(cur_type)
        else:
            scan_type.append(cur_type)

    newindex = scan_type + assr_type
    dfpp = dfpp.reindex(index=newindex)

    # Draw bar for each status, these will be displayed in order
    # ydata should be the types, xdata should be count of status
    # for each type
    for cur_status, cur_color in QASTATUS2COLOR.items():
        ydata = dfpp.index
        if cur_status not in dfpp:
            xdata = [0] * len(dfpp.index)
        else:
            xdata = dfpp[cur_status]

        cur_name = '{} ({})'.format(cur_status, sum(xdata))

        _width = (len(xdata) * 0.1) + 0.1
        _width = min(_width, 0.8)
        fig.append_trace(
            go.Bar(
                x=ydata,
                y=xdata,
                name=cur_name,
                marker=dict(color=cur_color),
                opacity=0.9,
                width=_width,
            ),
            1, 1)

    # Customize figure
    fig['layout'].update(barmode='stack', showlegend=True, width=900)

    # Export figure to image
    _png = fig.to_image(format="png")
    image = Image.open(io.BytesIO(_png))

    return image


def _plottable(var):
    try:
        _ = var.str.strip('%').astype(float)
        return True
    except:
        return False


def plot_stats(df, proctype):
    """Plot stats, one boxlplot per var."""
    box_width = 250
    min_box_count = 4

    logging.debug('plot_stats:{}'.format(proctype))

    # Check for empty data
    if len(df) == 0:
        logging.debug('empty data, using empty figure')
        fig = go.Figure()
        _png = fig.to_image(format="png")
        image = Image.open(io.BytesIO(_png))
        return image

    # Filter var list to only include those that have data
    var_list = [x for x in df.columns if not pd.isnull(df[x]).all()]

    # Filter var list to only stats variables
    var_list = [x for x in var_list if x not in HIDECOLS]

    # Filter var list to only stats can be plotted as float
    var_list = [x for x in var_list if _plottable(df[x])]

    # Determine how many boxplots we're making, depends on how many vars, use
    # minimum so graph doesn't get too small
    box_count = len(var_list)

    if box_count < 3:
        box_width = 500
        min_box_count = 2
    elif box_count < 6:
        box_width = 333
        min_box_count = 3

    if box_count < min_box_count:
        box_count = min_box_count

    graph_width = box_width * box_count

    # Horizontal spacing cannot be greater than (1 / (cols - 1))
    hspacing = 1 / (box_count * 4)

    logging.debug(f'{box_count}, {min_box_count}, {graph_width}, {hspacing}')

    # Make the figure with 1 row and a column for each var we are plotting
    fig = plotly.subplots.make_subplots(
        rows=1,
        cols=box_count,
        horizontal_spacing=hspacing,
        subplot_titles=var_list)

    # Add box plot for each variable
    for i, var in enumerate(var_list):

        # Create boxplot for this var and add to figure
        logging.debug('plotting var:{}'.format(var))

        _row = 1
        _col = i + 1

        fig.append_trace(
            go.Box(
                y=df[var].str.strip('%').astype(float),
                x=df['SITE'],
                boxpoints='all',
                text=df['ASSR'],
            ),
            _row,
            _col)

        # fig.update_layout(yaxis=dict(tickmode='linear', tick0=0.5, dtick=0.75))
        # fig.update_layout(yaxis=dict(showexponent='all', exponentformat='e'))
        fig.update_yaxes(autorange=True)

        # ax1.set_xticks(range(0,len(x), 100))    #set interval here

        if var.startswith('con_') or var.startswith('inc_'):
            logging.debug('setting beta range:{}'.format(var))
            _yaxis = 'yaxis{}'.format(i + 1)
            fig['layout'][_yaxis].update(range=[-1, 1], autorange=False)
        else:
            # logging.debug('setting autorange')
            pass

    # Move the subtitles to bottom instead of top of each subplot
    if len(df['SITE'].unique()) < 4:
        for i in range(len(fig.layout.annotations)):
            fig.layout.annotations[i].update(y=-.15)

    # Customize figure to hide legend and fit the graph
    fig.update_layout(
        showlegend=False,
        autosize=False,
        width=graph_width,
        margin=dict(l=20, r=40, t=40, b=80, pad=0))

    _png = fig.to_image(format="png")
    image = Image.open(io.BytesIO(_png))
    return image


def make_pdf(info, filename):
    """Make PDF from info, save to filename."""
    logging.debug('making PDF')

    # Initialize a new PDF letter size and shaped
    pdf = blank_letter()
    pdf.set_filename(filename)
    pdf.set_project(info['project'])


    # Add first page showing MRIs
    logging.debug('adding first page')
    _add_page1(pdf, info['sessions'])

    # Add other Modalities, counts for each session type
    logging.debug('adding other page')
    _add_other_page(pdf, info['sessions'])

    # Timeline
    logging.debug('adding timeline page')
    _add_timeline_page(pdf, info)

    # Session type pages - counts per scans, counts per assessor
    logging.debug('adding qa pages')
    for curtype in info['sessions'].SESSTYPE.unique():
        logging.debug('add_qa_page:{}'.format(curtype))

        # Get the scan and assr data
        scandf = info['scanqa'].copy()
        assrdf = info['assrqa'].copy()

        # Limit to the current session type
        scandf = scandf[scandf.SESSTYPE == curtype]
        assrdf = assrdf[assrdf.SESSTYPE == curtype]

        # Drop columns that are all empty
        scandf = scandf.dropna(axis=1, how='all')
        assrdf = assrdf.dropna(axis=1, how='all')

        # Add the page for this session type
        _add_qa_page(pdf, scandf, assrdf, curtype)

    # Add stats pages
    if info['stats'].empty:
        logging.debug('no stats')
    else:
        stats = info['stats']
        for s in info['stattypes']:
            # Limit the data to this proctype
            stat_data = stats[stats.PROCTYPE == s]
            if stat_data.empty:
                logging.debug(f'no stats for proctype:{s}')
            else:
                logging.debug(f'add stats page:{s}')
                short_descrip = info['proclib'].get(s, {}).get('short_descrip', None)
                stats_descrip = info['proclib'].get(s, {}).get('stats_descrip', None)
                _add_stats_page(pdf, stat_data, s, short_descrip, stats_descrip)

    # Phantom pages
    if 'phantoms' in info:
        logging.debug('adding phantom page')
        _add_phantom_page(pdf, info)

    # QA/Jobs/Issues counts
    _add_activity_page(pdf, info)

    # Save to file
    logging.debug('saving PDF to file:{}'.format(pdf.filename))
    try:
        pdf.output(pdf.filename)
    except Exception as err:
        logging.error('error while saving PDF:{}:{}'.format(pdf.filename, err))

    return True


def make_main_report():
    """Make main report."""
    # last week
    # show counts from last week

    # show issue counts

    # previous week

    # previous month

    # previous year

    # Note that all of these can be opened interactively in dashboard

    return


def _scanqa(scans, scantypes=None):
    dfp = _scan_pivot(scans).reset_index()

    # Filter columns to include
    include_list = SESSCOLS + scantypes
    include_list = [x for x in include_list if x in dfp.columns]
    include_list = list(set(include_list))
    dfp = dfp[include_list]

    # Drop columns that are all empty
    dfp = dfp.dropna(axis=1, how='all')

    return dfp


def _assrqa(assessors, proctypes=None):
    # Load that data
    dfp = _assr_pivot(assessors).reset_index()

    # Filter columns to include
    include_list = SESSCOLS + proctypes
    include_list = [x for x in include_list if x in dfp.columns]
    include_list = list(set(include_list))
    dfp = dfp[include_list]

    return dfp


def _scan_pivot(df):
    _index = ('SESSION', 'SUBJECT', 'PROJECT', 'DATE', 'SESSTYPE', 'SITE', 'MODALITY')
    df['TYPE'] = df['SCANTYPE']
    df['STATUS'] = df['QUALITY']
    dfp = df.pivot_table(
        index=_index,
        columns='TYPE',
        values='STATUS',
        aggfunc=lambda x: ''.join(x))

    return dfp


def _assr_pivot(df):
    _index = ('SESSION', 'SUBJECT', 'PROJECT', 'DATE', 'SESSTYPE', 'SITE', 'MODALITY')
    df['TYPE'] = df['PROCTYPE']
    df['STATUS'] = df['PROCSTATUS']
    dfp = df.pivot_table(
        index=_index,
        columns='TYPE',
        values='STATUS',
        aggfunc=lambda x: ''.join(x))

    return dfp


def get_metastatus(status):
    if not status or pd.isnull(status):  # np.isnan(status):
        # empty so it's none
        metastatus = 'NONE'
    elif 'P' in status:
        # at least one passed, so PASSED
        metastatus = 'PASS'
    elif 'Q' in status:
        # any are still needs qa, then 'NEEDS_QA'
        metastatus = 'NQA'
    elif 'N' in status:
        # if any jobs are still running, then NEEDS INPUTS?
        metastatus = 'NPUT'
    elif 'F' in status:
        # at this point if one failed, then they all failed, so 'FAILED'
        metastatus = 'FAIL'
    elif 'X' in status:
        metastatus = 'JOBF'
    elif 'R' in status:
        metastatus = 'JOBR'
    elif 'usable' in status:
        metastatus = 'PASS'
    elif 'questionable' in status:
        metastatus = 'NQA'
    elif 'unusable' in status:
        metastatus = 'FAIL'
    else:
        # whatever else is UNKNOWN, grey
        metastatus = 'NONE'

    return metastatus


def make_project_report(
    garjus,
    project,
    pdfname,
    zipname
):
    """"Make the project report PDF and zip files"""
    # TODO: garjus.proctypes_info()
    proclib = garjus.processing_library(project)
    activity = garjus.activity(project)
    issues = garjus.issues(project)

    # Load types for this project
    proctypes = garjus.proctypes(project)
    scantypes = garjus.scantypes(project)
    stattypes = garjus.stattypes(project)

    # Loads scans/assessors with type filters applied
    scans = garjus.scans(projects=[project], scantypes=scantypes)
    assessors = garjus.assessors(projects=[project], proctypes=proctypes)

    # Extract sessions from scans/assessors
    sessions = pd.concat([scans[SESSCOLS], assessors[SESSCOLS]])
    sessions = sessions.drop_duplicates().sort_values('SESSION')

    # Load stats with extra assessor columns
    stats = garjus.stats(project)
    stats = pd.merge(assessors[ACOLS], stats, left_on='ASSR', right_on='stats_assr')
    stats = stats.drop(columns=['stats_assr'])

    # Make the info dictionary for PDF
    info = {}
    info['proclib'] = proclib
    info['project'] = project
    info['stattypes'] = stattypes
    info['scantypes'] = scantypes
    info['proctypes'] = proctypes
    info['sessions'] = sessions
    info['activity'] = activity
    info['issues'] = issues
    info['recentjobs'] = _recent_jobs(assessors)
    info['recentqa'] = _recent_qa(assessors)
    info['stats'] = stats
    info['scanqa'] = _scanqa(scans, scantypes)
    info['assrqa'] = _assrqa(assessors, proctypes)
    # if phantom_project:
    #    info['phantoms'] = data.load_phantom_info(phantom_project)

    # Save the PDF report to file
    make_pdf(info, pdfname)

    # Save the stats to zip file
    stats2zip(stats, zipname)


def stats2zip(stats, filename):
    """Convert stats dict to zip of csv files, one csv per proctype."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Prep output dir
        stats_dir = os.path.join(tmpdir, 'stats')
        zip_file = os.path.join(tmpdir, 'stats.zip')
        os.mkdir(stats_dir)

        # Save a csv for each proc type
        for proctype in stats.PROCTYPE.unique():
            # Get the data for this processing type
            dft = stats[stats.PROCTYPE == proctype]
            dft = dft.dropna(axis=1, how='all')
            dft = dft.sort_values('ASSR')

            # Save file for this type
            csv_file = os.path.join(stats_dir, f'{proctype}.csv')
            logging.info(f'saving csv:{proctype}:{csv_file}')
            dft.to_csv(csv_file, index=False)

        # Create zip file of dir of csv files
        shutil.make_archive(stats_dir, 'zip', stats_dir)

        # Save it outside of temp dir
        logging.info(f'saving zip:{filename}')
        shutil.copy(zip_file, filename)


def _last_month():
    from dateutil.relativedelta import relativedelta
    return (datetime.today() - relativedelta(months=1)).strftime('%Y-%m-%d')


def _recent_jobs(assessors, startdate=None):
    """Get recent jobs, assessors on XNAT with job date since startdate."""
    if startdate is None:
        startdate = _last_month()

    df = assessors.copy()

    # Filter by jobstartdate date, include anything with job running
    df = df[(df['JOBDATE'] >= startdate) | (df['PROCSTATUS'] == 'JOB_RUNNING')]

    # Relabel as jobs
    df['LABEL'] = df['ASSR']
    df['CATEGORY'] = df['PROCTYPE']
    df['STATUS'] = df['PROCSTATUS'].map({
        'COMPLETE': 'COMPLETE',
        'JOB_FAILED': 'FAIL',
        'JOB_RUNNING': 'NPUT'}).fillna('UNKNOWN')
    df['CATEGORY'] = df['PROCTYPE']
    df['DESCRIPTION'] = 'JOB' + ':' + df['LABEL']
    df['DATETIME'] = df['JOBDATE']
    df['ID'] = df.index

    return df


def _recent_qa(assessors, startdate=None):
    if startdate is None:
        startdate = _last_month()

    df = assessors.copy()

    # Filter by qc date
    df = df[df['QCDATE'] >= startdate]

    # Relabel as qa
    df['LABEL'] = df['ASSR']
    df['CATEGORY'] = df['PROCTYPE']
    df['STATUS'] = df['QCSTATUS'].map({
        'Failed': 'FAIL',
        'Passed': 'PASS'}).fillna('UNKNOWN')
    df['CATEGORY'] = df['PROCTYPE']
    df['DESCRIPTION'] = 'QA' + ':' + df['LABEL']
    df['DATETIME'] = df['QCDATE']
    df['ID'] = df.index

    return df

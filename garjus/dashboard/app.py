import datetime
import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

hour = datetime.datetime.now().hour
if hour < 9 or hour > 17:
    stylesheets = [dbc.themes.DARKLY, dbc_css]
    load_figure_template("darkly")
else:
    stylesheets = [dbc.themes.FLATLY, dbc_css]
    load_figure_template("flatly")

app = dash.Dash(__name__, external_stylesheets=stylesheets)

server = app.server

app.config.suppress_callback_exceptions = True

# more here:
# https://hellodash.pythonanywhere.com
# https://codepen.io/chriddyp/pen/bWLwgP.css
# dbc.themes.DARKLY flat dark
# dbc.themes.FLATLY flat light
# dbc.themes.LUMEN bright
# dbc.themes.SLATE dark
# dbc.themes.SPACELAB buttony
# dbc.themes.YETI nice

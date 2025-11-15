import pandas as pd
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
from dash import html

'''
vendor_df = pd.read_csv("data/CAD_Parts_Vendor_Database.csv")
po_df = pd.read_csv("data/CAD_Parts_Purchase_Orders.csv")
bom_df = pd.read_csv("data/CAD_Parts_BOM_Complete.csv")
'''
vendor_df = pd.read_csv("uploads/CAD_Parts_Vendor_Database.csv")
po_df = pd.read_csv("uploads/CAD_Parts_Purchase_Orders.csv")
bom_df = pd.read_csv("uploads/CAD_Parts_BOM_Complete.csv")

po_df['State'] = po_df['Location'].str.split(',').str[1].str.strip()
po_df['Date'] = pd.to_datetime(po_df['Date'])

app_d = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                requests_pathname_prefix="/xforia-coast/dashboard/"
                )
app_d.layout=html.Div("Dash inside FastAPI!")

app_d.layout = dbc.Container([
      
    dbc.Row([
        dbc.Col(
            html.Div(
                [
                    html.A(
                        html.Img(
                            src=dash.get_asset_url("images/logo.png"),
                            style={
                                "width": "200px",
                                "height": "auto",
                                "marginTop": "0px"
                            }
                        ),
                        href="https://www.xforiacoast.com/"
                    ),
                    html.Span(
                        [
                            "Ride the", html.Br(),
                            "wave of", html.Br(),
                            "efficiency."
                        ],
                        style={
                            "marginLeft": "3px",  
                            "fontSize": "0.8rem",
                            "color": "#14967c",
                            "lineHeight": "1.2"  ,
                            'font-weight':'bold'   
                        }
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginLeft": "60px"    }   
            ),
            width="auto"
        ),

    

        dbc.Col(
            html.H1(
                "Supply Chain Hub",
                style={
                    "margin": "0",
                    "fontWeight": "bold",
                    "color": "#0e563b"
                }
            ),
            width=True,
            style={"textAlign": "center", "display": "flex", "alignItems": "center", "justifyContent": "center"}
        )


    ], align="center", className="mb-2",
    style={
        "display": "flex",             
        "alignItems": "center",        
        "justifyContent": "center",
    "position": "fixed",
    "top": "0",
    "left": "0",
    "width": "100%",
    "zIndex": "1000",
    "backgroundColor": "white",
    "padding": "10px 0",
    "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"

        }),

    

        

    dbc.Row([
    dbc.Col(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(html.H6("Total Vendors", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto"),
                    dbc.Col(html.H4(id="kpi-vendors", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto")
                ], justify="between", align="center")
            ),
            color="primary",
            inverse=True,
            style={"height": "50px", "padding": "5px"}  
        ), width=3
    ),
    dbc.Col(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(html.H6("Total Parts", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto"),
                    dbc.Col(html.H4(id="kpi-parts", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto")
                ], justify="between", align="center")
            ),
            color="info",
            inverse=True,
            style={"height": "50px", "padding": "5px"}
        ), width=3
    ),
    dbc.Col(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(html.H6("Total BOMs", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto"),
                    dbc.Col(html.H4(id="kpi-bom", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto")
                ], justify="between", align="center")
            ),
            color="warning",
            inverse=True,
            style={"height": "50px", "padding": "5px"}
        ), width=3
    ),
    dbc.Col(
        dbc.Card(
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(html.H6("Total Orders", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto"),
                    dbc.Col(html.H4(id="kpi-orders", style={"margin": 0, "font-size":"1.2rem","font-weight": "bold"}), width="auto")
                ], justify="between", align="center")
            ),
            color="success",
            inverse=True,
            style={"height": "50px", "padding": "5px"}
        ), width=3
    ),
], className="mb-2"),

    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="month-dropdown",
                options=[{"label": m, "value": m} for m in po_df['Date'].astype(str).str[:7].unique()],
                placeholder="Select Month",
                multi=True
            ), width=3
        ),
        dbc.Col(
            dcc.Dropdown(
                id="part-dropdown",
                options=[{"label": p, "value": p} for p in vendor_df['Part Name'].unique()],
                placeholder="Select Part",
                multi=True
            ), width=3
        ),
        dbc.Col(
            dcc.Dropdown(
                id="bom-dropdown",
                options=[{"label": b, "value": b} for b in bom_df['Part Name'].unique()],
                placeholder="Select BOM",
                multi=True
            ), width=3
        ),
        dbc.Col(
            dcc.Dropdown(
                id="vendor-dropdown",
                options=[{"label": v, "value": v} for v in vendor_df['Vendor Name'].unique()],
                placeholder="Select Vendor",
                multi=True
            ), width=3
        )
    ], className="mb-3"),

    html.Div([
        html.Button("Show/Hide Vendor Details", id="toggle-table-btn", n_clicks=0, className="btn btn-secondary mb-2"),
        html.Div(id="vendor-table-container", children=[
            dash_table.DataTable(
                id='vendor-details-table',
                columns=[
                    {"name": "Vendor Name", "id": "Vendor Name"},
                    {"name": "Part Name", "id": "Part Name"},
                    {"name": "Orders", "id": "Orders"},
                    {"name": "DPPM", "id": "DPPM"},
                    {"name": "Avg Days", "id": "Avg Days"},
                    {"name": "On-Time %", "id": "On-Time %"},
                    {"name": "Quality %", "id": "Quality %"},
                    {"name": "Rating", "id": "Rating"}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center'},
                style_header={
                    'fontWeight': 'bold',  
                    'backgroundColor': '#f9f9f9', 
                    'textAlign': 'center'
                },
                page_size=10
            )
        ],style={'display':'none'})
    ], className="mb-3"),

  
    dbc.Row([
        dbc.Col(dcc.Graph(id='scatter-graph', style={'height':'40vh'}), width=4),
        dbc.Col(dcc.Graph(id='heatmap-graph', style={'height':'40vh'}), width=4),
        dbc.Col(dcc.Graph(id='pairplot-graph', style={'height':'40vh'}), width=4)
    ], className="mb-3"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='map-graph', style={'height':'50vh'}), width=4),
        dbc.Col(dcc.Graph(id='timeline-graph', style={'height':'40vh'}), width=4),
        dbc.Col(dcc.Graph(id='treemap-graph', style={'height':'45vh'}), width=4)
    ]),

    dbc.Row([
        dbc.Col(
            dbc.Button(
                "⬅ Go Back",
                href="https://www.xforiacoast.com/pages/manufacturing/consolidate-files.html?company=Xforia&unified=true",
                color="secondary",
                style={"width": "150px"},
            ),
            width="auto",
        )
    ],justify="center",className="mb-3"),
    
    html.Footer(
        className='footer-content',
        children="© 2025 Xforia COAST - All Rights Reserved."
    )


],  fluid=True, style={"marginTop": "120px"}) 

# n
@app_d.callback(
        Output('bom-dropdown','options'),
        Input('part-dropdown','value')
)

def update_bom_options(selected_parts):
    if not selected_parts:
        return [{'label':b,'value':b} for b in bom_df['Part Name'].unique()]
    selected_pids=vendor_df[vendor_df["Part Name"].isin(selected_parts)]['PID'].unique()
    filtered_bom=bom_df[bom_df['Part ID (PID)'].isin(selected_pids)]
    return [{'label':b,'value':b} for b in filtered_bom['Part Name'].unique()]
#n


@app_d.callback(
    Output('scatter-graph', 'figure'),
    Output('heatmap-graph', 'figure'),
    Output('pairplot-graph', 'figure'),
    Output('map-graph', 'figure'),
    Output('timeline-graph', 'figure'),
    Output('treemap-graph', 'figure'),
    Output('kpi-vendors', 'children'),
    Output('kpi-parts', 'children'),
    Output('kpi-bom', 'children'),
    Output('kpi-orders', 'children'),
    Output('vendor-details-table', 'data'),
    Output('vendor-table-container', 'style'),
    Input('month-dropdown', 'value'),
    Input('part-dropdown', 'value'),
    Input('bom-dropdown', 'value'),
    Input('vendor-dropdown', 'value'),
    Input('toggle-table-btn', 'n_clicks')
)
def update_dashboard(selected_months, selected_parts, selected_boms, selected_vendors, n_clicks):
    #n
    if selected_boms:
        related_pids = bom_df[bom_df['Part Name'].isin(selected_boms)]['Part ID (PID)'].unique()
        related_parts = vendor_df[vendor_df['PID'].isin(related_pids)]['Part Name'].unique()
        selected_parts = related_parts
    #n
    filtered_po = po_df.copy()
    if selected_months:
        filtered_po = filtered_po[filtered_po['Date'].astype(str).str[:7].isin(selected_months)]

    filtered_vendor = vendor_df.copy()
    if selected_parts:
        filtered_vendor = filtered_vendor[filtered_vendor['Part Name'].isin(selected_parts)]
    if selected_vendors:
        filtered_vendor = filtered_vendor[filtered_vendor['Vendor Name'].isin(selected_vendors)]

    vendors_in_month = filtered_po['Vendor'].unique()
    filtered_vendor = filtered_vendor[filtered_vendor['Vendor Name'].isin(vendors_in_month)]

    scatter_fig = px.scatter(
        filtered_vendor,
        x="On-Time %",
        y="DPPM",
        size="Orders",
        color="Rating",
        hover_name="Part Name",
        title="<b>On-Time Delivery vs Defective Parts</b>"
    )

    heatmap_df = filtered_vendor.groupby('Part Name')[['Orders','Avg Days','DPPM']].mean()
    heatmap_fig = px.imshow(
        heatmap_df.T,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='Viridis',
        title="<b>Orders, Lead Time, and DPPM by Parts</b>"
    )
    # heatmap_fig.update_xaxes(tickangle=-45, showticklabels=False)
    heatmap_fig.update_xaxes(title_text="Parts", tickangle=-45, showticklabels=False)

    # Pair Plot
    # pairplot_fig = px.scatter_matrix(
    #     filtered_vendor,
    #     dimensions=['Orders','Avg Days','DPPM'],
    #     color='Rating',
    #     hover_name='Part Name',
    #     title="<b>Correlation of Orders, Average Lead Time, and DPPM by Rating</b>"
    # )

    
    vendor_grouped = filtered_vendor.groupby("Vendor Name").agg({
        "Orders": "sum",
        "DPPM": "mean",
        "Quality %": "mean",
        "Avg Days": "mean",
        "On-Time %": "mean"
    }).reset_index()

    if len(vendor_grouped) > 1:
        vendor_grouped = vendor_grouped.sort_values("Orders", ascending=False).head(10)
    
    blue_shades = [
    "#005ce6" ,
    "#3385ff", 
    "#66b2ff", 
    "#99ccff", 
    "#cce5ff", ]

    vendor_bar_fig = px.bar(
        vendor_grouped,
        x="Vendor Name",
        y=["Orders", "DPPM", "Quality %", "Avg Days", "On-Time %"],   
        title="<b>Top Vendors by Features </b>",
        barmode="stack",
        color_discrete_sequence=blue_shades
    )

    vendor_bar_fig.update_layout(
        updatemenus=[
            dict(
                buttons=list([
                    dict(
                        label="Sort by Orders",
                        method="relayout",
                        args=[{"xaxis.categoryorder": "array",
                            "xaxis.categoryarray": vendor_grouped.sort_values("Orders", ascending=False)["Vendor Name"]}]
                    ),
                    dict(
                        label="Sort by Quality %",
                        method="relayout",
                        args=[{"xaxis.categoryorder": "array",
                            "xaxis.categoryarray": vendor_grouped.sort_values("Quality %", ascending=False)["Vendor Name"]}]
                    ),
                    dict(
                        label="Sort by DPPM",
                        method="relayout",
                        args=[{"xaxis.categoryorder": "array",
                            "xaxis.categoryarray": vendor_grouped.sort_values("DPPM", ascending=True)["Vendor Name"]}]
                    ),
                    dict(
                        label="Sort by Avg Days",
                        method="relayout",
                        args=[{"xaxis.categoryorder": "array",
                            "xaxis.categoryarray": vendor_grouped.sort_values("Avg Days", ascending=True)["Vendor Name"]}]
                    ),
                    dict(
                        label="Sort by On-Time %",
                        method="relayout",
                        args=[{"xaxis.categoryorder": "array",
                            "xaxis.categoryarray": vendor_grouped.sort_values("On-Time %", ascending=False)["Vendor Name"]}]
                    )
                ]),
                direction="down",
                showactive=True,
                x=1.15,
                y=1.2
            )
        ]
    )

    vendor_bar_fig.update_layout(
        xaxis=dict(showticklabels=False),
        xaxis_title="Vendors",
        yaxis_title="Metrics",
        legend_title="Metrics"
    )

    po_df["Amount ($)"] = po_df["Amount ($)"].replace(r'[\$,]', '', regex=True).astype(float)

    po_df.columns = po_df.columns.str.strip()
    filtered_po = po_df.copy()
    if selected_months:
        filtered_po = filtered_po[filtered_po['Date'].astype(str).str[:7].isin(selected_months)]
    if selected_vendors:
        filtered_po = filtered_po[filtered_po['Vendor'].isin(selected_vendors)]
    if selected_parts:
        selected_pids = vendor_df[vendor_df['Part Name'].isin(selected_parts)]['PID'].unique()
        filtered_po = filtered_po[filtered_po['Part ID'].isin(selected_pids)]
    if selected_boms:
        selected_pids = bom_df[bom_df['Part Name'].isin(selected_boms)]['Part ID (PID)'].unique()
        filtered_po = filtered_po[filtered_po['Part ID'].isin(selected_pids)]



    map_fig = px.scatter_geo(
    filtered_po,
    locations="State",
    locationmode="USA-states",
    scope="usa",
    color="PO Status",
    size="Amount ($)",
    hover_name="Location",
    hover_data={
        "Qty Ordered": True,
        "Vendor": True,
        "Materials Supported": True,
        "Amount ($)": True,
        "PO Status": True
    },
    title="<b>Geographic Distribution of Purchase Orders</b>"
)

    timeline_fig = px.line(
        filtered_po.sort_values('Date'),
        x='Date',
        y='Amount ($)',
        color='PO Status',
        markers=True,
        title="<b>Purchase Order over Time by Status</b>",
        hover_data={
        "Vendor": True,        
        "Qty Ordered": True,
        "Materials Supported": True,
        "Amount ($)": True,
        "PO Status": True
    }
    )
     
    # filtered_bom = bom_df.copy()
    # if selected_boms:
    #     filtered_bom = filtered_bom[filtered_bom['Part Name'].isin(selected_boms)]
    # if selected_parts:
    #     filtered_bom = filtered_bom[filtered_bom['Part Name'].isin(selected_parts)]
    filtered_bom = bom_df.copy()
    if selected_parts:
        selected_pids=vendor_df[vendor_df['Part Name'].isin(selected_parts)]['PID'].unique()
        filtered_bom=filtered_bom[filtered_bom['Part ID (PID)'].isin(selected_pids)]

    if selected_boms:
        filtered_bom=filtered_bom[filtered_bom['Part Name'].isin(selected_boms)]

        related_pids=filtered_bom['Part ID (PID)'].unique()
        related_parts=vendor_df[vendor_df['PID'].isin(related_pids)]['Part Name'].unique()
        selected_parts=related_parts


    treemap_fig = px.treemap(
        filtered_bom,
        path=['Part Name', 'Description'],
        values='Quantity',
        color='Critical',
        title="<b>Bill of Materials Hierarchy </b>",
        custom_data=['Description', 'Quantity', 'Unit', 'Category', 'Specification', 'Lead Time', 'Material', 'Dimensions (mm)', 'Finish']
    )
    treemap_fig.update_traces(
        hovertemplate=
        "<b>%{label}</b><br>" +
        "Description: %{customdata[0]}<br>" +
        "Quantity: %{customdata[1]} %{customdata[2]}<br>" +
        "Category: %{customdata[3]}<br>" +
        "Specification: %{customdata[4]}<br>" +
        "Lead Time: %{customdata[5]}<br>" +
        "Material: %{customdata[6]}<br>" +
        "Dimensions: %{customdata[7]}<br>" +
        "Finish: %{customdata[8]}<extra></extra>",hoverlabel=dict(
        bgcolor="black",     
        font_size=12,         
        font_color="white"    
    )
    )

    # kpi_vendors = filtered_vendor['Vendor Name'].nunique()
    # kpi_parts = filtered_vendor['Part Name'].nunique()
    # kpi_bom = filtered_bom['Part Name'].nunique()
    # kpi_orders = filtered_vendor['Orders'].sum()


    #     # Determine parts related to selected BOMs
    # kpi_vendors = filtered_vendor['Vendor Name'].nunique()
    # kpi_orders = filtered_vendor['Orders'].sum()

    # # Show the number of selected parts or BOMs
    # kpi_parts = len(selected_parts) if selected_parts else filtered_vendor['Part Name'].nunique()
    # kpi_bom = len(selected_boms) if selected_boms else filtered_bom['Part Name'].nunique()

    # Number of vendors after filtering
    kpi_vendors = filtered_vendor['Vendor Name'].nunique()

    # Number of parts corresponding to selected BOMs or selected parts
    if selected_boms:
        # Parts that are in the selected BOMs
        bom_pids = bom_df[bom_df['Part Name'].isin(selected_boms)]['Part ID (PID)'].unique()
        parts_in_boms = vendor_df[vendor_df['PID'].isin(bom_pids)]['Part Name'].unique()
        kpi_parts = len(parts_in_boms)
        kpi_bom = len(selected_boms)
    elif selected_parts:
        kpi_parts = len(selected_parts)
        kpi_bom = bom_df[bom_df['Part ID (PID)'].isin(vendor_df[vendor_df['Part Name'].isin(selected_parts)]['PID'].unique())]['Part Name'].nunique()
    else:
        kpi_parts = filtered_vendor['Part Name'].nunique()
        kpi_bom = filtered_bom['Part Name'].nunique()

    # Total orders for filtered vendors
    kpi_orders = filtered_vendor['Orders'].sum()





    if selected_vendors:
        table_data = filtered_vendor.to_dict('records')
    else:
        table_data = []

    table_style = {"display": "block"} if n_clicks % 2 == 1 else {"display": "none"}

    return scatter_fig, heatmap_fig, vendor_bar_fig, map_fig, timeline_fig, treemap_fig, kpi_vendors, kpi_parts, kpi_bom, kpi_orders, table_data, table_style

def run_dash(debug=True, port=8000):
    app_d.run(debug=debug, port=port)
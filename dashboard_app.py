'''
Streamlit app to download recent job offers from linkedin based on keyword given by the user

Usage: 
streamlit run dashboard_app.py
'''

import os
import pandas as pd
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# configuration of the page
st.set_page_config(layout="wide")
SPACER = .2
ROW = 1


@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)


@st.cache_data
def get_occurrences(df_orders, df_products, df_aisles, df_departments):
    l = df_orders["product_id"].to_list()
    l = [int(item) for sublist in l for item in sublist[1:-1].replace(" ", "").split(",")]
    df_product_occurrence = pd.DataFrame(l, columns=["product_id"])
    df_product_occurrence = df_product_occurrence.value_counts().reset_index()
    df_product_occurrence = df_product_occurrence.rename(columns={0: "count"})
    df_product_occurrence = df_product_occurrence.merge(df_products, on=["product_id"])
    df_product_occurrence = df_product_occurrence.merge(df_aisles, on=["aisle_id"])
    df_product_occurrence = df_product_occurrence.merge(df_departments, on=["department_id"])
    return df_product_occurrence


def hide_streamlit_header_footer():
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    css = '''
        <style>
        section.main > div:has(~ footer ) {
            padding-bottom: 0px;
        }
        </style>
        '''
    st.markdown(css, unsafe_allow_html=True)


def plot_metric(number, delta_number, title):
    config = {'staticPlot': True, 'displayModeBar': False}

    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=number,
        title={"text": title, "font": {"size": 24}},
        delta={'reference': delta_number, 'relative': True},
        domain={'row': 0, 'column': 0}))

    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    fig.update_layout(
        # paper_bgcolor="lightgrey",
        margin=dict(t=30, b=0),
        showlegend=False,
        plot_bgcolor="white",
        height=100,
    )

    st.plotly_chart(fig, use_container_width=True, config=config)


def get_time_of_day(hour):
    if (hour <= 6):
        return "night"
    elif (hour <= 9):
        return "early morning"
    elif (hour <= 12):
        return "morning"
    elif (hour <= 15):
        return "early afternoon"
    elif (hour <= 18):
        return "afternoon"
    elif (hour > 18):
        return "evening"


def main():

    hide_streamlit_header_footer()

    # HEADER
    title, _, header_button = st.columns((ROW, .05, ROW*2))
    with title:
        st.title('Instacart sales dashboard')

    df_products = load_data(f"data/raw/products.csv")
    df_aisles = load_data(f"data/raw/aisles.csv")
    df_departments = load_data(f"data/raw/departments.csv")

    df_new_users = load_data("data/processed/new_users.zip")
    df_new_users["date"] = pd.to_datetime(df_new_users["date"])

    df_volumes = load_data("data/processed/volumes.zip")
    df_volumes["date"] = pd.to_datetime(df_volumes["date"])

    with header_button:
        button_1, button_2, button_3, button_4 = st.columns(4)
        with button_1:
            week_list = [file for file in os.listdir("data/processed") if file[0:6] == "orders"]
            week_list = [file[7:-4] for file in week_list]
            week_list.sort(reverse=True)
            week = st.selectbox('Week', week_list[1:-1])

            df_orders = load_data(f"data/processed/orders_{week}.zip")
            df_orders_prev = load_data(f"data/processed/orders_{week_list[week_list.index(week)+1]}.zip")

    st.write("")

    week_occurrences = get_occurrences(df_orders, df_products, df_aisles, df_departments)
    week_occurrences_prev = get_occurrences(df_orders_prev, df_products, df_aisles, df_departments)

    row_1_col_1, row_1_col_2, row_1_col_3, row_1_col_4, row_1_col_5 = st.columns(5)
    with row_1_col_1:
        plot_metric(len(df_orders["user_id"].unique()), len(df_orders_prev["user_id"].unique()), "Total users")

    with row_1_col_2:
        plot_metric(len(df_orders["order_id"].unique()), len(df_orders_prev["order_id"].unique()), "Total orders")

    with row_1_col_3:
        plot_metric(df_orders["basket_size"].mean(), df_orders_prev["basket_size"].mean(), "Average basket size")

    with row_1_col_4:
        plot_metric(df_orders["days_since_prior_order"].mean(),
                    df_orders_prev["days_since_prior_order"].mean(), "Days between orders")

    with row_1_col_5:
        week_end, week_start = pd.to_datetime(week.split("_")[0]), pd.to_datetime(week.split("_")[1])
        df_new_users_this_week = df_new_users[(df_new_users["date"] >= week_start) & (df_new_users["date"] <= week_end)]

        prev_week = week_list[week_list.index(week)+1]
        week_end, week_start = pd.to_datetime(prev_week.split("_")[0]), pd.to_datetime(prev_week.split("_")[1])
        df_new_users_last_week = df_new_users[(df_new_users["date"] >= week_start) & (df_new_users["date"] <= week_end)]
        plot_metric(len(df_new_users_this_week), len(df_new_users_last_week), "New users")

    # st.write()
    row_2_col_1, _, row_2_col_2, _, row_2_col_3 = st.columns((ROW*1.5, .05, ROW, .05, ROW))
    with row_2_col_1:
        df_volumes = df_volumes[df_volumes["date"] <= pd.to_datetime(week.split("_")[0])]
        df_wv = df_volumes.groupby(pd.Grouper(key='date', freq='W')).sum().reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_wv['date'], y=df_wv['order_number'], name="Orders"), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_wv['date'], y=df_wv['basket_size'], name="Sold items"), secondary_y=True)

        fig.update_layout(title_text="Weekly sales", height=300, margin=dict(l=0, r=0, b=0, t=50))
        fig.update_xaxes(title_text="week")
        fig.update_yaxes(title_text="Order volume", secondary_y=False)
        fig.update_yaxes(title_text="Items volume", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with row_2_col_2:
        df_ = df_orders.groupby("date").order_number.count().reset_index()
        df_["date"] = pd.to_datetime(df_["date"]).dt.day_name()

        df_prev_ = df_orders_prev.groupby("date").order_number.count().reset_index()
        df_prev_["date"] = pd.to_datetime(df_prev_["date"]).dt.day_name()

        data = [
            go.Bar(x=df_['date'], y=df_['order_number'], name="This week"),
            go.Scatter(x=df_prev_['date'], y=df_prev_['order_number'], name="Previous week")
        ]

        fig = go.Figure(data=data, layout=go.Layout(title='Average daily orders',
                        height=300, margin=dict(l=0, r=0, b=0, t=50)))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with row_2_col_3:
        df_ = df_orders.groupby("datetime").order_number.count().reset_index()
        df_["hour"] = pd.to_datetime(df_["datetime"]).dt.hour
        df_["time_of_day"] = df_["hour"].apply(lambda x: get_time_of_day(x))
        df_ = df_.groupby("time_of_day").agg({"order_number": "sum", "hour": "max"}).reset_index().sort_values("hour")

        df_prev_ = df_orders_prev.groupby("datetime").order_number.count().reset_index()
        df_prev_["hour"] = pd.to_datetime(df_prev_["datetime"]).dt.hour
        df_prev_["time_of_day"] = df_prev_["hour"].apply(lambda x: get_time_of_day(x))
        df_prev_ = df_prev_.groupby("time_of_day").agg(
            {"order_number": "sum", "hour": "max"}).reset_index().sort_values("hour")

        data = [
            go.Bar(x=df_['time_of_day'], y=df_['order_number'], name="This week"),
            go.Scatter(x=df_prev_['time_of_day'], y=df_prev_['order_number'], name="Previous week")
        ]

        fig = go.Figure(data=data, layout=go.Layout(title='Time of order',
                        height=300, margin=dict(l=0, r=0, b=0, t=50)))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    row_3_col_1, _, row_3_col_2, _, row_3_col_3 = st.columns((ROW, .05, ROW, .05, ROW))
    with row_3_col_1:
        df_top_departments = week_occurrences.groupby("department")["count"].sum().reset_index()
        df_top_departments = df_top_departments.sort_values("count", ascending=False)
        other_count = df_top_departments[6:]["count"].sum()
        df_top_departments = df_top_departments.append({"department": "other", "count": other_count}, ignore_index=True)
        df_top_departments = df_top_departments.sort_values("count", ascending=False)

        fig = px.pie(df_top_departments[0:7], values='count', names='department', title="Top departments")
        fig.update_layout(height=300, margin=dict(l=0, r=0, b=0, t=50))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with row_3_col_2:
        df_top_aisles = week_occurrences.groupby("aisle")["count"].sum().reset_index()
        df_top_aisles_prev = week_occurrences_prev.groupby("aisle")["count"].sum().reset_index()
        df_top_aisles = df_top_aisles.merge(df_top_aisles_prev, on="aisle", suffixes=["", "_prev"])
        df_top_aisles = df_top_aisles.sort_values("count", ascending=False)[0:5]

        data = [
            go.Bar(x=df_top_aisles['aisle'], y=df_top_aisles['count'], name="This week"),
            go.Scatter(x=df_top_aisles['aisle'], y=df_top_aisles['count_prev'], name="Previous week")
        ]

        fig = go.Figure(data=data, layout=go.Layout(title='Top aisles',
                        height=300, margin=dict(l=0, r=0, b=0, t=50)))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with row_3_col_3:
        active_users_this_week = list(df_orders["user_id"].unique())
        active_users_last_week = list(df_orders_prev["user_id"].unique())
        active_users_last_two_weeks = set(active_users_last_week + active_users_this_week)

        fig = go.Figure(
            go.Indicator(
                value=100*len(active_users_this_week)/len(active_users_last_two_weeks),
                mode="gauge+number",
                domain={"x": [0, 1], "y": [0, 1]},
                number={
                    "suffix": "%",
                    "font.size": 26,
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": "green"},
                },
                title={
                    "text": "Active users",
                    "font": {"size": 28},
                },
            )
        )
        fig.update_layout(
            # paper_bgcolor="lightgrey",
            height=200,
            margin=dict(l=10, r=10, t=50, b=10, pad=8),
        )
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()

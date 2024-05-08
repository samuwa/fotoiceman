import streamlit as st
import pandas as pd
from apify_client import ApifyClient
import plotly.express as px
from datetime import date

today = date.today()

@st.cache_data
def get_data():
    client = ApifyClient(st.secrets["KEY"])
    data = client.dataset(st.secrets["DATASET"]).list_items().items
    df = pd.DataFrame(data)
    df["scrapeDate"] = pd.to_datetime(df["scrapeDate"]).dt.date
    df['price'] = df['price'].str.replace('Ahora', '', regex=False)
    df['price'] = df['price'].str.replace('$', '', regex=False)
    df['price'] = df['price'].str.replace(',', '', regex=False)
    df['price'] = df['price'].astype(float)
    df = df[df['productName'].str.contains('bocina', case=False)]
    return df


st.set_page_config(layout="wide")

if "data" not in st.session_state:
    st.session_state["data"] = None

if "df" not in st.session_state:
    st.session_state.df = None

if "apify_client" not in st.session_state:
    st.session_state.apify_client = None



# Create Dataset
st.session_state.df = get_data()



st.title("Price Monitoring")

col1, col2 = st.columns(2)

min_price = col1.number_input("Min Price", value=1)
max_price = col2.number_input("Max Price", value=500)

st.session_state.df = st.session_state.df[(st.session_state.df['price'] >= min_price) & (st.session_state.df['price'] <= max_price)]



tab1, tab2, tab3 = st.tabs(["Product Tracker", "Added and Removed Products", "Change Tracker"])

with tab1:
    productos = st.multiselect("Select Products", st.session_state.df["productName"].unique())


    for x in productos:

        df = st.session_state.df[st.session_state.df["productName"] == x]

        df = df.sort_values("scrapeDate", ascending=False)

        current = df.iloc[0]["price"]

        min = df['price'].min()

        min_fecha = df.loc[df['price'] == min]['scrapeDate'].iloc[0]

        max = df['price'].max()

        max_fecha = df.loc[df['price'] == max]['scrapeDate'].iloc[0]

        col1, col2 = st.columns([1,3])


        col1.write(x)
        col1.metric("Last Price", f"{current:,.2f}")
        col3, col4 = col1.columns(2)
        col3.metric("Min Recorded Price", f"{min:,.2f}", str(min_fecha), delta_color="off")
        col4.metric("Max Recorded Price", f"{max:,.2f}", str(max_fecha), delta_color="off")

        fig = px.line(df, x='scrapeDate', y='price', title='Price Over Time')

        col2.plotly_chart(fig, use_container_width=True)




with tab2:
# Convert selected_date to datetime to match the DataFrame's date type
    selected_datetime = st.date_input("Select a date")

    df_before = st.session_state.df[st.session_state.df['scrapeDate'] <= selected_datetime]
    df_after = st.session_state.df[st.session_state.df['scrapeDate'] > selected_datetime]

    products_before_date = df_before['productName'].unique()
    products_after_date = df_after['productName'].unique()

    # Identify products added after the selected date and find their first and recent prices
    added_products = []
    for product in products_after_date:
        if product not in products_before_date:
            product_data = df_after[df_after['productName'] == product]
            first_date = product_data['scrapeDate'].min()
            recent_date = product_data['scrapeDate'].max()
            first_price = product_data[product_data['scrapeDate'] == first_date]['price'].iloc[0]
            recent_price = product_data[product_data['scrapeDate'] == recent_date]['price'].iloc[0]
            added_products.append((product, first_date, first_price, recent_price))


    df_just_after = st.session_state.df[st.session_state.df['scrapeDate'] > selected_datetime]
    products_just_after_date = df_just_after['productName'].unique()

    # Latest products in the dataset
    latest_date = st.session_state.df['scrapeDate'].max()
    df_latest = st.session_state.df[st.session_state.df['scrapeDate'] == latest_date]
    products_latest = df_latest['productName'].unique()

    # Identify products that were present after the selected date but not in the latest dataset
    removed_products = []
    for product in products_just_after_date:
        if product not in products_latest:
            # Get the last date and price the product was seen after the selected date
            product_data = df_just_after[df_just_after['productName'] == product]
            last_seen_date = product_data['scrapeDate'].max()
            last_price = product_data[product_data['scrapeDate'] == last_seen_date]['price'].iloc[0]
            removed_products.append((product, last_seen_date, last_price))
    # Convert the list to DataFrame
    #removed_df = pd.DataFrame(removed_products, columns=['Product Name', 'Last Seen Date', 'Last Price'])

    # Convert the lists to DataFrames
    added_df = pd.DataFrame(added_products, columns=['Product Name', 'Added Date', 'First Price', 'Most Recent Price'])
    removed_df = pd.DataFrame(removed_products, columns=['Product Name', 'Last Seen Date', 'Last Price'])

    # Show the DataFrames
    st.write("Products Added After Selected Date:")
    st.dataframe(added_df.sort_values("Added Date", ascending=False), use_container_width=True, hide_index=True)

    st.write("Products Removed After Selected Date:")
    st.dataframe(removed_df, use_container_width=True, hide_index=True)

with tab3:

    with st.expander("Brands"):
        brand = st.multiselect("Select brands to filter", st.session_state.df["brand"].unique(),st.session_state.df["brand"].unique())

    col1, col2 = st.columns(2)

    percentage_change = col1.number_input("Enter the percentage change", min_value=0.0, value=10.0, step=0.5)


    adf = st.session_state.df[st.session_state.df["brand"].isin(brand)]


    # User input for date range
    date_range = col2.date_input("Select the date range", value=[pd.to_datetime('today').date() - pd.Timedelta(days=30),
                                                               pd.to_datetime('today').date()],
                               min_value=None, max_value=None)

    start_datetime, end_datetime = date_range

    # Filter the DataFrame for the specified date range
    date_filtered_df = adf[(adf['scrapeDate'] >= start_datetime) &
                                           (adf['scrapeDate'] <= end_datetime)]

    # Group by product name to calculate the price change
    price_change_df = date_filtered_df.groupby('productName').agg(StartPrice=('price', 'first'),
                                                                  EndPrice=('price', 'last')).reset_index()

    # Calculate the percentage change for each product
    price_change_df['PriceChange'] = ((price_change_df['EndPrice'] - price_change_df['StartPrice']) /
                                      price_change_df['StartPrice']) * 100



    # Find products that meet the percentage change criterion
    matched_products_df = price_change_df[(price_change_df['PriceChange'] >= percentage_change) |
                                          (price_change_df['PriceChange'] <= -percentage_change)]

    matched_products_df = matched_products_df.sort_values("PriceChange", ascending=False)

    matched_products_df['PriceChange'] = matched_products_df['PriceChange'].astype(float).map("{:,.2f}".format)

    # Show the DataFrame
    st.write(f"Products that changed in price by ±{percentage_change:,.2f}% between {start_datetime} and {end_datetime}:")
    st.dataframe(matched_products_df, hide_index=True, use_container_width=True)


    st.write(f"Unique products: **{len(st.session_state.df['productName'].unique())}**")


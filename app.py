import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
import io
import base64
import pyreadstat

# Set page title and layout
st.set_page_config(page_title="Time Series Analysis & Forecasting", layout="wide")

# Header
st.title("Time Series Analysis & Forecasting")

# File uploader
uploaded_file = st.file_uploader("Upload your data", type=['csv', 'xlsx', 'sav'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.sav'):
            df, meta = pyreadstat.read_sav(uploaded_file)
        else:
            st.error("Unsupported file format.")

        st.success("File uploaded and parsed successfully")

        with st.expander("Show raw data"):
            st.dataframe(df)

        required_cols = ['NUTS Code', 'NUTS name', 'Year']
        if not all(col in df.columns for col in required_cols):
            st.error("Required columns missing. File must contain: NUTS Code, NUTS name, and Year columns")
        else:
            numeric_cols = [col for col in df.columns if col not in required_cols and pd.api.types.is_numeric_dtype(df[col])]

            st.subheader("Spatial Filter")
            region_options = df[['NUTS Code', 'NUTS name']].drop_duplicates()
            region_options['Display'] = region_options['NUTS name'] + ' (' + region_options['NUTS Code'] + ')'
            selected_regions = st.multiselect("Select region(s)", options=region_options['Display'].tolist())

            st.subheader("Variable Filter")
            selected_variable = st.selectbox("Select a variable", numeric_cols)

            filtered_data = None
            if selected_variable and selected_regions:
                selected_codes = [entry.split('(')[-1].strip(')') for entry in selected_regions]
                filtered_data = df[df['NUTS Code'].isin(selected_codes)]

                if not filtered_data.empty:
                    for region_code in selected_codes:
                        region_df = filtered_data[filtered_data['NUTS Code'] == region_code]
                        time_series_data = region_df[['Year', selected_variable]].sort_values('Year')
                        time_series_data = time_series_data.rename(columns={selected_variable: 'Value'})

                        def generate_arima_forecast(data, forecast_steps=8):
                            if len(data) < 2:
                                st.warning("Insufficient data for ARIMA forecast. At least two data points required.")
                                return pd.DataFrame()
                            try:
                                values = data['Value'].values
                                model = ARIMA(values, order=(2, 1, 2))
                                model_fit = model.fit()
                                forecast_result = model_fit.forecast(steps=forecast_steps)
                                latest_year = data['Year'].max()
                                forecast_years = range(latest_year + 1, latest_year + forecast_steps + 1)
                                forecast_df = pd.DataFrame({
                                    'Year': forecast_years,
                                    'Value': forecast_result,
                                    'Type': 'Forecast'
                                })
                                return forecast_df
                            except Exception as e:
                                st.error(f"Error generating ARIMA forecast: {str(e)}")
                                return pd.DataFrame()

                        forecast_data = generate_arima_forecast(time_series_data)
                        time_series_data['Type'] = 'Historical'
                        combined_data = pd.concat([time_series_data, forecast_data], ignore_index=True)

                        st.subheader(f"Time Series Visualization for {region_df['NUTS name'].iloc[0]} ({region_code})")
                        fig = go.Figure()
                        historical = combined_data[combined_data['Type'] == 'Historical']
                        forecast = combined_data[combined_data['Type'] == 'Forecast']

                        fig.add_trace(go.Scatter(
                            x=historical['Year'], y=historical['Value'], mode='lines+markers', name='Historical Data',
                            line=dict(color='#2563eb')
                        ))
                        if not forecast.empty:
                            fig.add_trace(go.Scatter(
                                x=forecast['Year'], y=forecast['Value'], mode='lines+markers', name='ARIMA Forecast',
                                line=dict(color='#9333ea', dash='dash')
                            ))
                            latest_year = historical['Year'].max()
                            fig.add_vline(x=latest_year, line=dict(dash='dot', color='gray'))
                            fig.add_annotation(x=latest_year, y=max(combined_data['Value']),
                                               text='Historical | Forecast', showarrow=False, yanchor='bottom',
                                               font=dict(color='gray'), textangle=-90)

                        fig.update_layout(xaxis_title='Year', yaxis_title=f'{selected_variable} (thousands)',
                                          title=f"{selected_variable} over Time", hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)

                        st.subheader("Data Table")
                        st.dataframe(combined_data)

                        st.subheader("Data Analysis Report")
                        if len(historical) >= 2:
                            first_value = historical['Value'].iloc[0]
                            last_value = historical['Value'].iloc[-1]
                            absolute_change = last_value - first_value
                            percent_change = (absolute_change / abs(first_value)) * 100 if first_value != 0 else 0
                            earliest_year = historical['Year'].min()
                            latest_year = historical['Year'].max()
                            year_span = latest_year - earliest_year
                            avg_annual_change = absolute_change / year_span if year_span > 0 else 0
                            trend_direction = "increasing" if absolute_change > 0 else "decreasing" if absolute_change < 0 else "stable"
                            if not forecast.empty:
                                last_forecast_value = forecast['Value'].iloc[-1]
                                forecasted_change = last_forecast_value - last_value
                                forecasted_percent = (forecasted_change / abs(last_value)) * 100 if last_value != 0 else 0
                                st.markdown(f"#### Summary for {region_df['NUTS name'].iloc[0]} ({region_code})")
                                st.write(f"Between **{earliest_year}** and **{latest_year}**, {selected_variable} exhibited a **{trend_direction}** trend with a net change of **{absolute_change:.2f}k**, or **{percent_change:.2f}%**.")
                                st.write(f"The average annual change during this period was **{avg_annual_change:.2f}k/year**.")
                                st.write(f"### Forecast ({latest_year + 1} - {latest_year + 8})")
                                st.write(f"Over the forecast horizon, the value is expected to reach **{last_forecast_value:.2f}k**, representing a projected change of **{forecasted_change:.2f}k** or **{forecasted_percent:.2f}%**.")
                                st.write(f"The average expected annual growth/change is approximately **{forecasted_change/8:.2f}k/year**.")
                                csv = forecast.to_csv(index=False)
                                st.download_button("Download Forecast Data (CSV)", csv, file_name=f"forecast_{region_code}.csv", mime="text/csv")

                        st.write("*Note: This forecast is based on an ARIMA (p=2, d=1, q=2) model. Actual values may vary due to external influences.*")

                else:
                    st.info("No matching data found for the selected region(s). Please adjust your filters.")

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
else:
    st.info("Please upload a CSV, Excel, or SAV file with time series data.")
    st.markdown("""
    ### Expected file format:
    Your file should include the following columns:
    - **NUTS Code**: Region code
    - **NUTS name**: Region name
    - **Year**: Year of observation
    - **Additional numeric columns**: Variables to analyze (population, GDP, etc.)
    """)

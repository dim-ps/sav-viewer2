import streamlit as st
import pyreadstat
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SPSS (.sav) File Viewer", layout="wide")

st.title("📊 SPSS (.sav) File Viewer and Visualizer")

# File upload
uploaded_file = st.file_uploader("Upload a .sav file", type="sav")

if uploaded_file is not None:
    try:
        # Read .sav file
        df, meta = pyreadstat.read_sav(uploaded_file)
        st.success("File loaded successfully!")

        # Show preview
        st.subheader("🔍 Data Preview")
        st.dataframe(df.head())

        # Summary statistics
        st.subheader("📈 Summary Statistics")
        st.write(df.describe())

        # Data types
        st.subheader("🧾 Column Info")
        st.write(df.dtypes)

        # CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download data as CSV",
            data=csv,
            file_name="exported_data.csv",
            mime="text/csv"
        )

        # Visualization
        st.subheader("📊 Data Visualization")
        num_cols = df.select_dtypes(include='number').columns.tolist()
        cat_cols = df.select_dtypes(include='object').columns.tolist()

        if num_cols or cat_cols:
            col_x = st.selectbox("Select X axis", num_cols + cat_cols)
            col_y = st.selectbox("Select Y axis", num_cols)

            if col_x and col_y:
                fig = px.scatter(df, x=col_x, y=col_y, title=f"{col_y} vs {col_x}")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No numeric or categorical columns available for plotting.")

    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
else:
    st.info("📂 Please upload a .sav file to get started.")
import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import pyreadstat

st.set_page_config(page_title="LFS SPSS Viewer", layout="wide")
st.title("📊 Greek Labour Force Survey (.sav) Viewer")

# Load variable description mapping
desc_path = "LFS_VARIABLE DESCRIPTION_PUF_1987_2024_GR.xlsx"
desc_df = pd.read_excel(desc_path)

# Extract mapping: 2021+ code → Greek label
mapping_df = desc_df[['2021+', 'Περιγραφή μεταβλητής']].dropna()
var_map = dict(zip(mapping_df['2021+'], mapping_df['Περιγραφή μεταβλητής']))

# File uploader
uploaded_file = st.file_uploader("Upload LFS .sav file", type="sav")

if uploaded_file:
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        # Load data
        df, meta = pyreadstat.read_sav(tmp_path)
        df.rename(columns=lambda col: var_map.get(col, col), inplace=True)

        st.success("✅ File loaded successfully!")

        # Sidebar Filters
        st.sidebar.header("🔎 Filter Data")
        for col in df.select_dtypes(include=['object', 'category']).columns:
            options = df[col].dropna().unique().tolist()
            selected = st.sidebar.multiselect(f"Filter by: {col}", options)
            if selected:
                df = df[df[col].isin(selected)]

        # Data preview
        st.subheader("📋 Data Preview")
        st.dataframe(df.head(100))

        # Summary
        st.subheader("📈 Summary Statistics")
        st.write(df.describe(include='all'))

        # Download filtered data
        st.download_button(
            "📥 Download filtered data as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="filtered_data.csv",
            mime="text/csv"
        )

        # Visualization
        st.subheader("📊 Visualization")
        all_cols = df.columns.tolist()
        num_cols = df.select_dtypes(include='number').columns.tolist()
        cat_cols = df.select_dtypes(exclude='number').columns.tolist()

        chart_type = st.selectbox("Select chart type", ["Histogram", "Bar Chart", "Scatter", "Box Plot"])

        if chart_type == "Histogram":
            col = st.selectbox("Select numeric column", num_cols)
            fig = px.histogram(df, x=col)
        elif chart_type == "Bar Chart":
            col = st.selectbox("Select categorical column", cat_cols)
            fig = px.bar(df[col].value_counts().reset_index(), x="index", y=col)
        elif chart_type == "Scatter":
            x = st.selectbox("X axis", num_cols)
            y = st.selectbox("Y axis", num_cols)
            fig = px.scatter(df, x=x, y=y)
        elif chart_type == "Box Plot":
            x = st.selectbox("Category", cat_cols)
            y = st.selectbox("Value", num_cols)
            fig = px.box(df, x=x, y=y)

        st.plotly_chart(fig, use_container_width=True)

        # Group & Aggregate
        st.subheader("📊 Group & Aggregate")
        group_col = st.selectbox("Group by (categorical)", cat_cols)
        agg_col = st.selectbox("Aggregate column (numeric)", num_cols)
        agg_func = st.selectbox("Aggregation function", ["mean", "sum", "count", "median", "min", "max"])

        if st.button("Compute Grouped Table"):
            grouped = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
            st.dataframe(grouped)

    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📂 Please upload a .sav file to begin.")

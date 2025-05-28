import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import pyreadstat

st.set_page_config(page_title="LFS SPSS Viewer", layout="wide")
st.title("📊 Greek Labour Force Survey (.sav) Viewer")

# Load variable description mapping from Excel
desc_path = "LFS_VARIABLE DESCRIPTION_PUF_1987_2024_GR.xlsx"
desc_df = pd.read_excel(desc_path)
mapping_df = desc_df[['2021+', 'Περιγραφή μεταβλητής']].dropna()
var_map = dict(zip(mapping_df['2021+'], mapping_df['Περιγραφή μεταβλητής']))

# Upload SAV file
uploaded_file = st.file_uploader("Upload LFS .sav file", type="sav")

if uploaded_file:
    try:
        # Save uploaded SAV file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        # Read SAV with value labels
        df, meta = pyreadstat.read_sav(tmp_path)

        # Rename columns using Excel variable names
        df.rename(columns=lambda col: var_map.get(col, col), inplace=True)

        # Replace coded values using metadata
        for var, labels in meta.variable_value_labels.items():
            var_name = var_map.get(var, var)
            if var_name in df.columns:
                df[var_name] = df[var_name].map(labels)

        st.success("✅ File loaded and decoded successfully!")

        # Sidebar Filters
        st.sidebar.header("🔎 Filter Data")
        for col in df.select_dtypes(include=['object', 'category']).columns:
            options = df[col].dropna().unique().tolist()
            selected = st.sidebar.multiselect(f"Filter by: {col}", options)
            if selected:
                df = df[df[col].isin(selected)]

        # Data Preview
        st.subheader("📋 Data Preview")
        st.dataframe(df.head(100))

        # Summary Statistics
        st.subheader("📈 Summary Statistics")
        st.write(df.describe(include='all'))

        # CSV Export
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

        # Codebook Viewer
        st.subheader("📖 Codebook Viewer")
        codebook = []

        for var, labels in meta.variable_value_labels.items():
            greek_name = var_map.get(var, "")
            label_str = "; ".join([f"{k} = {v}" for k, v in labels.items()])
            codebook.append({"Variable Code": var, "Label": greek_name, "Values": label_str})

        codebook_df = pd.DataFrame(codebook)
        search_term = st.text_input("Search codebook (variable or description):")
        if search_term:
            codebook_df = codebook_df[
                codebook_df.apply(lambda row: search_term.lower() in str(row["Variable Code"]).lower()
                                                  or search_term.lower() in str(row["Label"]).lower(), axis=1)
            ]

        st.dataframe(codebook_df)

    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📂 Please upload a .sav file to begin.")
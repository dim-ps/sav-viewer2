import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import pyreadstat
import os

st.set_page_config(page_title="SPSS (.sav) viewer", layout="wide")
st.title("📊 SPSS (.sav) viewer")

# --- Guide of Use ---
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
**Upload Instructions:**\n\nThis tool is ideal for exploring open-access public microdata from official surveys such as:\n- 🟦 Labour Force Survey (LFS)\n- 🟨 European Union Statistics on Income and Living Conditions (EU-SILC)\n
- Upload one or more `.sav` files (from the Greek Labour Force Survey or other sources).
- Also include the variable description file: `LFS_VARIABLE DESCRIPTION_PUF_1987_2024_GR.xlsx`.

**What This App Does:**
- Automatically reads and merges multiple `.sav` files with the same structure.
- Applies variable name replacements using the Greek dictionary.
- Decodes value labels (e.g., gender codes into words like Άνδρας, Γυναίκα).
- Lets you explore, visualize, and export your filtered dataset.
- Includes a codebook viewer with searchable descriptions.

**Recommended:**
- Upload datasets from the same structure/year group.
- Use the sidebar to filter by any categorical field (region, gender, etc.).
- Check the "Group & Aggregate" tab for summaries.
""")

# Load variable description mapping from Excel
desc_path = "LFS_VARIABLE DESCRIPTION_PUF_1987_2024_GR.xlsx"
desc_df = pd.read_excel(desc_path)
mapping_df = desc_df[['2021+', 'Περιγραφή μεταβλητής']].dropna()
var_map = dict(zip(mapping_df['2021+'], mapping_df['Περιγραφή μεταβλητής']))

# Upload multiple SAV files
uploaded_files = st.file_uploader("Upload one or more LFS .sav files", type="sav", accept_multiple_files=True)

if uploaded_files:
    try:
        combined_data = []
        all_value_labels = {}

        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            df, meta = pyreadstat.read_sav(tmp_path)
            df["source_file"] = os.path.basename(uploaded_file.name)

            for var, labels in meta.variable_value_labels.items():
                all_value_labels[var] = labels

            combined_data.append(df)

        df = pd.concat(combined_data, ignore_index=True)
        df.rename(columns=lambda col: var_map.get(col, col), inplace=True)

        for var, labels in all_value_labels.items():
            var_name = var_map.get(var, var)
            if var_name in df.columns:
                df[var_name] = df[var_name].map(labels)

        st.success("✅ All files loaded and combined successfully!")

        st.sidebar.header("🔎 Filter Data")
        for col in df.select_dtypes(include=['object', 'category']).columns:
            options = df[col].dropna().unique().tolist()
            selected = st.sidebar.multiselect(f"Filter by: {col}", options)
            if selected:
                df = df[df[col].isin(selected)]

        st.subheader("📋 Data Preview")
        st.dataframe(df.head(100))

        st.subheader("📈 Summary Statistics")
        st.write(df.describe(include='all'))

        st.download_button(
            "📥 Download filtered data as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="combined_filtered_data.csv",
            mime="text/csv"
        )

        st.subheader("📊 Visualization")
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

        st.subheader("📊 Group & Aggregate")
        group_col = st.selectbox("Group by (categorical)", cat_cols, index=cat_cols.index("YPA_R") if "YPA_R" in cat_cols else 0)
        agg_col = st.selectbox("Aggregate column (numeric)", num_cols)
        agg_func = st.selectbox("Aggregation function", ["mean", "sum", "count", "median", "min", "max"])

        if st.button("Compute Grouped Table"):
            grouped = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
            st.dataframe(grouped)

        
    st.subheader("🗺️ Regional Map (NUTS 2 - YPA_R)")

    # Choropleth map generation
    try:
        import geopandas as gpd

        # Load the shapefile
        shapefile = "NUTS_RG_01M_2021_4326.shp"
        gdf = gpd.read_file(shapefile)

        # Filter NUTS level 2
        gdf = gdf[gdf['LEVL_CODE'] == 2]

        # Ensure YPA_R match
        if "YPA_R" in df.columns:
            # Aggregation input
            map_value_col = st.selectbox("Column to map (numeric)", num_cols)
            map_agg_func = st.selectbox("Aggregation method", ["mean", "sum", "count"])
            region_stats = df.groupby("YPA_R")[map_value_col].agg(map_agg_func).reset_index()
            region_stats.columns = ["NUTS_ID", "value"]

            # Merge to GeoDataFrame
            gdf_map = gdf.merge(region_stats, on="NUTS_ID")

            # Plot map
            st.map(gdf_map.set_geometry("geometry").to_crs(epsg=4326))
            st.write(gdf_map[["NUTS_ID", "value"]])
        else:
            st.warning("Column 'YPA_R' not found in dataset.")

    except Exception as e:
        st.warning(f"Could not load map: {e}")

    st.subheader("📖 Codebook Viewer")
    
        codebook = []
        for var, labels in all_value_labels.items():
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
    st.info("📂 Please upload one or more .sav files to begin.")
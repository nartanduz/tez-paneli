import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Highway Traffic Analysis Dashboard", layout="wide")

st.title("🚗 Highway Traffic Flow and Speed Analysis Dashboard")
st.markdown("This dashboard analyzes vehicle time headway (THW) and speed relationships obtained from computer vision data.")

# --- 1. DATA LOADING (FROM REAL EXCEL FILES) ---
@st.cache_data
def get_data():
    # Keep exact file names to match your local files, but change display names to Section 1 & 2
    dosyalar = {
        'Section 1': 'helvaci_tum_sayfalar_headways.xlsx', 
        'Section 2': 'video3_tum_sayfalar_headways.xlsx'
    }
    # Keep exact sheet names
    seritler = ['SOL', 'ORTA', 'SAG']
    all_pairs = []

    def map_vtype(v):
        v_str = str(v).lower()
        if 'araba' in v_str: return 'C'  # Car
        if 'minibus' in v_str: return 'M' # Minibus
        if 'kamyon' in v_str or 'otobus' in v_str: return 'T' # Truck/Bus
        return 'U'

    for lokasyon, dosya_adi in dosyalar.items():
        try:
            xl = pd.ExcelFile(dosya_adi)
            for serit in seritler:
                if serit in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=serit)
                    # Keep column names in Turkish as they are in your Excel file!
                    df = df.dropna(subset=['Hiz (km/h)', 'Gecis Araligi (sn)', 'Arac Tipi']).reset_index(drop=True)
                    
                    for i in range(1, len(df)):
                        lider_hiz = df.loc[i-1, 'Hiz (km/h)']
                        lider_tip = df.loc[i-1, 'Arac Tipi']
                        takipci_hiz = df.loc[i, 'Hiz (km/h)']
                        takipci_tip = df.loc[i, 'Arac Tipi']
                        thw = df.loc[i, 'Gecis Araligi (sn)']
                        
                        cift = f"{map_vtype(lider_tip)}{map_vtype(takipci_tip)}"
                        
                        if thw > 0 and lider_hiz > 40:
                            # English Lane Names Translation
                            if serit == 'SAG':
                                lane_name = "Right Lane"
                            elif serit == 'ORTA':
                                lane_name = "Middle Lane"
                            else:
                                lane_name = "Left Lane"

                            all_pairs.append({
                                'Location': lokasyon,
                                'Lane': lane_name,
                                'Leader_Speed': lider_hiz,
                                'Follower_Speed': takipci_hiz,
                                'THW': thw,
                                'Vehicle_Pair': cift
                            })
        except Exception as e:
            st.sidebar.error(f"Error: {dosya_adi} could not be read. Please check the file name.")

    df_pairs = pd.DataFrame(all_pairs)
    
    if df_pairs.empty:
        return df_pairs, []

    # Speed Bins (km/h)
    bins = [0, 80, 90, 100, 110, 120, 130, 140, 999]
    labels = ['<80', '80-89', '90-99', '100-109', '110-119', '120-129', '130-139', '140+']
    df_pairs['Speed_Bin'] = pd.cut(df_pairs['Leader_Speed'], bins=bins, labels=labels, right=False)
    
    return df_pairs, labels

df, speed_labels = get_data()

# --- 2. SIDEBAR (CONTROLS) ---
st.sidebar.header("Control Panel")

if not df.empty:
    location_selection = st.sidebar.radio("Location / Dataset Selection:", ["All (Section 1 + Section 2)", "Section 1", "Section 2"])
    lane_selection = st.sidebar.radio("Lane Selection:", ["Left Lane", "Middle Lane", "Right Lane"])
    pair_selection = st.sidebar.multiselect("Vehicle Interaction Types:", df['Vehicle_Pair'].unique(), default=['CC', 'CT', 'TC'])
    speed_bin_selection = st.sidebar.multiselect("Leader Vehicle Speed Range (km/h):", speed_labels, default=speed_labels)
    zoom_limit = st.sidebar.slider("Axis / Seconds Limit (Zoom):", min_value=5, max_value=20, value=20)

    # --- 3. FILTERING ---
    df_filtered = df.copy()

    if location_selection == "Section 1":
        df_filtered = df_filtered[df_filtered['Location'] == 'Section 1']
    elif location_selection == "Section 2":
        df_filtered = df_filtered[df_filtered['Location'] == 'Section 2']

    df_filtered = df_filtered[df_filtered['Lane'] == lane_selection]
    df_filtered = df_filtered[df_filtered['Vehicle_Pair'].isin(pair_selection)]
    df_filtered = df_filtered[df_filtered['Speed_Bin'].isin(speed_bin_selection)]

    # --- 4. TOP METRIC CARDS ---
    st.subheader(f"Selected Data Summary ({lane_selection} | {location_selection})")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Number of Vehicles (N)", value=f"{len(df_filtered)}")
    with col2:
        st.metric(label="Average THW", value=f"{df_filtered['THW'].mean():.2f} sec" if not df_filtered.empty else "0")
    with col3:
        st.metric(label="Median THW", value=f"{df_filtered['THW'].median():.2f} sec" if not df_filtered.empty else "0")
    with col4:
        st.metric(label="Average Leader Speed", value=f"{df_filtered['Leader_Speed'].mean():.1f} km/h" if not df_filtered.empty else "0")

    st.divider()

    # --- 5. TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Interactive THW Distribution", 
        "📈 THW Analysis by Speed Bins",
        "🏎️ Speed Distribution (Boxplot)",
        "🧮 3-Parameter Analysis Matrix"
    ])

    with tab1:
        st.markdown("### Time Headway by Vehicle Pairs")
        if not df_filtered.empty:
            fig_thw_box = px.box(df_filtered, x="Vehicle_Pair", y="THW", color="Vehicle_Pair",
                                 points="all", 
                                 title="THW Distribution by Vehicle Interaction Types")
            fig_thw_box.update_yaxes(range=[0, zoom_limit]) 
            fig_thw_box.update_layout(xaxis_title="Vehicle Pair (Leader-Follower)", yaxis_title="THW (Seconds)")
            st.plotly_chart(fig_thw_box, use_container_width=True)
        else:
            st.warning("No data found to display.")

    with tab2:
        if not df_filtered.empty:
            col_grafik1, col_grafik2 = st.columns(2)
            
            with col_grafik1:
                st.markdown("##### THW Internal Distribution in 10 km/h Bins (Violin)")
                fig_violin = px.violin(df_filtered, x="Speed_Bin", y="THW", color="Vehicle_Pair",
                                       box=True, points="all",
                                       category_orders={"Speed_Bin": speed_labels})
                fig_violin.update_yaxes(range=[0, zoom_limit])
                fig_violin.update_layout(xaxis_title="Leader Vehicle Speed (km/h)", yaxis_title="THW (Seconds)")
                st.plotly_chart(fig_violin, use_container_width=True)
                
            with col_grafik2:
                st.markdown("##### Number of Vehicles in Speed Bins (N)")
                df_count = df_filtered.groupby(['Speed_Bin', 'Vehicle_Pair']).size().reset_index(name='Vehicle_Count')
                fig_bar = px.bar(df_count, x="Speed_Bin", y="Vehicle_Count", color="Vehicle_Pair",
                                 text="Vehicle_Count", barmode="group",
                                 category_orders={"Speed_Bin": speed_labels})
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(xaxis_title="Leader Vehicle Speed (km/h)", yaxis_title="Number of Vehicles")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("No data found for these filters.")

    with tab3:
        st.markdown("### Speed Distributions by Vehicle Interactions (Boxplot)")
        if not df_filtered.empty:
            fig_speed_box = px.box(df_filtered, x="Vehicle_Pair", y="Leader_Speed", color="Vehicle_Pair",
                                   points="outliers",
                                   labels={"Leader_Speed": "Leader Vehicle Speed (km/h)", "Vehicle_Pair": "Vehicle Pair"})
            fig_speed_box.update_layout(xaxis_title="Vehicle Interaction Type", yaxis_title="Speed (km/h)")
            st.plotly_chart(fig_speed_box, use_container_width=True)
        else:
            st.warning("No data found to display speed distribution.")

    with tab4:
        st.markdown("### 3-Parameter THW Analysis Matrix (Heatmap)")
        if not df_filtered.empty:
            pivot_df = pd.pivot_table(df_filtered, values='THW', index='Speed_Bin', columns='Vehicle_Pair', aggfunc='mean', observed=False)
            fig_heatmap = px.imshow(pivot_df, text_auto=".2f", aspect="auto", color_continuous_scale="YlOrRd",
                                    labels=dict(x="Vehicle Pair (Leader-Follower)", y="Leader Vehicle Speed (km/h)", color="Avg. THW (sec)"))
            fig_heatmap.update_layout(xaxis_title="Vehicle Pair", yaxis_title="Leader Vehicle Speed (km/h)")
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.markdown("#### Detailed Matrix Table")
            st.dataframe(pivot_df.style.background_gradient(cmap='YlOrRd', axis=None).format("{:.2f} s", na_rep="No Data"), use_container_width=True)
        else:
            st.warning("No data found to create the matrix.")
else:
    st.error("Excel files could not be read or are empty! Please ensure 'helvaci_tum_sayfalar_headways.xlsx' and 'video3_tum_sayfalar_headways.xlsx' are in the same directory as this script.")

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.ticker as ticker

# 1. Page Settings
st.set_page_config(layout="wide", page_title="Advanced Traffic Flow & Speed Dashboard")
st.title("Traffic Flow, THW and Speed Analysis Dashboard")

# 2. Load and Combine Data
@st.cache_data
def load_data():
    lanes = {"SOL": "Left Lane", "ORTA": "Middle Lane", "SAG": "Right Lane"}
    
    files = {
        "Section 1": "helvaci_tum_sayfalar_headways.xlsx",
        "Section 2": "video3_tum_sayfalar_headways.xlsx"
    }
    dfs = []
    
    for loc_name, file_name in files.items():
        try:
            for lane, title in lanes.items():
                df = pd.read_excel(file_name, sheet_name=lane)
                cols = ['c-c', 'c-t', 't-c', 't-t', 'c-m', 'm-c', 'm-m', 'm-t', 't-m']
                available_cols = [c for c in cols if c in df.columns]
                
                speed_col = None
                for sc in ['Hiz (km/h)', 'Hız (km/h)', 'Speed']:
                    if sc in df.columns:
                        speed_col = sc
                        break
                        
                if speed_col:
                    df_sub = df[available_cols + [speed_col]].copy()
                    rename_dict = {c: c.upper().replace('-', '') for c in available_cols}
                    df_sub = df_sub.rename(columns=rename_dict)
                    
                    df_melt = df_sub.melt(id_vars=[speed_col], var_name='Combination', value_name='THW').dropna()
                    df_melt = df_melt.rename(columns={speed_col: 'Leader_Speed'})
                else:
                    df_sub = df[available_cols].copy()
                    rename_dict = {c: c.upper().replace('-', '') for c in available_cols}
                    df_sub = df_sub.rename(columns=rename_dict)
                    
                    df_melt = df_sub.melt(var_name='Combination', value_name='THW').dropna()
                    df_melt['Leader_Speed'] = np.nan
                    
                df_melt['Lane'] = title
                df_melt['Location'] = loc_name
                dfs.append(df_melt)
        except Exception as e:
            st.sidebar.warning(f"Note: Could not read {file_name}. Ensure it is in the directory.")
            
    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        
        bins = [0, 80, 90, 100, 110, 120, 130, 140, 999]
        labels = ['<80', '80-89', '90-99', '100-109', '110-119', '120-129', '130-139', '140+']
        
        if df_all['Leader_Speed'].notna().any():
            df_all['Speed_Bin'] = pd.cut(df_all['Leader_Speed'], bins=bins, labels=labels, right=False)
            return df_all, labels
        else:
            df_all['Speed_Bin'] = "Hız Verisi Yok"
            return df_all, ["Hız Verisi Yok"]
            
    return pd.DataFrame(), []

df_all, speed_labels = load_data()

if df_all.empty:
    st.warning("No data could be loaded. Please check the Excel file names in the directory.")
    st.stop()

# 3. SIDEBAR (CONTROL PANEL)
st.sidebar.header("Control Panel")

secilen_lokasyon = st.sidebar.radio(
    "Location / Dataset Selection:",
    ["All Sections", "Only Section 1", "Only Section 2"]
)

secilen_serit = st.sidebar.radio(
    "Lane Selection:", 
    ["Left Lane", "Middle Lane", "Right Lane"]
)

SABIT_SIRALAMA = ['CC', 'CT', 'TC', 'TT', 'CM', 'MC', 'MM', 'MT', 'TM']
# Araç Seçimine ALL Eklendi
secilen_araclar = st.sidebar.multiselect(
    "Vehicle Interaction Types:", 
    ['ALL'] + SABIT_SIRALAMA,
    default=['ALL', 'CC', 'CT', 'TC']
)

# Hız Seçimine ALL Eklendi
if 'Speed_Bin' in df_all.columns and not df_all['Speed_Bin'].eq("Hız Verisi Yok").all():
    secilen_hizlar = st.sidebar.multiselect(
        "Leader Vehicle Speed Range (km/h):",
        ['ALL'] + speed_labels,
        default=['ALL']
    )
else:
    secilen_hizlar = ['ALL']

max_thw = st.sidebar.slider("Axis / Seconds Limit (Zoom):", min_value=5, max_value=80, value=20, step=1)

# 4. BASE FILTERING (Lokasyon ve Şerit)
df_base = df_all.copy()

if secilen_lokasyon == "Only Section 1":
    df_base = df_base[df_base['Location'] == "Section 1"]
elif secilen_lokasyon == "Only Section 2":
    df_base = df_base[df_base['Location'] == "Section 2"]

df_base = df_base[(df_base['Lane'] == secilen_serit) & (df_base['THW'] <= max_thw)]

# ALL seçeneğini anlayıp üst bilgi kartları için veriyi filtreleme
valid_veh = SABIT_SIRALAMA if 'ALL' in secilen_araclar else secilen_araclar
valid_speed = speed_labels if 'ALL' in secilen_hizlar else secilen_hizlar

df_filtered = df_base[(df_base['Combination'].isin(valid_veh)) & (df_base['Speed_Bin'].isin(valid_speed))]

# 5. METRIC CARDS
st.markdown(f"### Selected Data Summary ({secilen_serit} | {secilen_lokasyon})")
col1, col2, col3 = st.columns(3)

col1.metric("Total Number of Vehicles (N)", len(df_filtered))
if not df_filtered.empty:
    col2.metric("Average THW", f"{df_filtered['THW'].mean():.2f} sec")
    col3.metric("Median THW", f"{df_filtered['THW'].median():.2f} sec")
else:
    st.warning("No vehicle interactions found for the selected filters! Try selecting different vehicles or speed ranges.")

# 6. PLOTTING
if not df_filtered.empty:
    st.markdown("---")
    # ALL için gri renk (#555555) eklendi
    colors = {'ALL': '#555555', 'CC': 'black', 'CT': 'red', 'TC': 'limegreen', 'TT': 'mediumblue',
              'CM': 'purple', 'MC': 'darkorange', 'MM': 'saddlebrown', 'MT': 'c', 'TM': 'm'}
    
    # Çizilecek kombinasyonları ve hızları belirleme
    plot_groups = []
    
    combs_to_plot = []
    if 'ALL' in secilen_araclar: combs_to_plot.append('ALL')
    combs_to_plot.extend([c for c in SABIT_SIRALAMA if c in secilen_araclar])

    speeds_to_plot = []
    if 'ALL' in secilen_hizlar: speeds_to_plot.append('ALL')
    speeds_to_plot.extend([s for s in speed_labels if s in secilen_hizlar])
    
    for comb in combs_to_plot:
        for speed in speeds_to_plot:
            subset = df_base.copy()
            
            # ALL kontrolü ile filtreleme
            if comb != 'ALL':
                subset = subset[subset['Combination'] == comb]
            else:
                subset = subset[subset['Combination'].isin(valid_veh)]
                
            if speed != 'ALL':
                subset = subset[subset['Speed_Bin'] == speed]
            else:
                subset = subset[subset['Speed_Bin'].isin(valid_speed)]

            data = subset['THW'].values
            if len(data) >= 2: # Boxplot için minimum 2 veri
                plot_groups.append({'comb': comb, 'speed': speed, 'data': data})
    
    if not plot_groups:
        st.warning("Not enough data to plot boxplots (minimum 2 data points required per category).")
    else:
        fig_width = max(15, len(plot_groups) * 2.5)
        fig, ax = plt.subplots(figsize=(fig_width, 8))
        
        x_labels = []
        
        for i, group in enumerate(plot_groups):
            x_base = i * 2  
            comb = group['comb']
            speed = group['speed']
            data = group['data']
            
            c = colors.get(comb, 'black')
            ax.axvline(x_base, color='black', linestyle='-', linewidth=0.8)

            # Histogram
            hist, bin_edges = np.histogram(data, bins=max_thw, range=(0, max_thw))
            if np.max(hist) > 0: hist = hist / np.max(hist) * 0.9  
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            bin_height = (bin_edges[1] - bin_edges[0])
            
            for h, y in zip(hist, bin_centers):
                if h > 0:
                    ax.add_patch(Rectangle((x_base, y - bin_height/2), h, bin_height, facecolor=c, alpha=0.4, edgecolor=c, linewidth=1.5))

            # Boxplot
            x_left = x_base - 0.4 
            q1, med, q3 = np.percentile(data, [25, 50, 75])
            mean_val = np.mean(data)
            
            iqr = q3 - q1
            lower_limit = max(np.min(data), q1 - 1.5 * iqr)
            upper_limit = min(np.max(data), q3 + 1.5 * iqr)

            box_width = 0.5
            box = Rectangle((x_left - box_width/2, q1), box_width, q3 - q1, facecolor='none', edgecolor=c, linewidth=1.5)
            ax.add_patch(box)
            ax.hlines(med, x_left - box_width/2, x_left + box_width/2, color=c, linewidth=1.5)
            ax.plot(x_left, mean_val, marker='s', color=c, markerfacecolor='none', markersize=5, markeredgewidth=1.2)
            ax.vlines(x_left, q3, upper_limit, color=c, linewidth=1.5)
            ax.vlines(x_left, lower_limit, q1, color=c, linewidth=1.5)
            
            x_labels.append(f"{comb}\n{speed}\n(N={len(data)})")
            
        ax.set_xticks([i * 2 for i in range(len(plot_groups))])
        ax.set_xticklabels(x_labels)
        ax.set_xlim(-1.5, len(plot_groups) * 2)
        ax.set_ylim(0, max_thw)
        
        if max_thw > 20: ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
        else: ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
            
        ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='lightgray')
        ax.set_ylabel('THW (Seconds)', fontsize=12)
        ax.set_title("Interactive THW Data Distribution by Speed & Vehicle Pair", fontsize=14, fontweight='bold')
        
        st.pyplot(fig)
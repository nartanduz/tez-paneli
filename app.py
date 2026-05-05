import streamlit as st
import pandas as pd
import plotly.express as px

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Otoyol Trafik Analiz Paneli", layout="wide")

st.title("🚗 Otoyol Trafik Akış ve Hız Analizi Paneli")
st.markdown("Bu panel, görüntü işleme verilerinden elde edilen araç takip mesafesi (THW) ve hız ilişkilerini analiz eder.")

# --- 1. VERİ YÜKLEME (GERÇEK EXCEL DOSYALARINDAN) ---
@st.cache_data
def get_data():
    dosyalar = {
        'Helvacı': 'helvaci_tum_sayfalar_headways.xlsx', 
        'Video 3': 'video3_tum_sayfalar_headways.xlsx'
    }
    seritler = ['SOL', 'ORTA', 'SAG']
    all_pairs = []

    def map_vtype(v):
        v_str = str(v).lower()
        if 'araba' in v_str: return 'C'
        if 'minibus' in v_str: return 'M'
        if 'kamyon' in v_str or 'otobus' in v_str: return 'T'
        return 'U'

    for lokasyon, dosya_adi in dosyalar.items():
        try:
            xl = pd.ExcelFile(dosya_adi)
            for serit in seritler:
                if serit in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=serit)
                    df = df.dropna(subset=['Hiz (km/h)', 'Gecis Araligi (sn)', 'Arac Tipi']).reset_index(drop=True)
                    
                    for i in range(1, len(df)):
                        lider_hiz = df.loc[i-1, 'Hiz (km/h)']
                        lider_tip = df.loc[i-1, 'Arac Tipi']
                        takipci_hiz = df.loc[i, 'Hiz (km/h)']
                        takipci_tip = df.loc[i, 'Arac Tipi']
                        thw = df.loc[i, 'Gecis Araligi (sn)']
                        
                        cift = f"{map_vtype(lider_tip)}{map_vtype(takipci_tip)}"
                        
                        if thw > 0 and lider_hiz > 40:
                            # TÜRKÇE KARAKTER DÜZELTMESİ (Sağ Şerit sorunu için)
                            duzgun_serit_adi = "Sağ Şerit" if serit == 'SAG' else f"{serit.capitalize()} Şerit"

                            all_pairs.append({
                                'Lokasyon': lokasyon,
                                'Serit': duzgun_serit_adi,
                                'Lider_Hizi': lider_hiz,
                                'Takipci_Hizi': takipci_hiz,
                                'THW': thw,
                                'Arac_Cifti': cift
                            })
        except Exception as e:
            st.sidebar.error(f"Hata: {dosya_adi} okunamadı. Dosya adını kontrol edin.")

    df_pairs = pd.DataFrame(all_pairs)
    
    # Eğer veri boş gelirse hata vermemesi için kontrol
    if df_pairs.empty:
        return df_pairs, []

    bins = [0, 80, 90, 100, 110, 120, 130, 140, 999]
    labels = ['<80', '80-89', '90-99', '100-109', '110-119', '120-129', '130-139', '140+']
    df_pairs['Hiz_Araligi'] = pd.cut(df_pairs['Lider_Hizi'], bins=bins, labels=labels, right=False)
    
    return df_pairs, labels

df, hiz_etiketleri = get_data()

# --- 2. YAN MENÜ (KONTROLLER) ---
st.sidebar.header("Kontrol Paneli")

if not df.empty:
    lokasyon_secimi = st.sidebar.radio("Lokasyon / Veri Seti Seçimi:", ["Tümü (Helvacı + Video 3)", "Helvacı", "Video 3"])
    serit_secimi = st.sidebar.radio("Şerit Seçimi:", ["Sol Şerit", "Orta Şerit", "Sağ Şerit"])
    secilen_cift = st.sidebar.multiselect("Araç Geçiş Türleri:", df['Arac_Cifti'].unique(), default=['CC', 'CT', 'TC'])
    secilen_hiz_araliklari = st.sidebar.multiselect("Lider Araç Hız Aralığı (km/h):", hiz_etiketleri, default=hiz_etiketleri)
    zoom_limiti = st.sidebar.slider("Eksen / Saniye Limiti (Zoom):", min_value=5, max_value=20, value=20)

    # --- 3. FİLTRELEME İŞLEMLERİ ---
    df_filtered = df.copy()

    if lokasyon_secimi == "Helvacı":
        df_filtered = df_filtered[df_filtered['Lokasyon'] == 'Helvacı']
    elif lokasyon_secimi == "Video 3":
        df_filtered = df_filtered[df_filtered['Lokasyon'] == 'Video 3']

    df_filtered = df_filtered[df_filtered['Serit'] == serit_secimi]
    df_filtered = df_filtered[df_filtered['Arac_Cifti'].isin(secilen_cift)]
    df_filtered = df_filtered[df_filtered['Hiz_Araligi'].isin(secilen_hiz_araliklari)]

    # --- 4. ÜST BİLGİ KARTLARI ---
    st.subheader(f"Seçilen Veri Özeti ({serit_secimi} | {lokasyon_secimi})")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Toplam Araç Sayısı (N)", value=f"{len(df_filtered)}")
    with col2:
        st.metric(label="Ortalama THW", value=f"{df_filtered['THW'].mean():.2f} Saniye" if not df_filtered.empty else "0")
    with col3:
        st.metric(label="Medyan THW", value=f"{df_filtered['THW'].median():.2f} Saniye" if not df_filtered.empty else "0")
    with col4:
        st.metric(label="Ortalama Lider Hızı", value=f"{df_filtered['Lider_Hizi'].mean():.1f} km/h" if not df_filtered.empty else "0")

    st.divider()

    # --- 5. SEKMELER (TABS) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 İnteraktif THW Veri Dağılımı", 
        "📈 Hız Dilimlerine Göre THW Analizi",
        "🏎️ Hız Dağılımı (Boxplot)",
        "🧮 3 Parametreli Analiz Matrisi"
    ])

    with tab1:
        st.markdown("### Araç Çiftlerine Göre Takip Mesafesi")
        if not df_filtered.empty:
            fig_thw_box = px.box(df_filtered, x="Arac_Cifti", y="THW", color="Arac_Cifti",
                                 points="all", 
                                 title="Araç Etkileşim Türlerine Göre THW Dağılımı")
            fig_thw_box.update_yaxes(range=[0, zoom_limiti]) 
            fig_thw_box.update_layout(xaxis_title="Araç Çifti (Lider-Takipçi)", yaxis_title="THW (Saniye)")
            st.plotly_chart(fig_thw_box, use_container_width=True)
        else:
            st.warning("Görüntülenecek veri bulunamadı.")

    with tab2:
        if not df_filtered.empty:
            col_grafik1, col_grafik2 = st.columns(2)
            
            with col_grafik1:
                st.markdown("##### 10 km/h Dilimlerde THW İç Dağılımı (Violin)")
                fig_violin = px.violin(df_filtered, x="Hiz_Araligi", y="THW", color="Arac_Cifti",
                                       box=True, points="all",
                                       category_orders={"Hiz_Araligi": hiz_etiketleri})
                fig_violin.update_yaxes(range=[0, zoom_limiti])
                fig_violin.update_layout(xaxis_title="Lider Araç Hızı (km/h)", yaxis_title="THW (Saniye)")
                st.plotly_chart(fig_violin, use_container_width=True)
                
            with col_grafik2:
                st.markdown("##### Hız Dilimlerindeki Araç Sayısı (N)")
                df_count = df_filtered.groupby(['Hiz_Araligi', 'Arac_Cifti']).size().reset_index(name='Arac_Sayisi')
                fig_bar = px.bar(df_count, x="Hiz_Araligi", y="Arac_Sayisi", color="Arac_Cifti",
                                 text="Arac_Sayisi", barmode="group",
                                 category_orders={"Hiz_Araligi": hiz_etiketleri})
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(xaxis_title="Lider Araç Hızı (km/h)", yaxis_title="Araç Sayısı (Adet)")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("Bu filtrelere uygun veri bulunamadı.")

    with tab3:
        st.markdown("### Araç Etkileşimlerine Göre Hız Dağılımları (Boxplot)")
        if not df_filtered.empty:
            fig_speed_box = px.box(df_filtered, x="Arac_Cifti", y="Lider_Hizi", color="Arac_Cifti",
                                   points="outliers",
                                   labels={"Lider_Hizi": "Lider Aracın Hızı (km/h)", "Arac_Cifti": "Araç Çifti"})
            fig_speed_box.update_layout(xaxis_title="Araç Etkileşim Türü", yaxis_title="Hız (km/h)")
            st.plotly_chart(fig_speed_box, use_container_width=True)
        else:
            st.warning("Hız dağılımı gösterilecek veri bulunamadı.")

    with tab4:
        st.markdown("### 3 Parametreli THW Analiz Matrisi (Isı Haritası)")
        if not df_filtered.empty:
            pivot_df = pd.pivot_table(df_filtered, values='THW', index='Hiz_Araligi', columns='Arac_Cifti', aggfunc='mean', observed=False)
            fig_heatmap = px.imshow(pivot_df, text_auto=".2f", aspect="auto", color_continuous_scale="YlOrRd",
                                    labels=dict(x="Araç Çifti (Lider-Takipçi)", y="Lider Aracın Hızı (km/h)", color="Ort. THW (sn)"))
            fig_heatmap.update_layout(xaxis_title="Araç Çifti", yaxis_title="Lider Aracın Hızı (km/h)")
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.markdown("#### Detaylı Matris Tablosu")
            st.dataframe(pivot_df.style.background_gradient(cmap='YlOrRd', axis=None).format("{:.2f} sn", na_rep="Veri Yok"), use_container_width=True)
        else:
            st.warning("Matris oluşturulacak veri bulunamadı.")
else:
    st.error("Excel dosyaları okunamadı veya içleri boş! Lütfen 'helvaci_tum_sayfalar_headways.xlsx' ve 'video3_tum_sayfalar_headways.xlsx' dosyalarının bu kod ile aynı klasörde olduğundan emin olun.")
"""
=============================================================================
  MONITOR ELECTORAL — SEGUNDA VUELTA PRESIDENCIAL PERÚ 2026
  Fuente: API Oficial ONPE · Persistencia: Google Sheets
=============================================================================
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import time
import base64, os
from datetime import datetime

# Logos pre-procesados (sin fondo negro) — cargados desde archivos locales
def _logo(fname):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

LOGO_FP = _logo("Logo_de_fuerza_popular.png")
LOGO_JP = _logo("Logo_juntos_por_el_Peru.png")

# =============================================================================
# IDENTIDAD DE CANDIDATOS
# =============================================================================
CANDIDATOS = {
    "FUJIMORI": {
        "display": "Keiko Fujimori",
        "partido": "Fuerza Popular",
        "color":   "#D95F02",
        "fill":    "rgba(217,95,2,0.10)",
        "bar":     "bar-fp",
        "logo":    LOGO_FP,
    },
    "SANCHEZ": {
        "display": "Roberto Sánchez",
        "partido": "Juntos por el Perú",
        "color":   "#1B7A3E",
        "fill":    "rgba(27,122,62,0.10)",
        "bar":     "bar-jp",
        "logo":    LOGO_JP,
    },
}

def apellido_key(nombre: str) -> str:
    """Escanea todos los tokens del nombre hasta encontrar uno que esté en CANDIDATOS."""
    tokens = nombre.strip().upper().split()
    for token in tokens:
        if token in CANDIDATOS:
            return token
    return tokens[1] if len(tokens) > 1 else tokens[0]

def info_cand(nombre: str) -> dict:
    return CANDIDATOS.get(apellido_key(nombre), {
        "display": nombre, "partido": "", "color": "#6B7280",
        "fill": "rgba(107,114,128,0.1)", "bar": "bar-default", "logo": None,
    })

# =============================================================================
# PÁGINA Y CSS
# =============================================================================
st.set_page_config(page_title="Monitor Electoral ONPE 2026", page_icon="🇵🇪",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#F4F6F9;color:#111827;}
.block-container{padding-top:1rem!important;padding-bottom:0!important;}
.main > div:last-child{padding-bottom:0!important;}
[data-testid="stVerticalBlock"] > div:last-child{margin-bottom:0!important;}
#MainMenu,footer,header{visibility:hidden;}

.footer-fixed {
    margin-top: 40px;
    border-top: 1px solid #E5E7EB;
    padding: 14px 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

.topbar{
    background:#fff;border-bottom:1px solid #E5E7EB;
    padding:14px 28px;margin:-1rem -1rem 24px -1rem;
    display:flex;align-items:center;justify-content:space-between;
    box-shadow:0 1px 4px rgba(0,0,0,0.07);
}
.topbar h1{font-size:1.05rem;font-weight:700;color:#111827;margin:0;}
.topbar p{font-size:0.7rem;color:#6B7280;margin:3px 0 0;font-family:'IBM Plex Mono',monospace;}
.live-pill{
    display:inline-flex;align-items:center;gap:7px;
    background:#ECFDF5;border:1px solid #6EE7B7;
    color:#065F46;font-size:0.7rem;font-weight:700;
    padding:6px 14px;border-radius:20px;letter-spacing:0.06em;
}
.ldot{width:7px;height:7px;border-radius:50%;background:#10B981;animation:bl 1.8s infinite;}
@keyframes bl{0%,100%{opacity:1}50%{opacity:0.2}}

/* STATS */
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.stat-card{background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.05);}
.stat-label{font-size:0.67rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.09em;font-weight:600;margin-bottom:7px;}
.stat-value{font-size:1.75rem;font-weight:700;color:#111827;font-family:'IBM Plex Mono',monospace;line-height:1;}
.stat-sub{font-size:0.68rem;color:#9CA3AF;margin-top:5px;font-family:'IBM Plex Mono',monospace;}
.green{color:#059669;}

/* CANDIDATE CARDS */
.cand-card{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:20px 22px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);}
.cand-top{display:flex;align-items:center;gap:14px;margin-bottom:14px;}
.cand-logo{width:56px;height:56px;object-fit:contain;border-radius:8px;border:1px solid #F3F4F6;padding:4px;background:#FAFAFA;}
.cand-name{font-size:1.05rem;font-weight:700;color:#111827;}
.cand-party{font-size:0.72rem;color:#6B7280;margin-top:2px;}
.cand-pct{font-size:2.1rem;font-weight:700;font-family:'IBM Plex Mono',monospace;margin-left:auto;}
.bar-track{height:10px;background:#F3F4F6;border-radius:5px;overflow:hidden;margin-bottom:8px;}
.bar-fp{height:100%;border-radius:5px;background:#D95F02;}
.bar-jp{height:100%;border-radius:5px;background:#1B7A3E;}
.bar-default{height:100%;border-radius:5px;background:#9CA3AF;}
.cand-sub{font-size:0.7rem;color:#9CA3AF;font-family:'IBM Plex Mono',monospace;}

/* PANELS */
.panel{background:#fff;border:1px solid #E5E7EB;border-radius:12px;padding:20px 22px;box-shadow:0 1px 3px rgba(0,0,0,0.05);margin-bottom:14px;}
.sec{font-size:0.67rem;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:0.1em;
     margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #F3F4F6;}
.ts{font-family:'IBM Plex Mono',monospace;font-size:0.63rem;color:#9CA3AF;text-align:right;margin-top:14px;}

/* DELTA badge */
.delta-up{color:#059669;font-size:0.72rem;font-weight:600;margin-left:6px;}
.delta-dn{color:#DC2626;font-size:0.72rem;font-weight:600;margin-left:6px;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# GOOGLE SHEETS
# =============================================================================
SHEET_ID   = "1tt3HjPNU_NO4B3WGOOYyoR8ezG3ktyj9j68ILwMKHxQ"
SHEET_NAME = "Hoja 1"
SCOPES     = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def cargar_historial():
    try:
        rows = get_sheet().get_all_records()
        for r in rows:
            for k,v in r.items():
                if k != "hora":
                    try: r[k] = float(v)
                    except: pass
        return rows
    except: return []

def guardar_punto(punto):
    try:
        sh = get_sheet()
        if not sh.get_all_values():
            sh.append_row(list(punto.keys()))
        sh.append_row(list(punto.values()))
    except Exception as e:
        st.session_state["sheet_error"] = str(e)

def actualizar_historial(totales, participantes):
    actas = totales.get("actasContabilizadas", 0)
    if "historial" not in st.session_state:
        st.session_state["historial"] = cargar_historial()
    hist = st.session_state["historial"]
    if not hist or hist[-1]["actas"] != actas:
        pt = {"hora": datetime.now().strftime("%H:%M:%S"), "actas": actas}
        for p in participantes:
            pt[apellido_key(p.get("nombreCandidato",""))] = round(p.get("porcentajeVotosValidos",0), 3)
        hist.append(pt)
        st.session_state["historial"] = hist
        guardar_punto(pt)
    return hist

# =============================================================================
# API ONPE
# =============================================================================
URL_P = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/participantes?idEleccion=10&tipoFiltro=eleccion"
URL_T = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/totales?idEleccion=10&tipoFiltro=eleccion"
HDR = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept":"application/json, text/plain, */*",
    "Accept-Language":"es-PE,es;q=0.9",
    "Referer":"https://resultadosegundavuelta.onpe.gob.pe/",
    "Origin":"https://resultadosegundavuelta.onpe.gob.pe",
    "sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"same-origin",
}

def _get(url):
    try:
        r = requests.get(url, headers=HDR, timeout=15)
        if r.status_code != 200: return None
        if "text/html" in r.headers.get("content-type",""): return None
        d = r.json()
        return d.get("data") if d.get("success") else None
    except: return None

@st.cache_data(ttl=30)
def obtener_participantes(): return _get(URL_P)

@st.cache_data(ttl=30)
def obtener_totales(): return _get(URL_T)

# =============================================================================
# GRÁFICO DE LÍNEAS — mejorado para distinguir tendencias
# =============================================================================
def grafico_lineas(historial, participantes):
    if len(historial) < 2:
        return None

    df = pd.DataFrame(historial)
    horas = df["hora"].tolist()
    cols = [c for c in df.columns if c not in ("hora","actas")]

    fig = go.Figure()

    for col in cols:
        info = CANDIDATOS.get(col, {"color":"#999","display":col})
        vals = df[col].tolist()

        # Etiquetas: valor + delta respecto al punto anterior
        labels = []
        for i, v in enumerate(vals):
            if i == 0:
                labels.append(f"{v:.2f}%")
            else:
                delta = v - vals[i-1]
                arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "–")
                labels.append(f"{v:.2f}%  {arrow}{abs(delta):.2f}")

        fig.add_trace(go.Scatter(
            x=horas, y=vals,
            mode="lines+markers+text",
            name=info["display"],
            line=dict(color=info["color"], width=2.5),
            marker=dict(color=info["color"], size=8,
                        line=dict(color="#FFFFFF", width=2)),
            text=labels,
            textposition="top center",
            textfont=dict(color=info["color"], size=10, family="IBM Plex Mono"),
            hovertemplate=f"<b>{info['display']}</b><br>%{{x}}<br>%{{y:.3f}}%<extra></extra>",
        ))

    # Línea 50%
    fig.add_hline(y=50, line=dict(color="#9CA3AF", width=1, dash="dash"),
                  annotation_text="50%",
                  annotation_font=dict(color="#9CA3AF", size=10, family="Inter"),
                  annotation_position="top right")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#374151", family="Inter", size=11),
        xaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            showline=True, linecolor="#E5E7EB",
            tickfont=dict(color="#6B7280", size=10, family="IBM Plex Mono"),
            title=None,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            ticksuffix="%",
            tickfont=dict(color="#6B7280", size=10, family="IBM Plex Mono"),
            range=[40, 60],   # eje Y fijo 40–60% — líneas centradas y movimientos visibles
            dtick=5,          # marcas cada 5%: 40, 45, 50, 55, 60
            title=None,
        ),
        legend=dict(
            orientation="h", x=0, y=1.15,
            font=dict(color="#374151", size=11, family="Inter"),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=20, t=45, b=10),
        height=340,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#fff", bordercolor="#E5E7EB",
                        font=dict(color="#111827", size=11, family="Inter")),
    )
    return fig

# =============================================================================
# RENDER
# =============================================================================
def render(participantes, totales, historial):
    actas_pct      = totales.get("actasContabilizadas", 0)
    contabilizadas = totales.get("contabilizadas", 0)
    total_actas    = totales.get("totalActas", 0)
    votos_validos  = totales.get("totalVotosValidos", 0)
    votos_emitidos = totales.get("totalVotosEmitidos", 0)
    ts_ms          = totales.get("fechaActualizacion", 0)
    try:    ts_str = datetime.fromtimestamp(ts_ms/1000).strftime("%d/%m/%Y  %H:%M:%S")
    except: ts_str = "—"

    ordenados = sorted(participantes, key=lambda x: x.get("porcentajeVotosValidos",0), reverse=True)
    lider  = ordenados[0]
    seg    = ordenados[1] if len(ordenados) > 1 else {}
    pct_l  = float(lider.get("porcentajeVotosValidos",0))
    pct_s  = float(seg.get("porcentajeVotosValidos",0))
    ventaja   = pct_l - pct_s
    diff_voto = int(lider.get("totalVotosValidos",0)) - int(seg.get("totalVotosValidos",0))
    info_l = info_cand(lider.get("nombreCandidato",""))

    # ── TOPBAR ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="topbar">
        <div>
            <h1>🇵🇪 &nbsp;Monitor Electoral · Segunda Vuelta Presidencial Perú 2026</h1>
            <p>Fuente: ONPE · Actualización ONPE: {ts_str}</p>
        </div>
        <div class="live-pill"><div class="ldot"></div>EN VIVO</div>
    </div>
    """, unsafe_allow_html=True)

    # ── STATS ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="stat-label">Actas contabilizadas</div>
            <div class="stat-value">{actas_pct:.3f}<span style="font-size:1rem;color:#9CA3AF">%</span></div>
            <div class="stat-sub">{contabilizadas:,} de {total_actas:,} actas</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Votos válidos</div>
            <div class="stat-value" style="font-size:1.4rem">{votos_validos:,}</div>
            <div class="stat-sub">de {votos_emitidos:,} emitidos</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Ventaja actual</div>
            <div class="stat-value green">+{ventaja:.3f}<span style="font-size:1rem">%</span></div>
            <div class="stat-sub">{info_l['display']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Diferencia en votos</div>
            <div class="stat-value" style="font-size:1.4rem">{diff_voto:,}</div>
            <div class="stat-sub">votos de ventaja</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_izq, col_der = st.columns([1, 1.15], gap="large")

    # ── COLUMNA IZQUIERDA ─────────────────────────────────────────────────────
    with col_izq:
        st.markdown('<div class="sec">Resultados por candidato</div>', unsafe_allow_html=True)

        for p in ordenados:
            nombre = p.get("nombreCandidato","")
            info   = info_cand(nombre)
            pct    = float(p.get("porcentajeVotosValidos",0))
            votos  = p.get("totalVotosValidos",0)
            pct_em = p.get("porcentajeVotosEmitidos",0)

            # Delta respecto al punto anterior en historial
            delta_str = ""
            if len(historial) >= 2:
                prev = historial[-2]
                curr = historial[-1]
                key  = apellido_key(nombre)
                if key in prev and key in curr:
                    d = curr[key] - prev[key]
                    if abs(d) > 0.0001:
                        color_d = "#059669" if d > 0 else "#DC2626"
                        arrow = "▲" if d > 0 else "▼"
                        delta_str = f'<span style="color:{color_d};font-size:0.72rem;font-weight:600;margin-left:6px;">{arrow} {abs(d):.3f}pp</span>'

            logo_src = info.get("logo") or ""
            logo_html = (
                f'<img src="{logo_src}" style="width:56px;height:56px;object-fit:contain;border-radius:8px;border:1px solid #F3F4F6;padding:4px;background:#FAFAFA;flex-shrink:0;">' if logo_src
                else '<div style="width:56px;height:56px;border-radius:8px;background:#F3F4F6;border:1px solid #E5E7EB;display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex-shrink:0;">🏛️</div>'
            )
            color = info["color"]
            display = info["display"]
            partido = info["partido"]

            st.markdown(f"""
            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:12px;
                        padding:20px 22px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
                    {logo_html}
                    <div style="flex:1;">
                        <div style="font-size:1.05rem;font-weight:700;color:#111827;">
                            {display}{delta_str}
                        </div>
                        <div style="font-size:0.72rem;color:#6B7280;margin-top:2px;">{partido}</div>
                    </div>
                    <div style="font-size:2.1rem;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{color};">
                        {pct:.3f}%
                    </div>
                </div>
                <div style="height:10px;background:#F3F4F6;border-radius:5px;overflow:hidden;margin-bottom:8px;">
                    <div style="height:100%;width:{pct}%;background:{color};border-radius:5px;"></div>
                </div>
                <div style="font-size:0.7rem;color:#9CA3AF;font-family:'IBM Plex Mono',monospace;">
                    {votos:,} votos válidos &nbsp;·&nbsp; {pct_em:.3f}% s/ votos emitidos
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Tabla
        st.markdown('<div class="sec" style="margin-top:18px">Tabla comparativa</div>', unsafe_allow_html=True)
        filas = []
        for p in ordenados:
            info = info_cand(p.get("nombreCandidato",""))
            filas.append({
                "Candidato":  info["display"],
                "Partido":    info["partido"],
                "Votos":      f"{p.get('totalVotosValidos',0):,}",
                "% válidos":  f"{p.get('porcentajeVotosValidos',0):.3f}%",
                "% emitidos": f"{p.get('porcentajeVotosEmitidos',0):.3f}%",
            })
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    # ── COLUMNA DERECHA ────────────────────────────────────────────────────────
    with col_der:
        st.markdown('<div class="sec">Evolución temporal · % votos válidos</div>', unsafe_allow_html=True)

        if len(historial) < 2:
            st.markdown("""
            <div class="panel" style="height:340px;display:flex;align-items:center;
                 justify-content:center;flex-direction:column;gap:10px;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                <div style="font-size:0.75rem;color:#9CA3AF;font-family:'IBM Plex Mono',monospace;
                     letter-spacing:0.08em;margin-top:8px;">Esperando siguiente actualización de la ONPE...</div>
                <div style="font-size:0.65rem;color:#D1D5DB;">El gráfico aparece al registrar 2 o más puntos</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            fig = grafico_lineas(historial, participantes)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Registro de cambios
        if historial:
            st.markdown('<div class="sec" style="margin-top:18px">Registro de actualizaciones ONPE</div>', unsafe_allow_html=True)
            log_data = []
            hist_slice = historial[-15:]  # últimos 15 puntos
            for i, h in enumerate(reversed(hist_slice)):
                # índice real en hist_slice (reversed)
                idx_real = len(hist_slice) - 1 - i
                cc = [k for k in h.keys() if k not in ("hora", "actas")]
                row = {"Hora": h["hora"], "Actas %": f"{h['actas']:.3f}%"}
                vals = {}
                for c in cc:
                    label = CANDIDATOS.get(c, {}).get("display", "").split()[0] or c
                    row[label] = f"{h[c]:.3f}%"
                    vals[c] = h[c]

                # Diferencia porcentual entre los dos candidatos en este punto
                if len(cc) >= 2:
                    diff = abs(vals[cc[0]] - vals[cc[1]])
                    lider_key = cc[0] if vals[cc[0]] > vals[cc[1]] else cc[1]
                    lider_label = CANDIDATOS.get(lider_key, {}).get("display", "").split()[0] or lider_key
                    row["Ventaja"] = f"+{diff:.3f}% ({lider_label})"

                    # Delta de ventaja respecto al punto anterior
                    if idx_real > 0:
                        h_prev = hist_slice[idx_real - 1]
                        diff_prev = abs(h_prev.get(cc[0], 0) - h_prev.get(cc[1], 0))
                        delta_v = diff - diff_prev
                        if abs(delta_v) > 0.0001:
                            arrow = "▲" if delta_v > 0 else "▼"
                            row["Δ Ventaja"] = f"{arrow}{abs(delta_v):.3f}pp"
                        else:
                            row["Δ Ventaja"] = "–"
                    else:
                        row["Δ Ventaja"] = "–"

                log_data.append(row)
            st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)

    ahora = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
    st.markdown(
        f'<p class="ts">Dashboard: {ahora} &nbsp;·&nbsp; {len(historial)} punto(s) en Google Sheets &nbsp;·&nbsp; refresco ~30 s</p>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="footer-fixed">
        <span style="font-size:0.7rem;color:#9CA3AF;font-family:'IBM Plex Mono',monospace;letter-spacing:0.08em;">
            &copy; 2026 &nbsp;
            <strong style="color:#6B7280;letter-spacing:0.12em;">darig</strong>

    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# MAIN
# =============================================================================
def main():
    participantes = obtener_participantes()
    totales       = obtener_totales()

    if not participantes or not totales:
        st.markdown("""
        <div style="margin-top:80px;text-align:center;">
            <p style="color:#EF4444;font-size:0.9rem;font-weight:600;">Sin conexión con la API de la ONPE</p>
            <p style="color:#9CA3AF;font-size:0.75rem;font-family:'IBM Plex Mono',monospace;">Reintentando en 30 segundos...</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        historial = actualizar_historial(totales, participantes)
        render(participantes, totales, historial)

    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()

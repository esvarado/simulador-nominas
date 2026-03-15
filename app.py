import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import textwrap

st.set_page_config(page_title="Simulador didáctico de nóminas", layout="wide")

st.markdown("""
<style>
.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2rem;
}
.small-note {
    font-size: 0.85rem;
    color: #666;
}
</style>
""", unsafe_allow_html=True)


def eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def input_conectado(label, min_value, max_value, value, step, key_base):

    if key_base not in st.session_state:
        st.session_state[key_base] = float(value)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.slider(
            f"{label}",
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=key_base,
        )

    with col2:
        st.number_input(
            f"{label} (€)",
            min_value=min_value,
            max_value=max_value,
            step=step,
            key=key_base,
        )

    return float(st.session_state[key_base])


def cuota_irpf_madrid_simplificada(base_liquidable_general, minimo_personal=5550.0):
    tramos = [
        (12450.0, 0.19),
        (20200.0, 0.24),
        (35200.0, 0.30),
        (60000.0, 0.37),
        (300000.0, 0.45),
        (None, 0.47),
    ]
    cuota_base = aplicar_tramos(max(0.0, base_liquidable_general), tramos)
    cuota_minimo = aplicar_tramos(max(0.0, minimo_personal), tramos)
    return max(0.0, cuota_base - cuota_minimo)


def reduccion_rendimientos_trabajo(rnt):
    if rnt <= 14852:
        return 7302.0
    if rnt < 19747.5:
        return max(0.0, 7302.0 - 1.75 * (rnt - 14852.0))
    return 0.0


def calcular_nomina(
    salario_base,
    complemento_personal,
    complemento_puesto,
    plus_transporte,
    plus_convenio,
    horas_extra,
    precio_hora_extra,
    pagas_ano,
    prorrata_extras,
    irpf_pct,
    cot_cc_pct,
    cot_desempleo_pct,
    cot_formacion_pct,
    emp_cc_pct,
    emp_desempleo_pct,
    emp_formacion_pct,
    emp_fogasa_pct,
    emp_at_ep_pct,
):
    complementos_salariales = complemento_personal + complemento_puesto + plus_convenio
    importe_horas_extra = horas_extra * precio_hora_extra

    devengo_ordinario = salario_base + complementos_salariales + plus_transporte + importe_horas_extra
    base_extra = salario_base + complementos_salariales

    if pagas_ano == 14:
        num_extras = 2
    else:
        num_extras = max(pagas_ano - 12, 0)

    # Prorrata que afecta al cobro mensual
    if prorrata_extras and num_extras > 0:
        prorrata_mensual = (base_extra * num_extras) / 12
    else:
        prorrata_mensual = 0.0

    total_devengado = devengo_ordinario + prorrata_mensual

    # Base de cotización correcta según número de pagas
    base_salarial = salario_base + complementos_salariales

    if pagas_ano == 14 and not prorrata_extras:
        # La Seguridad Social prorratea las extras en la base mensual
        base_cotizacion = (base_salarial * 14 / 12) + importe_horas_extra
    else:
        # 12 pagas o 14 con prorrata
        base_cotizacion = base_salarial + prorrata_mensual + importe_horas_extra

    # Deducciones trabajador
    cuota_cc = base_cotizacion * cot_cc_pct / 100
    cuota_desempleo = base_cotizacion * cot_desempleo_pct / 100
    cuota_formacion = base_cotizacion * cot_formacion_pct / 100
    irpf = total_devengado * irpf_pct / 100

    total_deducciones = cuota_cc + cuota_desempleo + cuota_formacion + irpf
    neto = total_devengado - total_deducciones

    # Cotizaciones empresa
    emp_cc = base_cotizacion * emp_cc_pct / 100
    emp_desempleo = base_cotizacion * emp_desempleo_pct / 100
    emp_formacion = base_cotizacion * emp_formacion_pct / 100
    emp_fogasa = base_cotizacion * emp_fogasa_pct / 100
    emp_at_ep = base_cotizacion * emp_at_ep_pct / 100

    total_cot_empresa = emp_cc + emp_desempleo + emp_formacion + emp_fogasa + emp_at_ep
    coste_empresa = total_devengado + total_cot_empresa

    # Bruto anual
    if pagas_ano == 12:
        bruto_anual = total_devengado * 12
    else:
        if prorrata_extras:
            bruto_anual = total_devengado * 12
        else:
            bruto_anual = devengo_ordinario * 12 + base_extra * num_extras

    # Neto anual estimado
    if pagas_ano == 12 or prorrata_extras:
        neto_anual_estimado = neto * 12
    else:
        neto_anual_estimado = (neto * 12) + (base_extra * num_extras * (1 - irpf_pct / 100))

    return {
        "salario_base": salario_base,
        "complemento_personal": complemento_personal,
        "complemento_puesto": complemento_puesto,
        "plus_convenio": plus_convenio,
        "plus_transporte": plus_transporte,
        "horas_extra": horas_extra,
        "precio_hora_extra": precio_hora_extra,
        "importe_horas_extra": importe_horas_extra,
        "prorrata_mensual": prorrata_mensual,
        "total_devengado": total_devengado,
        "base_cotizacion": base_cotizacion,
        "cuota_cc": cuota_cc,
        "cuota_desempleo": cuota_desempleo,
        "cuota_formacion": cuota_formacion,
        "irpf": irpf,
        "total_deducciones": total_deducciones,
        "neto": neto,
        "emp_cc": emp_cc,
        "emp_desempleo": emp_desempleo,
        "emp_formacion": emp_formacion,
        "emp_fogasa": emp_fogasa,
        "emp_at_ep": emp_at_ep,
        "total_cot_empresa": total_cot_empresa,
        "coste_empresa": coste_empresa,
        "bruto_anual": bruto_anual,
        "neto_anual_estimado": neto_anual_estimado,
        "num_extras": num_extras,
        "pagas_ano": pagas_ano,
        "prorrata_extras": prorrata_extras,
        "irpf_pct": irpf_pct,
    }

def calcular_retribucion_flexible_madrid(
    bruto_anual,
    ss_trab_anual,
    ss_empresa_anual,
    comida_anual,
    transporte_anual,
    seguro_anual,
    guarderia_anual,
    acciones_anual,
    pension_anual,
    personas_seguro=1,
    dias_laborables=220,
    minimo_personal=5550.0,
    smi_anual=15876.0,
):
    # -------------------------------------------------
    # 1) LÍMITE GLOBAL DE SALARIO EN ESPECIE
    # -------------------------------------------------
    especie_inicial = (
        comida_anual
        + transporte_anual
        + seguro_anual
        + guarderia_anual
        + acciones_anual
    )

    limite_especie_30 = 0.30 * bruto_anual
    limite_por_smi = max(0.0, bruto_anual - smi_anual)
    especie_maxima_permitida = min(limite_especie_30, limite_por_smi)

    ajuste_especie_aplicado = False
    factor_ajuste = 1.0

    if especie_inicial > especie_maxima_permitida and especie_inicial > 0:
        ajuste_especie_aplicado = True
        factor_ajuste = especie_maxima_permitida / especie_inicial

        comida_anual *= factor_ajuste
        transporte_anual *= factor_ajuste
        seguro_anual *= factor_ajuste
        guarderia_anual *= factor_ajuste
        acciones_anual *= factor_ajuste

    especie_final = (
        comida_anual
        + transporte_anual
        + seguro_anual
        + guarderia_anual
        + acciones_anual
    )

    # -------------------------------------------------
    # 2) LÍMITES EXENTOS POR CONCEPTO
    # -------------------------------------------------
    comida_exenta = min(comida_anual, 11.0 * dias_laborables)
    comida_sujeta = max(0.0, comida_anual - comida_exenta)

    transporte_exento = min(transporte_anual, 1500.0)
    transporte_sujeto = max(0.0, transporte_anual - transporte_exento)

    seguro_exento = min(seguro_anual, 500.0 * personas_seguro)
    seguro_sujeto = max(0.0, seguro_anual - seguro_exento)

    guarderia_exenta = max(0.0, guarderia_anual)
    guarderia_sujeta = 0.0

    acciones_exentas = min(acciones_anual, 12000.0)
    acciones_sujetas = max(0.0, acciones_anual - acciones_exentas)

    # -------------------------------------------------
    # 3) REDUCCIÓN POR PLAN DE PENSIONES
    #    Modelo prudente:
    #    menor entre aportación, 10.000 y 30% del RNT previo
    # -------------------------------------------------
    exento_previo_pension = (
        comida_exenta
        + transporte_exento
        + seguro_exento
        + guarderia_exenta
        + acciones_exentas
    )

    rit_previo = bruto_anual - exento_previo_pension
    rnt_previo = max(0.0, rit_previo - ss_trab_anual - 2000.0)
    limite_pension_porcentaje = 0.30 * rnt_previo
    pension_reduccion = min(pension_anual, 10000.0, limite_pension_porcentaje)

    # -------------------------------------------------
    # 4) TOTALES FLEXIBLE
    # -------------------------------------------------
    flexible_total = especie_final + pension_anual
    total_exento = (
        comida_exenta
        + transporte_exento
        + seguro_exento
        + guarderia_exenta
        + acciones_exentas
    )

    total_sujeto_especie = (
        comida_sujeta
        + transporte_sujeto
        + seguro_sujeto
        + guarderia_sujeta
        + acciones_sujetas
    )

    salario_monetario = bruto_anual - flexible_total

    # -------------------------------------------------
    # 5) ESCENARIO SIN FLEXIBLE
    # -------------------------------------------------
    rit_sin = bruto_anual
    gastos_deducibles_sin = ss_trab_anual + 2000.0
    rnt_sin = max(0.0, rit_sin - gastos_deducibles_sin)
    red_trab_sin = reduccion_rendimientos_trabajo(rnt_sin)
    blg_sin = max(0.0, rnt_sin - red_trab_sin)
    base_gravable_sin = max(0.0, blg_sin - minimo_personal)
    irpf_sin = cuota_irpf_madrid_simplificada(blg_sin, minimo_personal=minimo_personal)
    neto_sin = bruto_anual - ss_trab_anual - irpf_sin

    # -------------------------------------------------
    # 6) ESCENARIO CON FLEXIBLE
    # -------------------------------------------------
    rit_con = bruto_anual - total_exento
    gastos_deducibles_con = ss_trab_anual + 2000.0
    rnt_con = max(0.0, rit_con - gastos_deducibles_con)
    red_trab_con = reduccion_rendimientos_trabajo(rnt_con)
    blg_con = max(0.0, rnt_con - red_trab_con - pension_reduccion)
    base_gravable_con = max(0.0, blg_con - minimo_personal)
    irpf_con = cuota_irpf_madrid_simplificada(blg_con, minimo_personal=minimo_personal)

    neto_monetario_con = salario_monetario - ss_trab_anual - irpf_con
    neto_economico_con = neto_monetario_con + flexible_total

    ahorro_fiscal = max(0.0, irpf_sin - irpf_con)
    mejora_poder_adquisitivo = neto_economico_con - neto_sin

    return {
        # generales
        "bruto_anual": bruto_anual,
        "ss_trab_anual": ss_trab_anual,
        "ss_empresa_anual": ss_empresa_anual,
        "minimo_personal": minimo_personal,
        "smi_anual": smi_anual,

        # flexible
        "flexible_total": flexible_total,
        "salario_monetario": salario_monetario,
        "total_exento": total_exento,
        "total_sujeto_especie": total_sujeto_especie,
        "pension_reduccion": pension_reduccion,

        # control límites
        "limite_especie_30": limite_especie_30,
        "limite_por_smi": limite_por_smi,
        "especie_inicial": especie_inicial,
        "especie_final": especie_final,
        "ajuste_especie_aplicado": ajuste_especie_aplicado,
        "factor_ajuste": factor_ajuste,
        "limite_pension_porcentaje": limite_pension_porcentaje,

        # detalle conceptos
        "comida_exenta": comida_exenta,
        "comida_sujeta": comida_sujeta,
        "transporte_exento": transporte_exento,
        "transporte_sujeto": transporte_sujeto,
        "seguro_exento": seguro_exento,
        "seguro_sujeto": seguro_sujeto,
        "guarderia_exenta": guarderia_exenta,
        "guarderia_sujeta": guarderia_sujeta,
        "acciones_exentas": acciones_exentas,
        "acciones_sujetas": acciones_sujetas,

        # escenario sin flexible
        "rit_sin": rit_sin,
        "gastos_deducibles_sin": gastos_deducibles_sin,
        "rnt_sin": rnt_sin,
        "red_trab_sin": red_trab_sin,
        "blg_sin": blg_sin,
        "base_gravable_sin": base_gravable_sin,
        "irpf_sin": irpf_sin,
        "neto_sin": neto_sin,

        # escenario con flexible
        "rit_con": rit_con,
        "gastos_deducibles_con": gastos_deducibles_con,
        "rnt_con": rnt_con,
        "red_trab_con": red_trab_con,
        "blg_con": blg_con,
        "base_gravable_con": base_gravable_con,
        "irpf_con": irpf_con,
        "neto_monetario_con": neto_monetario_con,
        "neto_economico_con": neto_economico_con,

        # resultados finales
        "ahorro_fiscal": ahorro_fiscal,
        "mejora_poder_adquisitivo": mejora_poder_adquisitivo,
        "carga_total_empleo_sin": irpf_sin + ss_trab_anual + ss_empresa_anual,
        "carga_total_empleo_con": irpf_con + ss_trab_anual + ss_empresa_anual,
    }

def render_nomina_html(datos_empresa, datos_trabajador, periodo, r):
    devengos_rows = [
        ("Salario base", "", eur(r["salario_base"])),
        ("Complemento personal", "", eur(r["complemento_personal"])),
        ("Complemento de puesto", "", eur(r["complemento_puesto"])),
        ("Plus convenio", "", eur(r["plus_convenio"])),
        ("Plus transporte", "", eur(r["plus_transporte"])),
        ("Horas extra", f'{r["horas_extra"]:.2f} h', eur(r["importe_horas_extra"])),
        ("Prorrata pagas extra", "", eur(r["prorrata_mensual"])),
    ]

    ded_rows = [
        ("Contingencias comunes", "Trabajador", eur(r["cuota_cc"])),
        ("Desempleo", "Trabajador", eur(r["cuota_desempleo"])),
        ("Formación profesional", "Trabajador", eur(r["cuota_formacion"])),
        ("IRPF", f'{r["irpf_pct"]:.2f}%', eur(r["irpf"])),
    ]

    dev_html = "".join([
        f'<div class="nomina-row"><div>{c}</div><div class="center">{u}</div><div class="right">{i}</div></div>'
        for c, u, i in devengos_rows
    ])
    ded_html = "".join([
        f'<div class="nomina-row"><div>{c}</div><div class="center">{t}</div><div class="right">{i}</div></div>'
        for c, t, i in ded_rows
    ])

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
body {{ margin: 0; padding: 16px; background: #ffffff; font-family: Arial, Helvetica, sans-serif; color: #111; }}
.nomina-wrapper {{ background: white; border: 2px solid #222; padding: 18px; color: #111; }}
.nomina-title {{ text-align: center; font-size: 20px; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px; }}
.nomina-subtitle {{ text-align: center; font-size: 12px; margin-bottom: 16px; color: #444; }}
.nomina-grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }}
.nomina-box {{ border: 1px solid #222; padding: 10px; min-height: 110px; box-sizing: border-box; }}
.nomina-box-title {{ font-weight: 700; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; border-bottom: 1px solid #222; padding-bottom: 4px; }}
.nomina-row {{ display: grid; grid-template-columns: 1.6fr 0.6fr 0.8fr; gap: 8px; padding: 5px 6px; border-bottom: 1px solid #ddd; font-size: 13px; box-sizing: border-box; }}
.nomina-row.header {{ font-weight: 700; background: #f2f2f2; border-top: 1px solid #222; border-bottom: 1px solid #222; padding: 7px 6px; }}
.nomina-row.total {{ font-weight: 700; background: #f6f6f6; border-top: 1px solid #222; }}
.nomina-section {{ margin-top: 12px; margin-bottom: 14px; }}
.nomina-section-title {{ font-weight: 700; font-size: 13px; background: #eaeaea; border: 1px solid #222; padding: 6px 8px; }}
.nomina-summary-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 12px; }}
.nomina-summary-box {{ border: 1px solid #222; padding: 8px 10px; background: #fafafa; box-sizing: border-box; }}
.nomina-summary-label {{ font-size: 12px; color: #444; }}
.nomina-summary-value {{ font-weight: 700; font-size: 17px; margin-top: 4px; }}
.nomina-footer {{ margin-top: 16px; border-top: 1px solid #222; padding-top: 8px; font-size: 11px; color: #444; }}
.right {{ text-align: right; }} .center {{ text-align: center; }}
</style>
</head>
<body>
<div class="nomina-wrapper">
<div class="nomina-title">RECIBO INDIVIDUAL DE SALARIOS</div>
<div class="nomina-subtitle">Simulación didáctica para uso docente</div>

<div class="nomina-grid-2">
<div class="nomina-box">
<div class="nomina-box-title">Empresa</div>
<div><strong>Empresa:</strong> {datos_empresa['nombre_empresa']}</div>
<div><strong>CIF:</strong> {datos_empresa['cif_empresa']}</div>
<div><strong>CCC:</strong> {datos_empresa['ccc_empresa']}</div>
<div><strong>Centro:</strong> {datos_empresa['centro_trabajo']}</div>
</div>

<div class="nomina-box">
<div class="nomina-box-title">Trabajador/a</div>
<div><strong>Nombre:</strong> {datos_trabajador['nombre_trabajador']}</div>
<div><strong>NIF:</strong> {datos_trabajador['nif_trabajador']}</div>
<div><strong>Nº SS:</strong> {datos_trabajador['num_ss']}</div>
<div><strong>Categoría:</strong> {datos_trabajador['categoria']}</div>
</div>
</div>

<div class="nomina-grid-2">
<div class="nomina-box">
<div class="nomina-box-title">Periodo de liquidación</div>
<div><strong>Desde:</strong> {periodo['fecha_inicio']}</div>
<div><strong>Hasta:</strong> {periodo['fecha_fin']}</div>
<div><strong>Total días:</strong> {periodo['dias']}</div>
</div>

<div class="nomina-box">
<div class="nomina-box-title">Datos contractuales</div>
<div><strong>Contrato:</strong> {datos_trabajador['tipo_contrato']}</div>
<div><strong>Grupo:</strong> {datos_trabajador['grupo_cotizacion']}</div>
<div><strong>Pagas/año:</strong> {r['pagas_ano']}</div>
<div><strong>Prorrata extras:</strong> {'Sí' if r['prorrata_extras'] else 'No'}</div>
</div>
</div>

<div class="nomina-section">
<div class="nomina-section-title">DEVENGOS</div>
<div class="nomina-row header"><div>Concepto</div><div class="center">Unidades / Tipo</div><div class="right">Importe</div></div>
{dev_html}
<div class="nomina-row total"><div>Total devengado</div><div></div><div class="right">{eur(r['total_devengado'])}</div></div>
</div>

<div class="nomina-section">
<div class="nomina-section-title">DEDUCCIONES</div>
<div class="nomina-row header"><div>Concepto</div><div class="center">Tipo</div><div class="right">Importe</div></div>
{ded_html}
<div class="nomina-row total"><div>Total a deducir</div><div></div><div class="right">{eur(r['total_deducciones'])}</div></div>
</div>

<div class="nomina-summary-grid">
<div class="nomina-summary-box"><div class="nomina-summary-label">Base de cotización</div><div class="nomina-summary-value">{eur(r['base_cotizacion'])}</div></div>
<div class="nomina-summary-box"><div class="nomina-summary-label">Líquido a percibir</div><div class="nomina-summary-value">{eur(r['neto'])}</div></div>
<div class="nomina-summary-box"><div class="nomina-summary-label">Coste empresa</div><div class="nomina-summary-value">{eur(r['coste_empresa'])}</div></div>
</div>

<div class="nomina-footer">Documento generado con fines didácticos. El cálculo es simplificado.</div>
</div>
</body>
</html>
"""
    return textwrap.dedent(html)


st.title("Simulador didáctico de nóminas")
st.markdown("Aplicación para clase: nómina, cotizaciones, coste empresa, comparación de escenarios y retribución flexible.")

st.sidebar.header("Configuración general")
perfil = st.sidebar.selectbox("Perfil de partida", ["Personalizado", "Administrativo junior", "Técnico con complementos", "Perfil con IRPF alto"])

if perfil == "Administrativo junior":
    defaults = {"salario_base": 1250.0, "complemento_personal": 80.0, "complemento_puesto": 100.0, "plus_convenio": 90.0, "plus_transporte": 85.0, "horas_extra": 0.0, "precio_hora_extra": 15.0, "pagas_ano": 14, "prorrata": False, "irpf": 8.0}
elif perfil == "Técnico con complementos":
    defaults = {"salario_base": 1750.0, "complemento_personal": 150.0, "complemento_puesto": 240.0, "plus_convenio": 120.0, "plus_transporte": 100.0, "horas_extra": 4.0, "precio_hora_extra": 18.0, "pagas_ano": 14, "prorrata": False, "irpf": 13.0}
elif perfil == "Perfil con IRPF alto":
    defaults = {"salario_base": 2600.0, "complemento_personal": 250.0, "complemento_puesto": 300.0, "plus_convenio": 150.0, "plus_transporte": 110.0, "horas_extra": 2.0, "precio_hora_extra": 22.0, "pagas_ano": 12, "prorrata": True, "irpf": 19.0}
else:
    defaults = {"salario_base": 1450.0, "complemento_personal": 100.0, "complemento_puesto": 120.0, "plus_convenio": 95.0, "plus_transporte": 90.0, "horas_extra": 0.0, "precio_hora_extra": 16.0, "pagas_ano": 14, "prorrata": False, "irpf": 10.0}

cot_cc_pct, cot_desempleo_pct, cot_formacion_pct = 4.70, 1.55, 0.10
emp_cc_pct, emp_desempleo_pct, emp_formacion_pct, emp_fogasa_pct, emp_at_ep_pct = 23.60, 5.50, 0.60, 0.20, 1.50
pagas_ano = defaults["pagas_ano"]
prorrata_extras = defaults["prorrata"]

nombre_empresa, cif_empresa, ccc_empresa, centro_trabajo = "Empresa Demo S.L.", "B12345678", "0111/22/123456789", "Madrid"
nombre_trabajador, nif_trabajador, num_ss, categoria = "Alumno Ejemplo", "12345678A", "28/1234567890", "Administrativo"
tipo_contrato, grupo_cotizacion = "Indefinido", "7"
fecha_inicio, fecha_fin, dias = date(2026, 3, 1), date(2026, 3, 31), 30

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Simulador", "Nómina generada", "Cotizaciones", "Comparar escenarios", "Retribución flexible"])

with tab1:
    st.subheader("1. Datos de empresa y trabajador")
    c1, c2 = st.columns(2)
    with c1:
        nombre_empresa = st.text_input("Empresa", value=nombre_empresa)
        cif_empresa = st.text_input("CIF empresa", value=cif_empresa)
        ccc_empresa = st.text_input("CCC", value=ccc_empresa)
        centro_trabajo = st.text_input("Centro de trabajo", value=centro_trabajo)
    with c2:
        nombre_trabajador = st.text_input("Trabajador/a", value=nombre_trabajador)
        nif_trabajador = st.text_input("NIF trabajador", value=nif_trabajador)
        num_ss = st.text_input("Nº Seguridad Social", value=num_ss)
        categoria = st.text_input("Categoría profesional", value=categoria)
        tipo_contrato = st.selectbox("Tipo de contrato", ["Indefinido", "Temporal", "Formativo"])
        grupo_cotizacion = st.selectbox("Grupo de cotización", ["1", "2", "3", "4", "5", "6", "7"], index=6)

    st.subheader("2. Periodo")
    c3, c4, c5 = st.columns(3)
    with c3:
        fecha_inicio = st.date_input("Fecha inicio", value=fecha_inicio)
    with c4:
        fecha_fin = st.date_input("Fecha fin", value=fecha_fin)
    with c5:
        dias = st.number_input("Días liquidados", min_value=1, max_value=31, value=dias, step=1)

    st.subheader("3. Parámetros salariales")
    col_izq, col_der = st.columns(2)
    with col_izq:
        salario_base = input_conectado("Salario base mensual", 0.0, 5000.0, defaults["salario_base"], 10.0, "salario_base")
        complemento_personal = input_conectado("Complemento personal", 0.0, 3000.0, defaults["complemento_personal"], 10.0, "complemento_personal")
        complemento_puesto = input_conectado("Complemento de puesto", 0.0, 3000.0, defaults["complemento_puesto"], 10.0, "complemento_puesto")
        plus_convenio = input_conectado("Plus convenio", 0.0, 1000.0, defaults["plus_convenio"], 5.0, "plus_convenio")
        plus_transporte = input_conectado("Plus transporte", 0.0, 1000.0, defaults["plus_transporte"], 5.0, "plus_transporte")
    with col_der:
        horas_extra = input_conectado("Número de horas extra", 0.0, 40.0, defaults["horas_extra"], 1.0, "horas_extra")
        precio_hora_extra = input_conectado("Precio por hora extra", 0.0, 50.0, defaults["precio_hora_extra"], 1.0, "precio_hora_extra")
        pagas_ano = st.selectbox("Número de pagas al año", [12, 14], index=0 if defaults["pagas_ano"] == 12 else 1)
        prorrata_extras = st.checkbox("Prorrata de pagas extra", value=defaults["prorrata"])
        irpf_pct = input_conectado("Retención IRPF (%)", 0.0, 30.0, defaults["irpf"], 0.5, "irpf_pct")

    with st.expander("Ajustes avanzados de cotización simplificada"):
        ca1, ca2 = st.columns(2)
        with ca1:
            cot_cc_pct = st.number_input("Trabajador - Contingencias comunes (%)", min_value=0.0, max_value=20.0, value=4.70, step=0.01)
            cot_desempleo_pct = st.number_input("Trabajador - Desempleo (%)", min_value=0.0, max_value=10.0, value=1.55, step=0.01)
            cot_formacion_pct = st.number_input("Trabajador - Formación profesional (%)", min_value=0.0, max_value=5.0, value=0.10, step=0.01)
        with ca2:
            emp_cc_pct = st.number_input("Empresa - Contingencias comunes (%)", min_value=0.0, max_value=40.0, value=23.60, step=0.01)
            emp_desempleo_pct = st.number_input("Empresa - Desempleo (%)", min_value=0.0, max_value=15.0, value=5.50, step=0.01)
            emp_formacion_pct = st.number_input("Empresa - Formación profesional (%)", min_value=0.0, max_value=5.0, value=0.60, step=0.01)
            emp_fogasa_pct = st.number_input("Empresa - FOGASA (%)", min_value=0.0, max_value=5.0, value=0.20, step=0.01)
            emp_at_ep_pct = st.number_input("Empresa - AT/EP (%)", min_value=0.0, max_value=15.0, value=1.50, step=0.01)

    resultado = calcular_nomina(salario_base, complemento_personal, complemento_puesto, plus_transporte, plus_convenio, horas_extra, precio_hora_extra, pagas_ano, prorrata_extras, irpf_pct, cot_cc_pct, cot_desempleo_pct, cot_formacion_pct, emp_cc_pct, emp_desempleo_pct, emp_formacion_pct, emp_fogasa_pct, emp_at_ep_pct)

    st.subheader("4. Resumen del escenario actual")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total devengado", eur(resultado["total_devengado"]))
    m2.metric("Total deducciones", eur(resultado["total_deducciones"]))
    m3.metric("Líquido a percibir", eur(resultado["neto"]))
    m4.metric("Coste empresa", eur(resultado["coste_empresa"]))

with tab2:
    resultado = calcular_nomina(
        st.session_state.get("salario_base", defaults["salario_base"]),
        st.session_state.get("complemento_personal", defaults["complemento_personal"]),
        st.session_state.get("complemento_puesto", defaults["complemento_puesto"]),
        st.session_state.get("plus_transporte", defaults["plus_transporte"]),
        st.session_state.get("plus_convenio", defaults["plus_convenio"]),
        st.session_state.get("horas_extra", defaults["horas_extra"]),
        st.session_state.get("precio_hora_extra", defaults["precio_hora_extra"]),
        pagas_ano,
        prorrata_extras,
        st.session_state.get("irpf_pct", defaults["irpf"]),
        cot_cc_pct,
        cot_desempleo_pct,
        cot_formacion_pct,
        emp_cc_pct,
        emp_desempleo_pct,
        emp_formacion_pct,
        emp_fogasa_pct,
        emp_at_ep_pct,
    )
    datos_empresa = {"nombre_empresa": nombre_empresa, "cif_empresa": cif_empresa, "ccc_empresa": ccc_empresa, "centro_trabajo": centro_trabajo}
    datos_trabajador = {"nombre_trabajador": nombre_trabajador, "nif_trabajador": nif_trabajador, "num_ss": num_ss, "categoria": categoria, "tipo_contrato": tipo_contrato, "grupo_cotizacion": grupo_cotizacion}
    periodo = {"fecha_inicio": fecha_inicio.strftime("%d/%m/%Y"), "fecha_fin": fecha_fin.strftime("%d/%m/%Y"), "dias": dias}
    st.subheader("Nómina visual")
    components.html(render_nomina_html(datos_empresa, datos_trabajador, periodo, resultado), height=1250, scrolling=True)

with tab3:
    resultado = calcular_nomina(
        st.session_state.get("salario_base", defaults["salario_base"]),
        st.session_state.get("complemento_personal", defaults["complemento_personal"]),
        st.session_state.get("complemento_puesto", defaults["complemento_puesto"]),
        st.session_state.get("plus_transporte", defaults["plus_transporte"]),
        st.session_state.get("plus_convenio", defaults["plus_convenio"]),
        st.session_state.get("horas_extra", defaults["horas_extra"]),
        st.session_state.get("precio_hora_extra", defaults["precio_hora_extra"]),
        pagas_ano,
        prorrata_extras,
        st.session_state.get("irpf_pct", defaults["irpf"]),
        cot_cc_pct,
        cot_desempleo_pct,
        cot_formacion_pct,
        emp_cc_pct,
        emp_desempleo_pct,
        emp_formacion_pct,
        emp_fogasa_pct,
        emp_at_ep_pct,
    )

    st.subheader("Cotizaciones y coste laboral")

    st.metric("Base de cotización mensual", eur(resultado["base_cotizacion"]))
    st.markdown("### Efecto del número de pagas")

e1, e2, e3 = st.columns(3)

e1.metric(
    "Salario mensual cobrado",
    eur(resultado["total_devengado"])
)

e2.metric(
    "Base de cotización Seguridad Social",
    eur(resultado["base_cotizacion"])
)

e3.metric(
    "Bruto anual estimado",
    eur(resultado["bruto_anual"])
)

st.write(
    f"""
Base de cotización calculada como:

**bruto anual / 12**

{eur(resultado["bruto_anual"])} / 12 = **{eur(resultado["base_cotizacion"])}**
"""
)

if resultado["pagas_ano"] == 14 and not resultado["prorrata_extras"]:
    st.info(
        "Con 14 pagas sin prorrata la Seguridad Social distribuye las pagas "
        "extraordinarias en las bases mensuales de cotización. "
        "Por eso la base de cotización es mayor que el salario cobrado ese mes."
    )

    a, b = st.columns(2)

    with a:
        st.markdown("### A cargo del trabajador")
        df_trab = pd.DataFrame({
            "Concepto": [
                "Contingencias comunes",
                "Desempleo",
                "Formación profesional",
            ],
            "Tipo aplicado": [
                f"{cot_cc_pct:.2f} %",
                f"{cot_desempleo_pct:.2f} %",
                f"{cot_formacion_pct:.2f} %",
            ],
            "Cuota": [
                eur(resultado["cuota_cc"]),
                eur(resultado["cuota_desempleo"]),
                eur(resultado["cuota_formacion"]),
            ],
        })
        st.dataframe(df_trab, use_container_width=True, hide_index=True)
        st.metric(
            "Total cotización trabajador",
            eur(resultado["cuota_cc"] + resultado["cuota_desempleo"] + resultado["cuota_formacion"])
        )

    with b:
        st.markdown("### A cargo de la empresa")
        df_emp = pd.DataFrame({
            "Concepto": [
                "Contingencias comunes",
                "Desempleo",
                "Formación profesional",
                "FOGASA",
                "AT/EP",
            ],
            "Tipo aplicado": [
                f"{emp_cc_pct:.2f} %",
                f"{emp_desempleo_pct:.2f} %",
                f"{emp_formacion_pct:.2f} %",
                f"{emp_fogasa_pct:.2f} %",
                f"{emp_at_ep_pct:.2f} %",
            ],
            "Cuota": [
                eur(resultado["emp_cc"]),
                eur(resultado["emp_desempleo"]),
                eur(resultado["emp_formacion"]),
                eur(resultado["emp_fogasa"]),
                eur(resultado["emp_at_ep"]),
            ],
        })
        st.dataframe(df_emp, use_container_width=True, hide_index=True)
        st.metric("Total cotización empresa", eur(resultado["total_cot_empresa"]))

    st.markdown("### Síntesis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Bruto mensual", eur(resultado["total_devengado"]))
    c2.metric("Neto mensual", eur(resultado["neto"]))
    c3.metric("Coste total empresa", eur(resultado["coste_empresa"]))

with tab4:
    st.subheader("Comparador paramétrico libre")
    base = calcular_nomina(
        st.session_state.get("salario_base", defaults["salario_base"]),
        st.session_state.get("complemento_personal", defaults["complemento_personal"]),
        st.session_state.get("complemento_puesto", defaults["complemento_puesto"]),
        st.session_state.get("plus_transporte", defaults["plus_transporte"]),
        st.session_state.get("plus_convenio", defaults["plus_convenio"]),
        st.session_state.get("horas_extra", defaults["horas_extra"]),
        st.session_state.get("precio_hora_extra", defaults["precio_hora_extra"]),
        pagas_ano,
        prorrata_extras,
        st.session_state.get("irpf_pct", defaults["irpf"]),
        cot_cc_pct,
        cot_desempleo_pct,
        cot_formacion_pct,
        emp_cc_pct,
        emp_desempleo_pct,
        emp_formacion_pct,
        emp_fogasa_pct,
        emp_at_ep_pct,
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Escenario base")
        st.write(f"Salario base: **{eur(base['salario_base'])}**")
        st.write(f"Complemento personal: **{eur(base['complemento_personal'])}**")
        st.write(f"Complemento puesto: **{eur(base['complemento_puesto'])}**")
        st.write(f"Plus convenio: **{eur(base['plus_convenio'])}**")
        st.write(f"Plus transporte: **{eur(base['plus_transporte'])}**")
        st.write(f"Horas extra: **{base['horas_extra']:.2f} h**")
        st.write(f"Precio hora extra: **{eur(base['precio_hora_extra'])}**")
        st.write(f"IRPF: **{base['irpf_pct']:.2f}%**")
        st.write(f"Pagas: **{base['pagas_ano']}**")
        st.write(f"Prorrata: **{'Sí' if base['prorrata_extras'] else 'No'}**")
    with right:
        st.markdown("### Escenario comparado editable")
        comp_salario_base = st.slider("Salario base comparado", 0.0, 6000.0, float(base["salario_base"]), 10.0)
        comp_complemento_personal = st.slider("Complemento personal comparado", 0.0, 3000.0, float(base["complemento_personal"]), 10.0)
        comp_complemento_puesto = st.slider("Complemento puesto comparado", 0.0, 3000.0, float(base["complemento_puesto"]), 10.0)
        comp_plus_convenio = st.slider("Plus convenio comparado", 0.0, 1500.0, float(base["plus_convenio"]), 5.0)
        comp_plus_transporte = st.slider("Plus transporte comparado", 0.0, 1000.0, float(base["plus_transporte"]), 5.0)
        comp_horas_extra = st.slider("Horas extra comparadas", 0.0, 40.0, float(base["horas_extra"]), 1.0)
        comp_precio_hora_extra = st.slider("Precio hora extra comparado", 0.0, 60.0, float(base["precio_hora_extra"]), 1.0)
        comp_irpf = st.slider("IRPF comparado (%)", 0.0, 30.0, float(base["irpf_pct"]), 0.5)
        comp_pagas = st.selectbox("Pagas comparadas", [12, 14], index=0 if base["pagas_ano"] == 12 else 1)
        comp_prorrata = st.checkbox("Prorrata comparada", value=base["prorrata_extras"])

    comp = calcular_nomina(comp_salario_base, comp_complemento_personal, comp_complemento_puesto, comp_plus_transporte, comp_plus_convenio, comp_horas_extra, comp_precio_hora_extra, comp_pagas, comp_prorrata, comp_irpf, cot_cc_pct, cot_desempleo_pct, cot_formacion_pct, emp_cc_pct, emp_desempleo_pct, emp_formacion_pct, emp_fogasa_pct, emp_at_ep_pct)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Neto base", eur(base["neto"]))
    c2.metric("Neto comparado", eur(comp["neto"]), delta=eur(comp["neto"] - base["neto"]))
    c3.metric("Coste empresa base", eur(base["coste_empresa"]))
    c4.metric("Coste empresa comparado", eur(comp["coste_empresa"]), delta=eur(comp["coste_empresa"] - base["coste_empresa"]))

    df_comp = pd.DataFrame({
        "Magnitud": ["Total devengado", "Total deducciones", "Líquido a percibir", "Base de cotización", "Coste empresa", "Bruto anual estimado", "Neto anual estimado"],
        "Escenario base": [eur(base["total_devengado"]), eur(base["total_deducciones"]), eur(base["neto"]), eur(base["base_cotizacion"]), eur(base["coste_empresa"]), eur(base["bruto_anual"]), eur(base["neto_anual_estimado"])],
        "Escenario comparado": [eur(comp["total_devengado"]), eur(comp["total_deducciones"]), eur(comp["neto"]), eur(comp["base_cotizacion"]), eur(comp["coste_empresa"]), eur(comp["bruto_anual"]), eur(comp["neto_anual_estimado"])],
    })
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Retribución flexible y ahorro fiscal estimado (Madrid)")

    base = calcular_nomina(
        st.session_state.get("salario_base", defaults["salario_base"]),
        st.session_state.get("complemento_personal", defaults["complemento_personal"]),
        st.session_state.get("complemento_puesto", defaults["complemento_puesto"]),
        st.session_state.get("plus_transporte", defaults["plus_transporte"]),
        st.session_state.get("plus_convenio", defaults["plus_convenio"]),
        st.session_state.get("horas_extra", defaults["horas_extra"]),
        st.session_state.get("precio_hora_extra", defaults["precio_hora_extra"]),
        pagas_ano,
        prorrata_extras,
        st.session_state.get("irpf_pct", defaults["irpf"]),
        cot_cc_pct,
        cot_desempleo_pct,
        cot_formacion_pct,
        emp_cc_pct,
        emp_desempleo_pct,
        emp_formacion_pct,
        emp_fogasa_pct,
        emp_at_ep_pct,
    )

    st.markdown("### Parámetros de retribución flexible")

    p1, p2 = st.columns(2)
    with p1:
        dias_laborables = st.slider(
            "Cheque restaurante anual (límite: 11 € × días laborables)",
            0.0,
            float(11 * 230),
            0.0,
            10.0,
        )
        personas_seguro = st.slider("Personas cubiertas por seguro médico", 1, 5, 1, 1)
        transporte_anual = st.slider(
            "Transporte público anual (límite fiscal general: 1.500 €)",
            0.0,
            1500.0,
            0.0,
            10.0,
        )
        seguro_anual = st.slider(
            f"Seguro médico anual (límite: {500 * personas_seguro} €)",
            0.0,
            float(500 * personas_seguro),
            0.0,
            10.0,
        )

    with p2:
        guarderia_anual = st.slider(
            "Guardería anual (exenta si cumple condiciones legales)",
            0.0,
            6000.0,
            0.0,
            10.0,
        )
        acciones_anual = st.slider(
            "Acciones / stock options anual (límite exento: 12.000 €)",
            0.0,
            12000.0,
            0.0,
            50.0,
        )
        pension_anual = st.slider(
            "Aportación plan pensiones empleo (la reducción aplicada puede ser menor)",
            0.0,
            10000.0,
            0.0,
            50.0,
        )

    comida_anual = dias_laborables

    ss_trab_anual = (base["cuota_cc"] + base["cuota_desempleo"] + base["cuota_formacion"]) * 12
    ss_empresa_anual = base["total_cot_empresa"] * 12

    rf = calcular_retribucion_flexible_madrid(
        bruto_anual=base["bruto_anual"],
        ss_trab_anual=ss_trab_anual,
        ss_empresa_anual=ss_empresa_anual,
        comida_anual=comida_anual,
        transporte_anual=transporte_anual,
        seguro_anual=seguro_anual,
        guarderia_anual=guarderia_anual,
        acciones_anual=acciones_anual,
        pension_anual=pension_anual,
        personas_seguro=personas_seguro,
        dias_laborables=int(dias_laborables / 11) if dias_laborables > 0 else 220,
    )

    # --------------------------------------------------
    # AVISOS Y VALIDACIONES
    # --------------------------------------------------
    st.markdown("### Validación de límites y operación de la simulación")

    v1, v2, v3 = st.columns(3)
    v1.metric("Límite 30% especie", eur(rf["limite_especie_30"]))
    v2.metric("Especie inicial propuesta", eur(rf["especie_inicial"]))
    v3.metric("Especie finalmente aplicada", eur(rf["especie_final"]))

    if rf["ajuste_especie_aplicado"]:
        st.warning(
            "La retribución en especie propuesta superaba el límite global permitido. "
            "La simulación ha ajustado automáticamente los importes en especie de forma proporcional."
        )

    st.info(
        f"La simulación aplica los límites legales de especie, el control de salario monetario mínimo "
        f"(referenciado al SMI anual: {eur(rf['smi_anual'])}) y una reducción prudente en previsión social "
        f"(límite porcentual calculado: {eur(rf['limite_pension_porcentaje'])})."
    )

    # --------------------------------------------------
    # MÉTRICAS PRINCIPALES
    # --------------------------------------------------
    st.markdown("### Resultado principal")

    k1, k2, k3 = st.columns(3)
    k1.metric("Ahorro fiscal anual", eur(rf["ahorro_fiscal"]))
    k2.metric("IRPF sin flexible", eur(rf["irpf_sin"]))
    k3.metric("IRPF con flexible", eur(rf["irpf_con"]), delta=eur(rf["irpf_con"] - rf["irpf_sin"]))

    k4, k5, k6 = st.columns(3)
    k4.metric("Neto anual sin flexible", eur(rf["neto_sin"]))
    k5.metric("Neto monetario con flexible", eur(rf["neto_monetario_con"]))
    k6.metric("Neto económico total con flexible", eur(rf["neto_economico_con"]), delta=eur(rf["neto_economico_con"] - rf["neto_sin"]))

    # --------------------------------------------------
    # PROCESO FISCAL EN DOS COLUMNAS
    # --------------------------------------------------
    st.markdown("### Proceso de cálculo fiscal en paralelo")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("## Sin retribución flexible")
        df_sin = pd.DataFrame({
            "Paso": [
                "Salario bruto anual",
                "Rendimiento íntegro del trabajo",
                "(-) Seguridad Social trabajador",
                "(-) Gasto deducible general",
                "(=) Rendimiento neto del trabajo",
                "(-) Reducción rendimientos trabajo",
                "(=) Base liquidable general",
                "Mínimo personal",
                "(=) Base sometida a gravamen",
                "IRPF anual estimado",
                "Neto anual",
            ],
            "Valor": [
                eur(rf["bruto_anual"]),
                eur(rf["rit_sin"]),
                eur(rf["ss_trab_anual"]),
                eur(2000.0),
                eur(rf["rnt_sin"]),
                eur(rf["red_trab_sin"]),
                eur(rf["blg_sin"]),
                eur(rf["minimo_personal"]),
                eur(rf["base_gravable_sin"]),
                eur(rf["irpf_sin"]),
                eur(rf["neto_sin"]),
            ],
        })
        st.dataframe(df_sin, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("## Con retribución flexible")
        df_con = pd.DataFrame({
            "Paso": [
                "Salario bruto anual",
                "(-) Retribución flexible exenta",
                "(=) Rendimiento íntegro del trabajo",
                "(-) Seguridad Social trabajador",
                "(-) Gasto deducible general",
                "(=) Rendimiento neto del trabajo",
                "(-) Reducción rendimientos trabajo",
                "(-) Reducción plan pensiones",
                "(=) Base liquidable general",
                "Mínimo personal",
                "(=) Base sometida a gravamen",
                "IRPF anual estimado",
                "Neto monetario",
                "(+) Retribución flexible total",
                "(=) Neto económico total",
            ],
            "Valor": [
                eur(rf["bruto_anual"]),
                eur(rf["total_exento"]),
                eur(rf["rit_con"]),
                eur(rf["ss_trab_anual"]),
                eur(2000.0),
                eur(rf["rnt_con"]),
                eur(rf["red_trab_con"]),
                eur(rf["pension_reduccion"]),
                eur(rf["blg_con"]),
                eur(rf["minimo_personal"]),
                eur(rf["base_gravable_con"]),
                eur(rf["irpf_con"]),
                eur(rf["neto_monetario_con"]),
                eur(rf["flexible_total"]),
                eur(rf["neto_economico_con"]),
            ],
        })
        st.dataframe(df_con, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # DETALLE DE CONCEPTOS FLEXIBLE
    # --------------------------------------------------
    st.markdown("### Detalle de conceptos de retribución flexible")

    df_limites = pd.DataFrame({
        "Concepto": [
            "Cheque restaurante",
            "Transporte público",
            "Seguro médico",
            "Guardería",
            "Acciones",
            "Plan pensiones empleo",
        ],
        "Importe introducido": [
            eur(comida_anual),
            eur(transporte_anual),
            eur(seguro_anual),
            eur(guarderia_anual),
            eur(acciones_anual),
            eur(pension_anual),
        ],
        "Parte exenta / reducible": [
            eur(rf["comida_exenta"]),
            eur(rf["transporte_exento"]),
            eur(rf["seguro_exento"]),
            eur(rf["guarderia_exenta"]),
            eur(rf["acciones_exentas"]),
            eur(rf["pension_reduccion"]),
        ],
        "Parte sujeta": [
            eur(rf["comida_sujeta"]),
            eur(rf["transporte_sujeto"]),
            eur(rf["seguro_sujeto"]),
            eur(0.0),
            eur(rf["acciones_sujetas"]),
            eur(0.0),
        ],
    })
    st.dataframe(df_limites, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # RESUMEN COMPARADO
    # --------------------------------------------------
    st.markdown("### Resumen comparado final")

    df_rf = pd.DataFrame({
        "Magnitud": [
            "Bruto anual",
            "SS trabajador anual",
            "Base liquidable general",
            "IRPF anual estimado",
            "Neto anual / monetario",
            "Retribución flexible total",
            "Neto económico total",
            "Carga total asociada al empleo",
            "Límite global especie",
            "Especie aplicada",
            "Reducción pensiones aplicada",
        ],
        "Sin flexible": [
            eur(rf["bruto_anual"]),
            eur(rf["ss_trab_anual"]),
            eur(rf["blg_sin"]),
            eur(rf["irpf_sin"]),
            eur(rf["neto_sin"]),
            eur(0.0),
            eur(rf["neto_sin"]),
            eur(rf["carga_total_empleo_sin"]),
            eur(rf["limite_especie_30"]),
            eur(0.0),
            eur(0.0),
        ],
        "Con flexible": [
            eur(rf["bruto_anual"]),
            eur(rf["ss_trab_anual"]),
            eur(rf["blg_con"]),
            eur(rf["irpf_con"]),
            eur(rf["neto_monetario_con"]),
            eur(rf["flexible_total"]),
            eur(rf["neto_economico_con"]),
            eur(rf["carga_total_empleo_con"]),
            eur(rf["limite_especie_30"]),
            eur(rf["especie_final"]),
            eur(rf["pension_reduccion"]),
        ],
    })
    st.dataframe(df_rf, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # GRÁFICO
    # --------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.bar(
        ["IRPF sin flexible", "IRPF con flexible", "Ahorro fiscal", "Mejora poder adquisitivo"],
        [rf["irpf_sin"], rf["irpf_con"], rf["ahorro_fiscal"], rf["mejora_poder_adquisitivo"]]
    )
    ax2.set_ylabel("Euros")
    ax2.set_title("Impacto fiscal de la retribución flexible")
    st.pyplot(fig2)

    st.markdown(
        '<div class="small-note">La simulación muestra el cálculo fiscal en paralelo y aplica automáticamente los límites legales incorporados al modelo.</div>',
        unsafe_allow_html=True
    )
